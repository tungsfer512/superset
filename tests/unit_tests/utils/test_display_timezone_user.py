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
"""The per-user tier of the ``DISPLAY_TIME_ZONE`` resolution."""

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


def _database(extra: dict | None = None) -> mock.Mock:
    database = mock.Mock()
    database.get_extra.return_value = extra if extra is not None else {}
    return database


def test_user_preference_wins_over_the_default(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_time_zone() == OTHER_TZ
            # ...while the configured tier is untouched
            assert display_timezone.get_configured_time_zone() == TZ


def test_user_without_a_preference_falls_back(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_user_time_zone() is None
            assert display_timezone.get_time_zone() == TZ


def test_user_preference_cannot_enable_a_disabled_instance(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """A user must not switch on conversion for data that may not be UTC."""
    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": None}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_time_zone() is None


def test_user_preference_cannot_override_a_database_opt_out(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            database = _database({"display_time_zone": None})
            assert display_timezone.get_time_zone(database) is None


def test_unknown_stored_zone_is_ignored(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    UserDAO.set_display_time_zone(admin_user, "Not/AZone")
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_time_zone() == TZ


def test_no_user_falls_back_to_the_default(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """Celery tasks without a user, anonymous browsing, guest tokens."""
    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(None):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_user_time_zone() is None
            assert display_timezone.get_time_zone() == TZ


def test_guest_user_falls_back_to_the_default() -> None:
    """A `GuestUser` is not an ORM row and reports `is_anonymous` as False."""
    from superset.security.guest_token import GuestUser

    guest = GuestUser(
        token={"user": {"username": "guest"}, "resources": []},  # type: ignore[arg-type]
        roles=[],
    )
    assert guest.is_anonymous is False
    assert UserDAO.get_display_time_zone(guest) is None

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(guest):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_user_time_zone() is None
            assert display_timezone.get_time_zone() == TZ


def test_cache_is_keyed_on_the_user(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """`override_user` swaps users inside one application context."""
    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()

    other = User(
        first_name="Bob",
        last_name="Viewer",
        email="bob_viewer@example.org",
        username="bob_viewer",
        roles=list(admin_user.roles),
    )
    db.session.add(other)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            assert display_timezone.get_time_zone() == OTHER_TZ
        with override_user(other):
            # no explicit cache clear: the memo must notice the user changed
            assert display_timezone.get_time_zone() == TZ


def test_clearing_the_preference(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()
    assert UserDAO.get_display_time_zone(admin_user) == OTHER_TZ

    UserDAO.set_display_time_zone(admin_user, "")
    db.session.flush()
    assert UserDAO.get_display_time_zone(admin_user) is None


def test_dataset_cache_key_differs_per_user(
    admin_user: User,  # noqa: F811
    after_each: None,  # noqa: F811
) -> None:
    """Otherwise a user in one zone would be served another user's results."""
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

    UserDAO.set_display_time_zone(admin_user, OTHER_TZ)
    db.session.flush()

    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": TZ}):
        with override_user(admin_user):
            display_timezone.clear_user_time_zone_cache()
            user_keys = dataset.get_extra_cache_keys(query_obj)
        with override_user(None):
            display_timezone.clear_user_time_zone_cache()
            default_keys = dataset.get_extra_cache_keys(query_obj)

    assert f"tz:{OTHER_TZ}" in user_keys
    assert f"tz:{TZ}" in default_keys
    assert user_keys != default_keys
