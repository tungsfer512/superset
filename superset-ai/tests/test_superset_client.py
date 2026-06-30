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
"""Tests for the Superset HTTP client using a mocked transport (no network)."""

import asyncio

import httpx

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.superset_client import SupersetClient
from superset_ai.superset_client.client import CSRF_PATH, SQLLAB_EXECUTE_PATH


def test_list_datasets_sends_rison_and_token():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["q"] = request.url.params.get("q")
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "count": 1,
                "result": [
                    {
                        "id": 1,
                        "table_name": "orders",
                        "schema": "public",
                        "database": {"database_name": "main"},
                    }
                ],
            },
        )

    async def scenario() -> dict:
        client = SupersetClient(
            "http://superset", transport=httpx.MockTransport(handler)
        )
        try:
            return await client.list_datasets(
                SupersetAuth(authorization="Bearer t0ken"), search="ord"
            )
        finally:
            await client.aclose()

    payload = asyncio.run(scenario())

    assert seen["path"] == "/api/v1/dataset/"
    assert seen["q"] is not None  # RISON-encoded query present
    assert seen["authorization"] == "Bearer t0ken"  # token pass-through
    assert payload["count"] == 1


def test_execute_sql_fetches_csrf_for_cookie_session():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == CSRF_PATH:
            return httpx.Response(200, json={"result": "csrf-123"})
        if request.url.path == SQLLAB_EXECUTE_PATH:
            assert request.headers.get("x-csrftoken") == "csrf-123"
            assert request.headers.get("cookie") == "session=abc"
            return httpx.Response(
                200, json={"columns": [{"name": "n"}], "data": [{"n": 1}]}
            )
        return httpx.Response(404)

    async def scenario() -> dict:
        client = SupersetClient(
            "http://superset", transport=httpx.MockTransport(handler)
        )
        try:
            return await client.execute_sql(
                SupersetAuth(cookie="session=abc"),
                database_id=7,
                sql="SELECT 1",
            )
        finally:
            await client.aclose()

    payload = asyncio.run(scenario())

    assert ("GET", CSRF_PATH) in calls
    assert ("POST", SQLLAB_EXECUTE_PATH) in calls
    assert payload["data"] == [{"n": 1}]
