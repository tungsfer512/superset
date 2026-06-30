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
"""Tests for the Phase-1 data endpoints with a fake (no-network) client."""

import pytest
from fastapi.testclient import TestClient

from superset_ai.deps import get_superset_client
from superset_ai.main import create_app

AUTH_HEADER = {"Authorization": "Bearer caller-token"}


class FakeClient:
    """Records auth and returns canned Superset payloads."""

    def __init__(self):
        self.last_auth = None
        self.last_sql = None

    async def list_datasets(self, auth, *, search=None, page=0, page_size=100):
        self.last_auth = auth
        return {
            "count": 1,
            "result": [
                {
                    "id": 1,
                    "table_name": "orders",
                    "schema": "public",
                    "database": {"database_name": "main"},
                }
            ],
        }

    async def get_dataset(self, auth, dataset_id):
        self.last_auth = auth
        return {
            "result": {
                "table_name": "orders",
                "schema": "public",
                "database": {"id": 7, "backend": "mysql"},
                "columns": [{"column_name": "id", "type": "INT", "description": None}],
            }
        }

    async def execute_sql(self, auth, *, database_id, sql, schema=None, row_limit=None):
        self.last_auth = auth
        self.last_sql = sql
        return {"columns": [{"name": "n"}], "data": [{"n": 1}]}


@pytest.fixture
def fake_client():
    return FakeClient()


@pytest.fixture
def client(fake_client):
    app = create_app()
    app.dependency_overrides[get_superset_client] = lambda: fake_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_datasets_passes_token_through(client, fake_client):
    resp = client.get("/datasets", headers=AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["datasets"][0]["database"] == "main"
    assert fake_client.last_auth.authorization == "Bearer caller-token"


def test_requires_auth():
    app = create_app()
    with TestClient(app) as test_client:
        assert test_client.get("/datasets").status_code == 401


def test_dataset_schema(client):
    resp = client.get("/datasets/1/schema", headers=AUTH_HEADER)
    assert resp.status_code == 200
    body = resp.json()
    assert body["database_id"] == 7
    assert body["columns"][0]["name"] == "id"


def test_run_sql_blocks_non_select(client):
    resp = client.post(
        "/sql/run",
        json={"database_id": 7, "sql": "DROP TABLE orders"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_run_sql_enforces_limit(client, fake_client):
    resp = client.post(
        "/sql/run",
        json={"database_id": 7, "sql": "SELECT * FROM orders"},
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 200
    assert "LIMIT" in resp.json()["executed_sql"].upper()
    assert "LIMIT" in (fake_client.last_sql or "").upper()
