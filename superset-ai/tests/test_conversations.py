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
"""Durable conversation history: store round-trips, scoping, and the API."""

import pytest
from fastapi.testclient import TestClient

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.deps import (
    get_llm,
    get_llm_optional,
    get_store,
    get_superset_client,
)
from superset_ai.main import create_app
from superset_ai.store import InMemoryConversationStore, SqliteConversationStore
from tests.fakes import FakeLLM, FakeSupersetClient, text_turn

AUTH = {"Authorization": "Bearer caller"}
# The store is keyed by the (hashed) caller identity, not the raw header.
USER_KEY = SupersetAuth(authorization="Bearer caller").identity()


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryConversationStore()
    return SqliteConversationStore(str(tmp_path / "conv.db"))


def test_store_round_trip_and_listing(store):
    assert store.get_messages("c1", "u1") == []
    store.append_messages(
        "c1",
        "u1",
        [
            {"role": "user", "text": "Xin chào", "artifacts": []},
            {"role": "assistant", "text": "Chào bạn!", "artifacts": [{"a": 1}]},
        ],
    )
    messages = store.get_messages("c1", "u1")
    assert [m["text"] for m in messages] == ["Xin chào", "Chào bạn!"]
    assert messages[1]["artifacts"] == [{"a": 1}]

    listing = store.list_conversations("u1")
    assert len(listing) == 1
    assert listing[0]["id"] == "c1"
    assert listing[0]["title"] == "Xin chào"
    assert listing[0]["message_count"] == 2


def test_store_is_user_scoped(store):
    store.append_messages("c1", "owner", [{"role": "user", "text": "secret"}])
    # Another user can neither read nor list it.
    assert store.get_messages("c1", "intruder") == []
    assert store.list_conversations("intruder") == []
    # And cannot append to it either.
    store.append_messages("c1", "intruder", [{"role": "user", "text": "inject"}])
    assert len(store.get_messages("c1", "owner")) == 1


def _app(llm, store):
    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_llm_optional] = lambda: llm
    app.dependency_overrides[get_superset_client] = lambda: FakeSupersetClient()
    app.dependency_overrides[get_store] = lambda: store
    return app


def test_conversations_api_list_and_get():
    store = InMemoryConversationStore()
    llm = FakeLLM([text_turn("Chào bạn.")])
    with TestClient(_app(llm, store)) as client:
        ask = client.post("/ask", json={"question": "Xin chào"}, headers=AUTH)
        cid = ask.json()["conversation_id"]

        listing = client.get("/conversations", headers=AUTH)
        assert listing.status_code == 200
        rows = listing.json()
        assert len(rows) == 1
        assert rows[0]["id"] == cid
        assert rows[0]["title"] == "Xin chào"

        detail = client.get(f"/conversations/{cid}", headers=AUTH)
        assert detail.status_code == 200
        messages = detail.json()["messages"]
        assert messages[0]["text"] == "Xin chào"
        assert messages[1]["text"] == "Chào bạn."


def test_suggestions_default_when_no_history():
    store = InMemoryConversationStore()
    llm = FakeLLM([])  # not consulted when there's no history
    with TestClient(_app(llm, store)) as client:
        resp = client.get("/suggestions", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["generated"] is False
    assert len(body["suggestions"]) == 3


def test_suggestions_inferred_from_history():
    store = InMemoryConversationStore()
    store.append_messages(
        "c1", USER_KEY, [{"role": "user", "text": "Doanh thu theo tháng"}]
    )
    llm = FakeLLM(
        [
            text_turn(
                '["Doanh thu theo quý?", "Top sản phẩm bán chạy?", "So sánh 2 năm?"]'
            )
        ]
    )
    with TestClient(_app(llm, store)) as client:
        resp = client.get("/suggestions", headers=AUTH)
    body = resp.json()
    assert body["generated"] is True
    assert "Doanh thu theo quý?" in body["suggestions"]
    assert len(body["suggestions"]) == 3


def test_suggestions_fall_back_to_titles_without_llm():
    store = InMemoryConversationStore()
    store.append_messages(
        "c1", USER_KEY, [{"role": "user", "text": "Câu hỏi cũ của tôi"}]
    )
    app = create_app()
    app.dependency_overrides[get_superset_client] = lambda: FakeSupersetClient()
    app.dependency_overrides[get_store] = lambda: store
    # No get_llm override -> app.state.llm is None -> re-surface past questions.
    with TestClient(app) as client:
        resp = client.get("/suggestions", headers=AUTH)
    body = resp.json()
    assert body["generated"] is False
    assert body["suggestions"] == ["Câu hỏi cũ của tôi"]


def test_followup_replays_prior_turns_for_context():
    store = InMemoryConversationStore()
    # One assistant turn per /ask call (no tools).
    llm = FakeLLM([text_turn("Đáp 1."), text_turn("Đáp 2.")])
    with TestClient(_app(llm, store)) as client:
        first = client.post("/ask", json={"question": "Câu 1"}, headers=AUTH)
        cid = first.json()["conversation_id"]
        client.post(
            "/ask",
            json={"question": "Câu 2", "conversation_id": cid},
            headers=AUTH,
        )

    # The second LLM call must have seen the first Q&A replayed as context.
    second_call_texts = [
        m.get("content") for m in llm.calls[1]["messages"] if isinstance(m, dict)
    ]
    assert "Câu 1" in second_call_texts
    assert "Đáp 1." in second_call_texts
    assert any("Câu 2" in str(t) for t in second_call_texts)
