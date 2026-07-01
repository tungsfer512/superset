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
"""Tests for the generic REST resource bridge and its guards."""

import asyncio

import pytest

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import Settings
from superset_ai.tools import rest_tools
from superset_ai.tools.registry import execute_tool
from superset_ai.tools.rest_tools import RESOURCES, ResourceError
from tests.fakes import FakeSupersetClient

AUTH = SupersetAuth(authorization="Bearer x")


def test_security_resources_not_exposed():
    for forbidden in ("user", "role", "rls", "permission", "security"):
        assert forbidden not in RESOURCES


def test_list_builds_path_and_search():
    client = FakeSupersetClient()
    asyncio.run(
        rest_tools.list_resource(client, AUTH, resource="dashboard", search="sales")
    )
    method, path, params = client.last_call
    assert method == "GET"
    assert path == "/api/v1/dashboard/"
    assert "dashboard_title" in params["q"]  # search col encoded in RISON


def test_unknown_resource_rejected():
    with pytest.raises(ResourceError):
        asyncio.run(
            rest_tools.get_resource(
                FakeSupersetClient(), AUTH, resource="nope", object_id=1
            )
        )


def test_delete_requires_confirm():
    with pytest.raises(ResourceError, match="confirm"):
        asyncio.run(
            rest_tools.delete_resource(
                FakeSupersetClient(),
                AUTH,
                resource="chart",
                object_id=1,
                confirm=False,
            )
        )


def test_read_only_resource_cannot_be_written():
    with pytest.raises(ResourceError, match="read-only"):
        asyncio.run(
            rest_tools.create_resource(
                FakeSupersetClient(), AUTH, resource="query", payload={}
            )
        )


def test_execute_tool_write_gating():
    # Write disabled -> error, even for a valid resource.
    disabled = asyncio.run(
        execute_tool(
            "superset_create",
            {"resource": "dashboard", "payload": {"dashboard_title": "x"}},
            client=FakeSupersetClient(),
            auth=AUTH,
            settings=Settings(allow_write_tools=False),
        )
    )
    assert "error" in disabled

    # Enabled -> goes through.
    enabled = asyncio.run(
        execute_tool(
            "superset_create",
            {"resource": "dashboard", "payload": {"dashboard_title": "x"}},
            client=FakeSupersetClient(),
            auth=AUTH,
            settings=Settings(allow_write_tools=True),
        )
    )
    assert enabled.get("id") == 99


def test_api_path_allow_and_deny():
    # Allowed introspection / nested endpoints.
    assert (
        rest_tools.check_api_path("/api/v1/database/1/tables/")
        == "/api/v1/database/1/tables/"
    )
    assert rest_tools.check_api_path("/api/v1/dashboard/2/charts") is not None
    # Strips host + query.
    assert (
        rest_tools.check_api_path("http://x:8088/api/v1/chart/?q=(a:1)")
        == "/api/v1/chart/"
    )
    # Blocked: security / users / roles / logs / raw execute / non-api.
    for blocked in (
        "/api/v1/security/roles/",
        "/api/v1/users/",
        "/api/v1/rowlevelsecurity/",
        "/api/v1/log/",
        "/api/v1/sqllab/execute/",
        "/static/anything",
    ):
        with pytest.raises(ResourceError):
            rest_tools.check_api_path(blocked)


def test_api_get_reaches_allowed_path():
    client = FakeSupersetClient()
    asyncio.run(rest_tools.api_get(client, AUTH, path="/api/v1/database/1/tables/"))
    method, path, _ = client.last_call
    assert method == "GET"
    assert path == "/api/v1/database/1/tables/"


def test_api_request_delete_needs_confirm():
    with pytest.raises(ResourceError, match="confirm"):
        asyncio.run(
            rest_tools.api_request(
                FakeSupersetClient(),
                AUTH,
                method="DELETE",
                path="/api/v1/chart/1",
                confirm=False,
            )
        )


def test_api_request_blocks_security_even_with_write():
    result = asyncio.run(
        execute_tool(
            "superset_api_request",
            {"method": "POST", "path": "/api/v1/security/roles/", "body": {}},
            client=FakeSupersetClient(),
            auth=AUTH,
            settings=Settings(allow_write_tools=True),
        )
    )
    assert "error" in result


def test_execute_tool_delete_without_confirm_is_error():
    result = asyncio.run(
        execute_tool(
            "superset_delete",
            {"resource": "chart", "object_id": 5, "confirm": False},
            client=FakeSupersetClient(),
            auth=AUTH,
            settings=Settings(allow_write_tools=True),
        )
    )
    assert "error" in result
