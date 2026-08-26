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
"""Thumbnails must not be shared between viewers in different time zones."""

from __future__ import annotations

from unittest.mock import patch, PropertyMock

from flask import current_app
from flask_appbuilder.security.sqla.models import User

from superset.tasks.types import ExecutorType, FixedExecutor
from superset.utils import display_timezone
from superset.utils.core import override_user

TZ = "Asia/Ho_Chi_Minh"
OTHER_TZ = "Europe/Paris"
HEADER = display_timezone.DEFAULT_HEADER_NAME


def _chart_digest(time_zone: str | None) -> str | None:
    from superset import security_manager
    from superset.models.slice import Slice
    from superset.thumbnails.digest import get_chart_digest

    chart = Slice(id=2, params={"a": "b"})
    user = User(id=1, username="1")

    with (
        patch.dict(
            current_app.config,
            {
                "THUMBNAIL_EXECUTORS": [FixedExecutor("1")],
                "THUMBNAIL_CHART_DIGEST_FUNC": None,
                "DISPLAY_TIME_ZONE": time_zone,
            },
        ),
        patch.object(
            type(chart),
            "datasource",
            new_callable=PropertyMock,
            return_value=None,
        ),
        patch.object(security_manager, "find_user", return_value=user),
        override_user(user),
    ):
        display_timezone.clear_user_time_zone_cache()
        return get_chart_digest(chart=chart)


def test_digest_differs_per_time_zone() -> None:
    assert _chart_digest(TZ) != _chart_digest(OTHER_TZ)


def test_digest_is_unchanged_when_the_feature_is_off() -> None:
    """Enabling nothing must not invalidate every existing thumbnail."""
    assert _chart_digest(None) == _chart_digest("")


def test_digest_ignores_the_request_tier() -> None:
    """The screenshot worker sends no header, so the key must not depend on it."""
    from superset import security_manager
    from superset.models.slice import Slice
    from superset.thumbnails.digest import get_chart_digest

    chart = Slice(id=2, params={"a": "b"})
    user = User(id=1, username="1")

    def digest(headers: dict[str, str]) -> str | None:
        with (
            patch.dict(
                current_app.config,
                {
                    "THUMBNAIL_EXECUTORS": [FixedExecutor("1")],
                    "THUMBNAIL_CHART_DIGEST_FUNC": None,
                    "DISPLAY_TIME_ZONE": TZ,
                },
            ),
            patch.object(
                type(chart),
                "datasource",
                new_callable=PropertyMock,
                return_value=None,
            ),
            patch.object(security_manager, "find_user", return_value=user),
        ):
            with current_app.test_request_context("/thumbnail", headers=headers):
                with override_user(user):
                    display_timezone.clear_user_time_zone_cache()
                    return get_chart_digest(chart=chart)

    assert digest({}) == digest({HEADER: OTHER_TZ})


def test_executor_type_is_still_honored() -> None:
    """The time zone must be added on top of the existing key, not replace it."""
    from superset import security_manager
    from superset.models.slice import Slice
    from superset.thumbnails.digest import get_chart_digest

    chart = Slice(id=2, params={"a": "b"})

    def digest(user_id: int) -> str | None:
        user = User(id=user_id, username=str(user_id))
        with (
            patch.dict(
                current_app.config,
                {
                    "THUMBNAIL_EXECUTORS": [ExecutorType.CURRENT_USER],
                    "THUMBNAIL_CHART_DIGEST_FUNC": None,
                    "DISPLAY_TIME_ZONE": TZ,
                },
            ),
            patch.object(
                type(chart),
                "datasource",
                new_callable=PropertyMock,
                return_value=None,
            ),
            patch.object(security_manager, "find_user", return_value=user),
            override_user(user),
        ):
            display_timezone.clear_user_time_zone_cache()
            return get_chart_digest(chart=chart)

    assert digest(1) != digest(2)
