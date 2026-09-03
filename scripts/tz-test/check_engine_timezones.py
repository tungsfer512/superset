#!/usr/bin/env python
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
"""Check that DISPLAY_TIME_ZONE converts correctly on a given database.

Builds the conversion with the engine spec Superset itself uses, runs it, and
compares the result against Python's ``zoneinfo``. That catches an engine that
accepts a zone name but shifts by the wrong amount -- not just one that errors.

Run it inside the Superset container, which has the drivers and the config:

    docker compose exec superset \
        python scripts/tz-test/check_engine_timezones.py <sqlalchemy_uri> [--all]

``--all`` sweeps every zone the picker offers instead of a representative
sample; expect it to take a while against a remote database.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text

# Zones chosen to exercise the awkward cases: no DST, southern DST, negative
# offsets, and the quarter-hour offsets that a naive implementation rounds away.
SAMPLE_ZONES = [
    "UTC",
    "Asia/Ho_Chi_Minh",  # +07:00, no DST
    "Europe/Paris",  # northern DST
    "America/New_York",  # negative offset, northern DST
    "America/Sao_Paulo",  # negative offset, DST abolished
    "Australia/Lord_Howe",  # +10:30/+11:00, half-hour DST shift
    "Asia/Kathmandu",  # +05:45
    "Pacific/Chatham",  # +12:45/+13:45
    "Africa/Cairo",  # DST reintroduced in 2023
    "Etc/GMT",  # what the deprecated `Greenwich` resolves to
]

# One instant in each hemisphere's summer, so a zone that gets DST wrong in only
# one direction still shows up.
SAMPLE_INSTANTS = [
    datetime(2026, 1, 15, 17, 30),
    datetime(2026, 7, 15, 17, 30),
]


def expected(dttm: datetime, time_zone: str) -> datetime:
    """The wall clock the database should report, per Python's tzdata."""
    return (
        dttm.replace(tzinfo=timezone.utc)
        .astimezone(ZoneInfo(time_zone))
        .replace(tzinfo=None)
    )


# A *naive* timestamp literal per engine. `convert_dttm` is not usable here:
# PostgreSQL renders `TO_TIMESTAMP(...)`, which is a `timestamptz`, and feeding a
# zone-aware value into the naive template converts it the other way round.
NAIVE_LITERAL = {
    "bigquery": "DATETIME '{s}'",
    "clickhouse": "toDateTime('{s}')",
    "clickhousedb": "toDateTime('{s}')",
    "mysql": "CAST('{s}' AS DATETIME)",
    "starrocks": "CAST('{s}' AS DATETIME)",
    "mssql": "CAST('{s}' AS DATETIME2)",
    "sqlite": "'{s}'",
}
DEFAULT_NAIVE_LITERAL = "CAST('{s}' AS TIMESTAMP)"


def literal_for(spec: Any, dttm: datetime) -> str:
    """A naive UTC timestamp literal this engine understands."""
    template = NAIVE_LITERAL.get(spec.engine, DEFAULT_NAIVE_LITERAL)
    return template.format(s=dttm.strftime("%Y-%m-%d %H:%M:%S"))


def check(uri: str, zones: list[str]) -> int:
    # imported here: loading the engine specs pulls in the ORM models, which
    # need an initialized app
    from superset.db_engine_specs import get_engine_spec
    from superset.utils.display_timezone import validate_time_zone

    engine = create_engine(uri)
    spec = get_engine_spec(engine.dialect.name, engine.driver)

    template = spec.utc_to_tz_expression
    print(f"engine: {spec.engine_name or spec.engine}   spec: {spec.__name__}")
    if not template:
        print("  NO CONVERSION TEMPLATE -- DISPLAY_TIME_ZONE is ignored here.")
        return 1
    print(f"  template: {template}\n")

    failures = 0
    with engine.connect() as conn:
        for zone in zones:
            canonical = validate_time_zone(zone) or zone
            expr_template = spec.get_utc_to_tz_expression(canonical)
            if not expr_template:
                print(f"  {zone:22} SKIPPED (engine declares no template)")
                failures += 1
                continue
            for dttm in SAMPLE_INSTANTS:
                sql = (
                    f"SELECT {expr_template.replace('{col}', literal_for(spec, dttm))}"
                )
                want = expected(dttm, canonical)
                try:
                    got = conn.execute(text(sql)).scalar()
                except Exception as ex:  # pylint: disable=broad-except
                    print(
                        f"  {zone:22} {dttm:%Y-%m-%d} ERROR {str(ex).splitlines()[0]}"
                    )
                    failures += 1
                    continue
                if isinstance(got, str):
                    got = datetime.fromisoformat(got.replace("Z", "+00:00"))
                if got is not None and got.tzinfo is not None:
                    got = got.replace(tzinfo=None)
                if got != want:
                    print(f"  {zone:22} {dttm:%Y-%m-%d} WRONG got={got} want={want}")
                    failures += 1
    if not failures:
        print(f"  all {len(zones)} zones correct on both sample instants")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri", help="SQLAlchemy URI of the database to check")
    parser.add_argument(
        "--all",
        action="store_true",
        help="check every zone the picker offers, not just a sample",
    )
    args = parser.parse_args()

    from superset.app import create_app

    with create_app().app_context():
        from superset.utils.display_timezone import canonical_time_zones

        zones = sorted(canonical_time_zones()) if args.all else SAMPLE_ZONES
        failures = check(args.uri, zones)
    print(f"\n{'FAILED' if failures else 'OK'}: {failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
