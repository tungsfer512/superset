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
"""Tests for the LLM tool-use orchestrator (fake LLM, no network)."""

import asyncio

import pytest

from superset_ai import orchestrator
from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import Settings
from superset_ai.sql.guard import UnsafeSqlError
from superset_ai.store import InMemoryConversationStore
from tests.fakes import FakeLLM, FakeSupersetClient, text_turn, tool_turn

AUTH = SupersetAuth(authorization="Bearer caller")
SETTINGS = Settings()


def test_ask_runs_tool_then_answers():
    llm = FakeLLM(
        [
            tool_turn(
                "t1",
                "run_select_sql",
                {"database_id": 7, "sql": "SELECT * FROM orders"},
            ),
            text_turn("Có 1 dòng dữ liệu."),
        ]
    )
    client = FakeSupersetClient()
    store = InMemoryConversationStore()

    result = asyncio.run(
        orchestrator.ask(
            llm,
            client,
            AUTH,
            SETTINGS,
            question="Có bao nhiêu đơn hàng?",
            store=store,
        )
    )

    assert result.answer == "Có 1 dòng dữ liệu."
    assert len(result.artifacts) == 1
    assert result.artifacts[0]["row_count"] == 1
    assert "LIMIT" in (client.last_sql or "").upper()  # limit enforced
    assert client.last_auth.authorization == "Bearer caller"  # pass-through
    # The transcript was persisted under the generated conversation id.
    assert store.get(result.conversation_id)


def test_ask_continues_after_tool_error():
    # First the model runs an invalid query (guard rejects -> error tool result),
    # then it recovers and answers.
    llm = FakeLLM(
        [
            tool_turn(
                "t1", "run_select_sql", {"database_id": 7, "sql": "DROP TABLE x"}
            ),
            text_turn("Mình không thể chạy lệnh đó, chỉ hỗ trợ SELECT."),
        ]
    )
    result = asyncio.run(
        orchestrator.ask(
            llm,
            FakeSupersetClient(),
            AUTH,
            SETTINGS,
            question="xoá bảng",
            store=InMemoryConversationStore(),
        )
    )
    assert "SELECT" in result.answer
    assert result.artifacts == []  # the unsafe query produced no artifact


def test_generate_sql_strips_fences_and_validates():
    llm = FakeLLM([text_turn("```sql\nSELECT id FROM orders\n```")])
    sql = asyncio.run(
        orchestrator.generate_sql(
            llm,
            FakeSupersetClient(),
            AUTH,
            SETTINGS,
            question="liệt kê id đơn hàng",
        )
    )
    assert sql == "SELECT id FROM orders"


def test_generate_sql_rejects_non_select():
    llm = FakeLLM([text_turn("DELETE FROM orders")])
    with pytest.raises(UnsafeSqlError):
        asyncio.run(
            orchestrator.generate_sql(
                llm, FakeSupersetClient(), AUTH, SETTINGS, question="xoá"
            )
        )
