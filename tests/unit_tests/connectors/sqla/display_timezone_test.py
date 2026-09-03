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
"""End-to-end SQL generated for a dataset when ``DISPLAY_TIME_ZONE`` is set."""

from datetime import datetime
from unittest import mock

import pytest
from flask import current_app
from sqlalchemy.dialects import postgresql

from superset.connectors.sqla.models import SqlaTable, TableColumn
from superset.models.core import Database

TZ = "Asia/Ho_Chi_Minh"
CONVERTED = "ts AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh'"


@pytest.fixture
def dataset() -> SqlaTable:
    database = Database(
        database_name="pg",
        sqlalchemy_uri="postgresql://user:password@localhost:5432/db",
    )
    return SqlaTable(
        table_name="events",
        schema="public",
        database=database,
        columns=[
            TableColumn(column_name="ts", type="TIMESTAMP", is_dttm=True),
            TableColumn(
                column_name="ts_tz", type="TIMESTAMP WITH TIME ZONE", is_dttm=True
            ),
            TableColumn(column_name="day", type="DATE", is_dttm=True),
            TableColumn(column_name="name", type="VARCHAR"),
        ],
        metrics=[],
    )


def _sql(dataset: SqlaTable, **query) -> str:
    query.setdefault("is_timeseries", False)
    query.setdefault("metrics", [])
    query.setdefault("row_limit", 100)
    query.setdefault("filter", [])
    sqla_query = dataset.get_sqla_query(**query).sqla_query
    return str(
        sqla_query.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_time_grain_truncates_in_the_target_zone(dataset: SqlaTable) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(
            dataset,
            granularity="ts",
            extras={"time_grain_sqla": "P1D"},
            columns=["ts"],
            groupby=["ts"],
            is_timeseries=True,
        )
    assert f"DATE_TRUNC('day', ({CONVERTED}))" in sql


def test_time_filter_uses_the_converted_column(dataset: SqlaTable) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(
            dataset,
            granularity="ts",
            from_dttm=datetime(2026, 8, 21),
            to_dttm=datetime(2026, 8, 22),
            columns=["name"],
            groupby=["name"],
        )
    # the bound is a plain local literal, compared against the converted column
    assert f"({CONVERTED}) >= TO_TIMESTAMP('2026-08-21 00:00:00.000000'" in sql
    assert f"({CONVERTED}) < TO_TIMESTAMP('2026-08-22 00:00:00.000000'" in sql


def test_temporal_column_as_a_dimension_is_converted(dataset: SqlaTable) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(dataset, columns=["ts"], groupby=["ts"])
    assert CONVERTED in sql


def test_date_only_column_is_left_alone(dataset: SqlaTable) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(dataset, columns=["day"], groupby=["day"])
    assert "AT TIME ZONE" not in sql


def test_non_temporal_column_is_left_alone(dataset: SqlaTable) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(dataset, columns=["name"], groupby=["name"])
    assert "AT TIME ZONE" not in sql


def test_column_opt_out(dataset: SqlaTable) -> None:
    dataset.columns[0].extra = '{"skip_time_zone_conversion": true}'
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(dataset, columns=["ts"], groupby=["ts"])
    assert "AT TIME ZONE" not in sql


def test_database_opt_out(dataset: SqlaTable) -> None:
    dataset.database.extra = '{"display_time_zone": null}'
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(dataset, columns=["ts"], groupby=["ts"])
    assert "AT TIME ZONE" not in sql


def test_disabled_by_default(dataset: SqlaTable) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": None}):
        sql = _sql(
            dataset,
            granularity="ts",
            extras={"time_grain_sqla": "P1D"},
            columns=["ts"],
            groupby=["ts"],
            is_timeseries=True,
        )
    assert "AT TIME ZONE" not in sql
    assert "DATE_TRUNC('day', ts)" in sql


def test_tz_aware_column_is_converted_once(dataset: SqlaTable) -> None:
    """A timestamptz column already carries its zone: reading it as UTC first
    would shift it twice. This goes through the same path a real dataset does,
    where the SQLAlchemy type has lost the distinction.
    """
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        sql = _sql(
            dataset,
            granularity="ts_tz",
            extras={"time_grain_sqla": "P1D"},
            columns=["ts_tz"],
            groupby=["ts_tz"],
            is_timeseries=True,
        )
    assert "DATE_TRUNC('day', (ts_tz AT TIME ZONE 'Asia/Ho_Chi_Minh'))" in sql
    assert "AT TIME ZONE 'UTC'" not in sql
