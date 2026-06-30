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
"""Tests for /ask and /ask/stream with a fake LLM and fake Superset client."""

from fastapi.testclient import TestClient

from superset_ai.deps import get_llm, get_superset_client
from superset_ai.main import create_app
from tests.fakes import FakeLLM, FakeSupersetClient, text_turn, tool_turn

AUTH = {"Authorization": "Bearer caller"}


def _app(llm):
    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_superset_client] = lambda: FakeSupersetClient()
    return app


def test_ask_returns_answer_and_artifacts():
    llm = FakeLLM(
        [
            tool_turn("t1", "run_select_sql", {"database_id": 7, "sql": "SELECT 1"}),
            text_turn("Kết quả là 1."),
        ]
    )
    with TestClient(_app(llm)) as client:
        resp = client.post("/ask", json={"question": "1 + 0 = ?"}, headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Kết quả là 1."
    assert body["conversation_id"]
    assert len(body["artifacts"]) == 1


def test_ask_requires_llm_configured():
    # No override -> app.state.llm is None -> 503.
    app = create_app()
    app.dependency_overrides[get_superset_client] = lambda: FakeSupersetClient()
    with TestClient(app) as client:
        resp = client.post("/ask", json={"question": "x"}, headers=AUTH)
    assert resp.status_code == 503


def test_ask_stream_emits_sse_events():
    llm = FakeLLM(
        [
            tool_turn("t1", "run_select_sql", {"database_id": 7, "sql": "SELECT 1"}),
            text_turn("Xong."),
        ]
    )
    with TestClient(_app(llm)) as client:
        resp = client.post("/ask/stream", json={"question": "chạy thử"}, headers=AUTH)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "event: start" in body
    assert "event: tool" in body
    assert "event: answer" in body
    assert "event: done" in body
