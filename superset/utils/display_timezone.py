# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Helpers for the ``DISPLAY_TIME_ZONE`` setting.

Superset assumes temporal data is stored in UTC.  When ``DISPLAY_TIME_ZONE`` is
set, temporal columns are converted to wall-clock time in that time zone *in
SQL*, so that grouping (time grains), filtering (time ranges) and rendering all
agree on what "a day" means.  Values then travel to the browser as naive local
wall clock, which is exactly how the frontend already renders them (d3
``utcFormat`` and ECharts ``useUTC: true``).

The zone is resolved in four tiers, most specific first:

1. the zone the request asserts, for embedded dashboards whose guest viewer has
   no stored preference (``?timezone=`` plus a matching header);
2. the current user's own choice, stored on ``user_attribute``;
3. the target database's ``Extra``, which may also opt the database out;
4. the ``DISPLAY_TIME_ZONE`` setting.

Tiers 3 and 4 decide *whether* to convert at all -- a database holding
non-UTC data opts out there, and neither a request nor a user preference can
re-enable it.  Tiers 1 and 2 only pick which zone to render in.  Because the
resolved zone is part of the query cache key, two viewers in different zones
never share cached results.
"""

from __future__ import annotations

import logging
import os
import re
import zoneinfo
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, TYPE_CHECKING
from zoneinfo import available_timezones, ZoneInfo, ZoneInfoNotFoundError

from flask import current_app, g, has_app_context, has_request_context, request

UTC = timezone.utc

#: Application-context key memoizing the current user's time zone.
_G_CACHE_KEY = "_superset_display_time_zone"


if TYPE_CHECKING:
    from superset.models.core import Database

logger = logging.getLogger(__name__)

CONFIG_KEY = "DISPLAY_TIME_ZONE"

#: Key used in a database's ``Extra`` JSON to override (or disable) the global
#: setting for that database only, e.g. ``{"display_time_zone": "UTC"}`` or
#: ``{"display_time_zone": null}`` to opt out entirely.
DATABASE_EXTRA_KEY = "display_time_zone"

#: Key used in a column's ``Extra`` JSON to opt a single column out, e.g. a
#: calculated column that already converts the time zone itself.
COLUMN_EXTRA_KEY = "skip_time_zone_conversion"

#: URL parameter carrying the viewer's time zone into an embedded dashboard,
#: alongside ``lang``, e.g. ``/embedded/<uuid>?timezone=Asia/Ho_Chi_Minh``.
URL_PARAM = "timezone"

#: Config key naming the request header that carries the same value on the API
#: calls the embedded page makes afterwards.
HEADER_CONFIG_KEY = "DISPLAY_TIME_ZONE_HEADER_NAME"
DEFAULT_HEADER_NAME = "X-Superset-Display-Timezone"

# ``TIMESTAMP WITH TIME ZONE``, ``TIMESTAMPTZ``, ``DateTime64(3, 'UTC')``, ...
_TZ_AWARE_TYPE_RE = re.compile(r"with\s+time\s+zone|timestamptz|timetz", re.IGNORECASE)

# Date-only columns must not be shifted: there is no time-of-day to carry the
# offset, so converting would simply move the calendar date around.
_DATE_ONLY_TYPE_RE = re.compile(r"^\s*date\s*$", re.IGNORECASE)


class InvalidTimeZoneError(ValueError):
    """Raised when a configured time zone name is not recognized."""


@lru_cache(maxsize=1)
def _zone_aliases() -> dict[str, str]:
    """Map every deprecated IANA name to the canonical zone it links to.

    Python's tzdata ships the IANA ``backward`` links -- ``Greenwich``,
    ``Asia/Saigon``, ``US/Eastern`` and ~150 more -- but databases generally
    ship only the canonical names. PostgreSQL, for one, rejects all of them:
    ``time zone "Greenwich" not recognized``. Since the zone name travels into
    the generated SQL verbatim, an alias would break the chart outright.

    The mapping is read from ``tzdata.zi``, the zone database's own source, so
    it stays correct as tzdata is updated instead of drifting from a list
    maintained here. Returns an empty map if that file cannot be found, which
    leaves names untouched -- the previous behaviour.
    """
    text: str | None = None
    for root in list(zoneinfo.TZPATH):
        path = os.path.join(root, "tzdata.zi")
        if os.path.isfile(path):
            text = Path(path).read_text(encoding="utf-8")
            break
    if text is None:
        try:
            text = (
                resources.files("tzdata.zoneinfo")
                .joinpath("tzdata.zi")
                .read_text(encoding="utf-8")
            )
        except (ModuleNotFoundError, FileNotFoundError, OSError):
            logger.warning(
                "tzdata.zi not found; deprecated time zone names will be passed "
                "to the database unchanged and may be rejected."
            )
            return {}

    aliases: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        # `L <target> <alias>`, the zic source form of a Link line
        if len(parts) > 2 and parts[0] in ("L", "Link"):
            aliases[parts[2]] = parts[1]
    return aliases


@lru_cache(maxsize=1)
def canonical_time_zones() -> frozenset[str]:
    """The zones this instance offers, excluding deprecated aliases.

    Also excludes the region-less legacy zones (``EST``, ``CET``,
    ``PST8PDT``...): they are canonical in tzdata but absent from PostgreSQL's
    ``pg_timezone_names``, and they describe a UTC offset rather than a place,
    which is not what a display time zone should mean.
    """
    aliases = _zone_aliases()
    return frozenset(
        name
        for name in available_timezones()
        # `UTC` is a link to `Etc/UTC` in tzdata, but it is the plainest name
        # for the most useful choice and every engine recognizes it
        if name == "UTC" or (name not in aliases and "/" in name)
    )


def canonicalize_time_zone(time_zone: str) -> str:
    """Resolve a deprecated alias to the canonical name databases accept.

    A name this instance already offers is returned untouched, so what the user
    picked is what reaches the SQL. That matters for ``UTC``, which tzdata links
    to ``Etc/UTC``: the plain name is the one every engine recognizes.
    """
    if time_zone in canonical_time_zones():
        return time_zone
    seen: set[str] = set()
    aliases = _zone_aliases()
    while time_zone in aliases and time_zone not in seen:
        seen.add(time_zone)
        time_zone = aliases[time_zone]
    return time_zone


@lru_cache(maxsize=1)
def available_time_zones() -> frozenset[str]:
    """Every IANA name this instance accepts as input (cached: it scans tzdata).

    Wider than :func:`canonical_time_zones`: a name already stored from an
    earlier version, or sent by an embedding host, still validates and is then
    canonicalized rather than rejected.

    Note this is not the same set a browser reports from
    ``Intl.supportedValuesOf('timeZone')``: the two disagree on which name in an
    alias pair is canonical (``Asia/Ho_Chi_Minh`` here, ``Asia/Saigon`` there).
    Pickers must therefore be populated from the server, not from the browser.
    """
    return frozenset(available_timezones())


def is_known_time_zone(time_zone: str) -> bool:
    """Whether ``time_zone`` is a name this instance accepts."""
    return time_zone in available_time_zones()


def validate_time_zone(time_zone: Any, source: str = CONFIG_KEY) -> str | None:
    """Return a usable, canonical IANA name for ``time_zone``, else ``None``.

    Deprecated aliases are resolved rather than rejected, so a name stored
    before this instance knew better keeps working instead of breaking the
    charts that use it.
    """
    if not time_zone:
        return None
    if not isinstance(time_zone, str):
        logger.warning("Ignoring non-string %s: %r", source, time_zone)
        return None
    if not is_known_time_zone(time_zone):
        logger.warning("Ignoring unknown %s: %r", source, time_zone)
        return None

    canonical = canonicalize_time_zone(time_zone)
    if canonical != time_zone:
        logger.info(
            "Resolving deprecated %s %r to %r, which databases recognize",
            source,
            time_zone,
            canonical,
        )
    return canonical


def get_configured_time_zone(database: Database | None = None) -> str | None:
    """The display time zone configured for a database, ignoring user choice.

    This decides *whether* conversion happens at all: a database whose data is
    not stored in UTC opts out here, and no user preference may re-enable it.

    :param database: database the query targets, if any
    :return: an IANA time zone name, or ``None`` when conversion is disabled
    """
    try:
        time_zone: Any = current_app.config.get(CONFIG_KEY)
    except RuntimeError:  # no application context (e.g. CLI, unit tests)
        return None

    if database is not None:
        try:
            extra = database.get_extra()
        except Exception:  # pylint: disable=broad-except
            extra = {}
        if DATABASE_EXTRA_KEY in extra:
            time_zone = extra[DATABASE_EXTRA_KEY]

    return validate_time_zone(time_zone)


def get_header_name() -> str:
    """Name of the request header carrying the viewer's time zone."""
    try:
        return current_app.config.get(HEADER_CONFIG_KEY) or DEFAULT_HEADER_NAME
    except RuntimeError:  # no application context
        return DEFAULT_HEADER_NAME


def get_request_time_zone() -> str | None:
    """The time zone the client asserted for this request, if any.

    An embedded dashboard runs in a cross-origin iframe, where cookies and
    sessions are unreliable and the viewer is an ephemeral guest user with no
    stored preference. The host application therefore states the zone
    explicitly: as a ``?timezone=`` parameter on the embedded page (the same way
    ``lang`` works), and as a header on the API calls that page makes
    afterwards.

    The value is client-supplied, so it is validated against the known IANA
    names and, like a user preference, can only choose *which* zone to render
    in -- never enable conversion for a database that opted out. It also feeds
    the query cache key, so two viewers in different zones never share results.
    """
    if not has_request_context():
        return None
    time_zone = request.headers.get(get_header_name()) or request.args.get(URL_PARAM)
    return validate_time_zone(time_zone, source=f"{URL_PARAM} request parameter")


def _current_user_id() -> int | None:
    """Id of the current user, or ``None`` when there is no stored preference.

    Anonymous users have none, and neither do guest users (embedded
    dashboards): a ``GuestUser`` is not an ORM object at all -- note it reports
    ``is_anonymous`` as ``False`` -- so it is excluded explicitly rather than
    left to the ``id`` check below. Both fall back to the configured default.
    """
    user = g.get("user")
    if user is None:
        return None
    if getattr(user, "is_anonymous", True) or getattr(user, "is_guest_user", False):
        return None
    user_id = getattr(user, "id", None)
    return user_id if isinstance(user_id, int) else None


def get_user_time_zone() -> str | None:
    """The time zone the current user picked, if any.

    Memoized per user on the application context: this is consulted once per
    column per query, and reading it hits the metadata database. The user id is
    part of the cache key because ``override_user`` swaps ``g.user`` within a
    single application context.
    """
    if not has_app_context():
        return None
    if (user_id := _current_user_id()) is None:
        return None

    cached = g.get(_G_CACHE_KEY)
    if cached is not None and cached[0] == user_id:
        return cached[1]  # type: ignore[no-any-return]

    time_zone = _load_user_time_zone(user_id)
    setattr(g, _G_CACHE_KEY, (user_id, time_zone))
    return time_zone


def _load_user_time_zone(user_id: int) -> str | None:
    """Read a user's time zone from ``user_attribute``."""
    # imported late: this module is loaded from `db_engine_specs.base`, long
    # before the models are importable
    from superset import db  # pylint: disable=import-outside-toplevel
    from superset.models.user_attributes import (  # pylint: disable=import-outside-toplevel
        UserAttribute,
    )

    try:
        time_zone = (
            db.session.query(UserAttribute.display_time_zone)
            .filter(UserAttribute.user_id == user_id)
            .limit(1)
            .scalar()
        )
    except Exception:  # pylint: disable=broad-except
        # never let a preference lookup break a query
        logger.warning("Could not read the display time zone for user %s", user_id)
        return None

    return validate_time_zone(time_zone, source="user display_time_zone")


def get_time_zone(database: Database | None = None) -> str | None:
    """Resolve the display time zone for a query.

    Resolution order: the zone asserted by the request (embedded dashboards),
    then the current user's choice, then the database's ``Extra`` override, then
    the ``DISPLAY_TIME_ZONE`` setting. The first two only select *which* zone to
    render in -- neither can enable conversion for a database that has opted
    out, whose data may not be UTC at all.

    :param database: database the query targets, if any
    :return: an IANA time zone name, or ``None`` when conversion is disabled
    """
    if (configured := get_configured_time_zone(database)) is None:
        return None
    return get_request_time_zone() or get_user_time_zone() or configured


def clear_user_time_zone_cache() -> None:
    """Forget the memoized user time zone, after the user changes it."""
    if has_app_context():
        g.pop(_G_CACHE_KEY, None)


def get_zone_info(time_zone: str) -> ZoneInfo:
    """``ZoneInfo`` for ``time_zone``, raising a Superset-friendly error."""
    try:
        return ZoneInfo(time_zone)
    except (ZoneInfoNotFoundError, ValueError) as ex:
        raise InvalidTimeZoneError(f"Unknown time zone: {time_zone}") from ex


def now(time_zone: str | None = None) -> datetime:
    """Current wall-clock time in ``time_zone``, as a naive ``datetime``.

    Falls back to the process-local ``datetime.now()`` when no time zone is
    configured, preserving upstream behaviour.
    """
    if time_zone is None:
        time_zone = get_time_zone()
    if time_zone is None:
        return datetime.now()
    return datetime.now(tz=get_zone_info(time_zone)).replace(tzinfo=None)


def to_utc(dttm: datetime, time_zone: str | None) -> datetime:
    """Read ``dttm`` as wall clock in ``time_zone`` and return naive UTC.

    Used when a bound has to be expressed in UTC after the rest of the pipeline
    has already moved to local wall clock (epoch-encoded columns).
    """
    if time_zone is None or dttm.tzinfo is not None:
        return dttm
    aware = dttm.replace(tzinfo=get_zone_info(time_zone))
    return aware.astimezone(UTC).replace(tzinfo=None)


def to_epoch_seconds(dttm: datetime, time_zone: str | None) -> int:
    """Whole seconds since the epoch for ``dttm``.

    With no time zone configured the naive value is read in the process's local
    zone, as upstream does; otherwise it is read as wall clock in ``time_zone``.
    """
    if time_zone is None or dttm.tzinfo is not None:
        return int(dttm.timestamp())
    return int(dttm.replace(tzinfo=get_zone_info(time_zone)).timestamp())


def get_utc_offset(time_zone: str, dttm: datetime | None = None) -> timedelta:
    """UTC offset of ``time_zone`` at ``dttm`` (default: now)."""
    reference = dttm or datetime.now()
    offset = reference.replace(tzinfo=get_zone_info(time_zone)).utcoffset()
    return offset or timedelta()


def format_utc_offset(time_zone: str, dttm: datetime | None = None) -> str:
    """UTC offset rendered as ``+HH:MM`` / ``-HH:MM``."""
    total_minutes = int(get_utc_offset(time_zone, dttm).total_seconds() // 60)
    sign = "-" if total_minutes < 0 else "+"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def get_utc_offset_minutes(time_zone: str, dttm: datetime | None = None) -> int:
    """UTC offset in whole minutes, e.g. ``420`` for ``Asia/Ho_Chi_Minh``."""
    return int(get_utc_offset(time_zone, dttm).total_seconds() // 60)


def is_tz_aware_type(type_: str | None, sqla_type: Any = None) -> bool:
    """Whether a column type already carries a time zone / is an instant."""
    if sqla_type is not None and getattr(sqla_type, "timezone", False):
        return True
    return bool(type_ and _TZ_AWARE_TYPE_RE.search(type_))


def is_date_only_type(type_: str | None) -> bool:
    """Whether a column type is a calendar date with no time-of-day."""
    return bool(type_ and _DATE_ONLY_TYPE_RE.match(type_))


def is_convertible_column(
    type_: str | None,
    python_date_format: str | None = None,
    extra: dict[str, Any] | None = None,
) -> bool:
    """Whether a temporal column may be time-zone converted in SQL.

    Excludes date-only columns, columns Superset parses from strings via
    ``python_date_format``, and columns explicitly opted out via ``Extra``.
    Epoch-encoded columns are allowed here because they are turned into a real
    timestamp first; callers that use the raw column must check separately.
    """
    if extra and extra.get(COLUMN_EXTRA_KEY):
        return False
    if python_date_format and python_date_format not in ("epoch_s", "epoch_ms"):
        return False
    return not is_date_only_type(type_)
