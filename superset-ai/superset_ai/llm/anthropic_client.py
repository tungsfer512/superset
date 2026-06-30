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
"""Anthropic Claude implementation of :class:`~superset_ai.llm.base.LlmClient`."""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic

from superset_ai.llm.base import LlmResult, ToolResult, ToolUse


class AnthropicClient:
    """Thin wrapper over the Anthropic Messages API with tool use."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096) -> None:
        self._client: Any = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    @staticmethod
    def _to_anthropic_tools(
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters", {"type": "object"}),
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
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens or self._max_tokens,
            system=system,
            tools=self._to_anthropic_tools(tools),
            messages=messages,
        )

        text_parts: list[str] = []
        tool_uses: list[ToolUse] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_input = block.input if isinstance(block.input, dict) else {}
                tool_uses.append(
                    ToolUse(id=block.id, name=block.name, input=dict(tool_input))
                )

        assistant_message = {
            "role": "assistant",
            "content": [block.model_dump() for block in response.content],
        }
        return LlmResult(
            text="".join(text_parts),
            tool_uses=tool_uses,
            stop_reason=response.stop_reason or "end_turn",
            assistant_message=assistant_message,
        )

    def user_message(self, text: str) -> dict[str, Any]:
        return {"role": "user", "content": text}

    def tool_result_message(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_use_id,
                        "content": result.content,
                    }
                    for result in results
                ],
            }
        ]
