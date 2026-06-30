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
"""Tests for /sql/generate, /sql/explain, /sql/fix."""

from fastapi.testclient import TestClient

from superset_ai.deps import get_llm, get_superset_client
from superset_ai.main import create_app
from tests.fakes import FakeLLM, FakeSupersetClient, text_turn

AUTH = {"Authorization": "Bearer caller"}


def _app(llm):
    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_superset_client] = lambda: FakeSupersetClient()
    return app


def test_generate_returns_sql():
    with TestClient(_app(FakeLLM([text_turn("SELECT id FROM orders")]))) as client:
        resp = client.post("/sql/generate", json={"question": "ids"}, headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["sql"] == "SELECT id FROM orders"


def test_generate_rejects_unsafe_sql():
    with TestClient(_app(FakeLLM([text_turn("DROP TABLE orders")]))) as client:
        resp = client.post("/sql/generate", json={"question": "drop"}, headers=AUTH)
    assert resp.status_code == 422


def test_explain_returns_text():
    with TestClient(_app(FakeLLM([text_turn("Truy vấn đếm số đơn hàng.")]))) as client:
        resp = client.post(
            "/sql/explain",
            json={"sql": "SELECT count(*) FROM orders"},
            headers=AUTH,
        )
    assert resp.status_code == 200
    assert "đơn hàng" in resp.json()["explanation"]


def test_fix_returns_corrected_select():
    with TestClient(_app(FakeLLM([text_turn("SELECT * FROM orders")]))) as client:
        resp = client.post(
            "/sql/fix",
            json={"sql": "SELET * FROM orders", "error": "syntax error"},
            headers=AUTH,
        )
    assert resp.status_code == 200
    assert resp.json()["sql"] == "SELECT * FROM orders"
