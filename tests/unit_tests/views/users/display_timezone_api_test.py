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
"""Reading and writing the current user's display timezone over the API."""

import re
from typing import Any

import pytest
from flask_appbuilder.security.sqla.models import Role, User
from pytest_mock import MockerFixture

from superset import db
from superset.daos.user import UserDAO
from superset.views.users.schemas import CurrentUserPutSchema

TZ = "Asia/Ho_Chi_Minh"


@pytest.fixture
def logged_in_user(
    mocker: MockerFixture,
    request: pytest.FixtureRequest,
) -> User:
    """A committed user that ``g.user`` resolves to inside the test client.

    The endpoint under test commits, so this cannot lean on the shared
    rollback-per-test fixture. Rather than unpick the self-referential audit
    foreign keys on ``ab_user`` to delete it again, each test gets its own name;
    the rows go away with the in-memory metadata database.
    """
    slug = re.sub(r"\W+", "_", request.node.name)[:48]
    role = db.session.query(Role).filter_by(name="Admin").one()
    user = User(
        first_name="Tina",
        last_name="Tester",
        email=f"{slug}@example.org",
        username=slug,
        roles=[role],
    )
    db.session.add(user)
    db.session.commit()
    mocker.patch("flask_login.utils._get_user", return_value=user)
    return user


def test_schema_accepts_a_known_zone() -> None:
    assert CurrentUserPutSchema().load({"display_time_zone": TZ}) == {
        "display_time_zone": TZ
    }


def test_schema_accepts_an_empty_string_to_clear() -> None:
    assert CurrentUserPutSchema().load({"display_time_zone": ""}) == {
        "display_time_zone": ""
    }


def test_schema_rejects_an_unknown_zone() -> None:
    from marshmallow import ValidationError

    with pytest.raises(ValidationError) as excinfo:
        CurrentUserPutSchema().load({"display_time_zone": "Not/AZone"})
    assert "display_time_zone" in excinfo.value.messages


def test_get_me_reports_the_preference(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    UserDAO.set_display_time_zone(logged_in_user, TZ)
    db.session.flush()

    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    assert response.json["result"]["display_time_zone"] == TZ


def test_get_me_reports_an_empty_preference(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    assert response.json["result"]["display_time_zone"] == ""


def test_put_me_stores_the_preference(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    response = client.put("/api/v1/me/", json={"display_time_zone": TZ})
    assert response.status_code == 200
    assert response.json["result"]["display_time_zone"] == TZ
    assert UserDAO.get_display_time_zone(logged_in_user) == TZ


def test_put_me_clears_the_preference(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    UserDAO.set_display_time_zone(logged_in_user, TZ)
    db.session.flush()

    response = client.put("/api/v1/me/", json={"display_time_zone": ""})
    assert response.status_code == 200
    assert response.json["result"]["display_time_zone"] == ""
    assert UserDAO.get_display_time_zone(logged_in_user) is None


def test_put_me_rejects_an_unknown_zone(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    response = client.put("/api/v1/me/", json={"display_time_zone": "Not/AZone"})
    assert response.status_code == 400
    assert "display_time_zone" in response.json["message"]
    assert UserDAO.get_display_time_zone(logged_in_user) is None


def test_timezones_endpoint_lists_what_the_schema_accepts(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    """The picker must not be able to offer a value the API would reject.

    Browsers report a different set of canonical IANA names than the server
    does -- `Asia/Saigon` there, `Asia/Ho_Chi_Minh` here -- so the list has to
    come from the server.
    """
    response = client.get("/api/v1/me/timezones/")
    assert response.status_code == 200

    zones = response.json["result"]
    names = [zone["name"] for zone in zones]
    assert TZ in names
    assert {"name": TZ, "offset": "+07:00"} in zones
    # ordered by offset, so the picker reads sensibly
    assert [zone["offset"] for zone in zones] == sorted(
        zone["offset"] for zone in zones
    )
    # every option is accepted by the field that consumes it
    for name in (names[0], TZ, names[-1]):
        assert CurrentUserPutSchema().load({"display_time_zone": name}) == {
            "display_time_zone": name
        }


def test_put_me_leaves_other_fields_alone(
    client: Any,
    full_api_access: None,
    logged_in_user: User,
) -> None:
    response = client.put(
        "/api/v1/me/",
        json={"first_name": "Alicia", "display_time_zone": TZ},
    )
    assert response.status_code == 200
    assert response.json["result"]["first_name"] == "Alicia"
    assert response.json["result"]["display_time_zone"] == TZ
