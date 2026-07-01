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
"""OpenAI (GPT) implementation of :class:`~superset_ai.llm.base.LlmClient`.

Uses the Chat Completions API with function/tool calling. The SDK objects are
treated as ``Any`` so the connector stays decoupled from SDK type churn.
"""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from superset_ai.llm.base import LlmResult, ToolResult, ToolUse


class OpenAIClient:
    """Thin wrapper over the OpenAI Chat Completions API with tool use."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096) -> None:
        self._client: Any = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    @staticmethod
    def _to_openai_tools(
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object"}),
                },
            }
            for tool in (tools or [])
        ]

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LlmResult:
        # OpenAI carries the system prompt as the first message.
        full_messages = [{"role": "system", "content": system}, *messages]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens or self._max_tokens,
            "messages": full_messages,
        }
        openai_tools = self._to_openai_tools(tools)
        if openai_tools:
            kwargs["tools"] = openai_tools

        response = await self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        tool_uses: list[ToolUse] = []
        serialized_calls: list[dict[str, Any]] = []
        for call in message.tool_calls or []:
            raw_args = call.function.arguments or "{}"
            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError:
                parsed = {}
            tool_uses.append(ToolUse(id=call.id, name=call.function.name, input=parsed))
            serialized_calls.append(
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": raw_args,
                    },
                }
            )

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }
        if serialized_calls:
            assistant_message["tool_calls"] = serialized_calls

        return LlmResult(
            text=message.content or "",
            tool_uses=tool_uses,
            stop_reason="tool_use" if tool_uses else "end_turn",
            assistant_message=assistant_message,
        )

    def user_message(self, text: str) -> dict[str, Any]:
        return {"role": "user", "content": text}

    def assistant_message(self, text: str) -> dict[str, Any]:
        return {"role": "assistant", "content": text}

    def tool_result_message(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        # OpenAI expects one message per tool result, keyed by tool_call_id.
        return [
            {
                "role": "tool",
                "tool_call_id": result.tool_use_id,
                "content": result.content,
            }
            for result in results
        ]
