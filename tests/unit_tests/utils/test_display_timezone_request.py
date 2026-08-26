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
"""The per-request tier of the ``DISPLAY_TIME_ZONE`` resolution.

This is what embedded dashboards use: the host application states the viewer's
zone as a ``?timezone=`` URL parameter, and the embedded page forwards it as a
header on the API calls it makes.
"""

from unittest import mock

from flask import current_app
from flask_appbuilder.security.sqla.models import User

from superset import db
from superset.daos.user import UserDAO
from superset.utils import display_timezone
from superset.utils.core import override_user
from tests.unit_tests.fixtures.common import admin_user, after_each  # noqa: F401

TZ = "Asia/Ho_Chi_Minh"
OTHER_TZ = "Europe/Paris"
THIRD_TZ = "America/New_York"
HEADER = display_timezone.DEFAULT_HEADER_NAME


def _database(extra: dict | None = None) -> mock.Mock:
    database = mock.Mock()
    database.get_extra.return_value = extra if extra is not None else {}
    return database


def test_no_request_context_is_a_noop() -> None:
    assert display_timezone.get_request_time_zone() is None


def test_url_parameter_is_read() -> None:
    """How the embedded page itself is rendered: /embedded/<uuid>?timezone=..."""
    with current_app.test_request_context(f"/embedded/abc?timezone={OTHER_TZ}"):
        assert display_timezone.get_request_time_zone() == OTHER_TZ


def test_header_is_read() -> None:
    """How the API calls that page makes afterwards carry the zone."""
    with current_app.test_request_context(
        "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
    ):
        assert display_timezone.get_request_time_zone() == OTHER_TZ


def test_header_wins_over_the_url_parameter() -> None:
    with current_app.test_request_context(
        f"/embedded/abc?timezone={THIRD_TZ}", headers={HEADER: OTHER_TZ}
    ):
        assert display_timezone.get_request_time_zone() == OTHER_TZ


def test_header_name_is_configurable() -> None:
    with mock.patch.dict(
        current_app.config, {"DISPLAY_TIME_ZONE_HEADER_NAME": "X-Tenant-TZ"}
    ):
        assert display_timezone.get_header_name() == "X-Tenant-TZ"
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={"X-Tenant-TZ": OTHER_TZ}
        ):
            assert display_timezone.get_request_time_zone() == OTHER_TZ
            # the default name is no longer honored
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            assert display_timezone.get_request_time_zone() is None


def test_request_zone_wins_over_the_default() -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            assert display_timezone.get_time_zone() == OTHER_TZ


def test_request_zone_wins_over_a_user_preference(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """The host application knows where the viewer actually is."""
    UserDAO.set_display_time_zone(admin_user, THIRD_TZ)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            with override_user(admin_user):
                display_timezone.clear_user_time_zone_cache()
                assert display_timezone.get_time_zone() == OTHER_TZ


def test_unknown_request_zone_is_ignored() -> None:
    """The value is client-supplied, so it must be validated."""
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: "Not/AZone"}
        ):
            assert display_timezone.get_request_time_zone() is None
            assert display_timezone.get_time_zone() == TZ


def test_request_zone_cannot_enable_a_disabled_instance() -> None:
    """A client must not switch on conversion for data that may not be UTC."""
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": None}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            assert display_timezone.get_time_zone() is None


def test_request_zone_cannot_override_a_database_opt_out() -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            database = _database({"display_time_zone": None})
            assert display_timezone.get_time_zone(database) is None


def test_dataset_cache_key_differs_per_request_zone() -> None:
    """Otherwise a viewer in one zone would be served another's results."""
    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.models.core import Database

    dataset = SqlaTable(
        table_name="events",
        database=Database(
            database_name="pg",
            sqlalchemy_uri="postgresql://user:password@localhost:5432/db",
        ),
        columns=[TableColumn(column_name="ts", type="TIMESTAMP", is_dttm=True)],
        metrics=[],
    )
    query_obj: dict = {"metrics": [], "columns": [], "filter": []}

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            embedded_keys = dataset.get_extra_cache_keys(query_obj)
        with current_app.test_request_context("/api/v1/chart/data"):
            default_keys = dataset.get_extra_cache_keys(query_obj)

    assert f"tz:{OTHER_TZ}" in embedded_keys
    assert f"tz:{TZ}" in default_keys
    assert embedded_keys != default_keys


def test_generated_sql_uses_the_request_zone() -> None:
    """End to end: the zone reaches the SQL the embedded dashboard runs."""
    from sqlalchemy.dialects import postgresql

    from superset.connectors.sqla.models import SqlaTable, TableColumn
    from superset.models.core import Database

    dataset = SqlaTable(
        table_name="events",
        schema="public",
        database=Database(
            database_name="pg",
            sqlalchemy_uri="postgresql://user:password@localhost:5432/db",
        ),
        columns=[TableColumn(column_name="ts", type="TIMESTAMP", is_dttm=True)],
        metrics=[],
    )

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with current_app.test_request_context(
            "/api/v1/chart/data", headers={HEADER: OTHER_TZ}
        ):
            sqla_query = dataset.get_sqla_query(
                columns=["ts"],
                groupby=["ts"],
                metrics=[],
                filter=[],
                is_timeseries=False,
                row_limit=100,
            ).sqla_query

    sql = str(sqla_query.compile(dialect=postgresql.dialect()))
    assert f"AT TIME ZONE 'UTC' AT TIME ZONE '{OTHER_TZ}'" in sql
