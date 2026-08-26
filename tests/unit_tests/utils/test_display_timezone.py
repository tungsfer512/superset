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
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from flask import current_app

from superset.utils import display_timezone

TZ = "Asia/Ho_Chi_Minh"


def _database(extra: dict | None = None) -> mock.Mock:
    database = mock.Mock()
    database.get_extra.return_value = extra if extra is not None else {}
    return database


def test_get_time_zone_unset() -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": None}):
        assert display_timezone.get_time_zone() is None


def test_get_time_zone_from_config() -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        assert display_timezone.get_time_zone() == TZ


def test_get_time_zone_unknown_is_ignored() -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": "Not/AZone"}):
        assert display_timezone.get_time_zone() is None


def test_get_time_zone_database_override() -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        assert display_timezone.get_time_zone(_database()) == TZ
        assert (
            display_timezone.get_time_zone(_database({"display_time_zone": "UTC"}))
            == "UTC"
        )
        # an explicit null opts the database out entirely
        assert (
            display_timezone.get_time_zone(_database({"display_time_zone": None}))
            is None
        )


@pytest.mark.parametrize(
    "time_zone,offset,minutes",
    [
        (TZ, "+07:00", 420),
        ("UTC", "+00:00", 0),
        ("Asia/Kathmandu", "+05:45", 345),
    ],
)
def test_utc_offset(time_zone: str, offset: str, minutes: int) -> None:
    assert display_timezone.format_utc_offset(time_zone) == offset
    assert display_timezone.get_utc_offset_minutes(time_zone) == minutes


def test_now_is_naive_wall_clock() -> None:
    naive = display_timezone.now(TZ)
    assert naive.tzinfo is None
    aware = datetime.now(tz=display_timezone.get_zone_info(TZ))
    assert abs((naive - aware.replace(tzinfo=None)).total_seconds()) < 5


def test_to_utc() -> None:
    # midnight in Ho Chi Minh City is 17:00 the previous day in UTC
    assert display_timezone.to_utc(datetime(2026, 8, 21), TZ) == datetime(
        2026, 8, 20, 17
    )
    assert display_timezone.to_utc(datetime(2026, 8, 21), None) == datetime(2026, 8, 21)


def test_to_epoch_seconds() -> None:
    expected = int(datetime(2026, 8, 20, 17, tzinfo=timezone.utc).timestamp())
    assert display_timezone.to_epoch_seconds(datetime(2026, 8, 21), TZ) == expected


@pytest.mark.parametrize(
    "type_,expected",
    [
        ("TIMESTAMP WITH TIME ZONE", True),
        ("timestamptz", True),
        ("TIMESTAMP", False),
        ("DATETIME", False),
        (None, False),
    ],
)
def test_is_tz_aware_type(type_: str | None, expected: bool) -> None:
    assert display_timezone.is_tz_aware_type(type_) is expected


def test_is_tz_aware_type_from_sqla_type() -> None:
    from sqlalchemy import types

    assert display_timezone.is_tz_aware_type(
        "TIMESTAMP", types.TIMESTAMP(timezone=True)
    )


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"type_": "TIMESTAMP"}, True),
        ({"type_": "DATETIME"}, True),
        # a calendar date has no time-of-day to carry the offset
        ({"type_": "DATE"}, False),
        # Superset parses these from strings itself
        ({"type_": "VARCHAR", "python_date_format": "%Y-%m-%d"}, False),
        # ...except epoch columns, which are decoded into real timestamps
        ({"type_": "BIGINT", "python_date_format": "epoch_s"}, True),
        ({"type_": "BIGINT", "python_date_format": "epoch_ms"}, True),
        (
            {"type_": "TIMESTAMP", "extra": {"skip_time_zone_conversion": True}},
            False,
        ),
    ],
)
def test_is_convertible_column(kwargs: dict, expected: bool) -> None:
    assert display_timezone.is_convertible_column(**kwargs) is expected


def test_reference_now_follows_the_display_zone() -> None:
    from superset.utils.date_parser import reference_now

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": "UTC"}):
        in_utc = reference_now()
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        in_saigon = reference_now()
    assert round((in_saigon - in_utc).total_seconds() / 60) == 420


def test_relative_range_is_midnight_in_the_display_zone() -> None:
    from superset.utils.date_parser import get_since_until

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        since, until = get_since_until("Last day")

    today = display_timezone.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    assert until == today
    assert since == today - timedelta(days=1)
