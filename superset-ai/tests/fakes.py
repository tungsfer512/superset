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
"""Shared test doubles (no network, no real LLM)."""

from __future__ import annotations

from superset_ai.llm.base import LlmResult, ToolResult, ToolUse


class FakeLLM:
    """Returns a scripted sequence of LlmResults; records calls."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    async def complete(self, *, system, messages, tools=None, max_tokens=None):
        self.calls.append({"system": system, "messages": list(messages)})
        return self._results.pop(0)

    def user_message(self, text):
        return {"role": "user", "content": text}

    def tool_result_message(self, results):
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": r.tool_use_id,
                        "content": r.content,
                    }
                    for r in results
                ],
            }
        ]


def text_turn(text: str) -> LlmResult:
    """A final assistant turn carrying plain text."""
    return LlmResult(
        text=text,
        stop_reason="end_turn",
        assistant_message={"role": "assistant", "content": text},
    )


def tool_turn(tool_use_id: str, name: str, tool_input: dict) -> LlmResult:
    """An assistant turn requesting a single tool call."""
    return LlmResult(
        text="",
        tool_uses=[ToolUse(id=tool_use_id, name=name, input=tool_input)],
        stop_reason="tool_use",
        assistant_message={"role": "assistant", "content": []},
    )


# Keep a reference so linters see ToolResult is part of the fake contract.
_ = ToolResult


class FakeSupersetClient:
    """Canned Superset responses; records the last auth and SQL seen."""

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
