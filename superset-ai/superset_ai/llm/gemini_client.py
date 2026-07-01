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
"""Google Gemini implementation of :class:`~superset_ai.llm.base.LlmClient`.

Uses the ``google-genai`` SDK with function calling. Messages use Gemini's
``contents`` format (roles ``user`` / ``model`` with ``parts``). Gemini matches
tool results by function *name* rather than a call id.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from google import genai

from superset_ai.llm.base import LlmResult, TextDelta, ToolResult, ToolUse


class GeminiClient:
    """Thin wrapper over the google-genai SDK with function calling."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 4096) -> None:
        self._client: Any = genai.Client(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    @staticmethod
    def _to_gemini_tools(
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        declarations = [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object"}),
            }
            for tool in (tools or [])
        ]
        return [{"function_declarations": declarations}] if declarations else []

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LlmResult:
        config: dict[str, Any] = {
            "system_instruction": system,
            "max_output_tokens": max_tokens or self._max_tokens,
        }
        gemini_tools = self._to_gemini_tools(tools)
        if gemini_tools:
            config["tools"] = gemini_tools

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=messages,
            config=config,
        )

        text_parts: list[str] = []
        tool_uses: list[ToolUse] = []
        serialized_parts: list[dict[str, Any]] = []
        candidate = response.candidates[0]
        for part in candidate.content.parts:
            if getattr(part, "text", None):
                text_parts.append(part.text)
                serialized_parts.append({"text": part.text})
            elif getattr(part, "function_call", None):
                call = part.function_call
                args = dict(call.args) if call.args else {}
                # Gemini has no call id; use the function name as the key.
                tool_uses.append(ToolUse(id=call.name, name=call.name, input=args))
                serialized_parts.append(
                    {"function_call": {"name": call.name, "args": args}}
                )

        assistant_message = {"role": "model", "parts": serialized_parts}
        return LlmResult(
            text="".join(text_parts),
            tool_uses=tool_uses,
            stop_reason="tool_use" if tool_uses else "end_turn",
            assistant_message=assistant_message,
        )

    async def complete_stream(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[TextDelta | LlmResult]:
        """Stream text deltas, accumulating into a final normalized result."""
        config: dict[str, Any] = {
            "system_instruction": system,
            "max_output_tokens": max_tokens or self._max_tokens,
        }
        gemini_tools = self._to_gemini_tools(tools)
        if gemini_tools:
            config["tools"] = gemini_tools

        stream = await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=messages,
            config=config,
        )

        text_parts: list[str] = []
        tool_uses: list[ToolUse] = []
        serialized_parts: list[dict[str, Any]] = []
        async for chunk in stream:
            candidates = getattr(chunk, "candidates", None)
            if not candidates or candidates[0].content is None:
                continue
            for part in candidates[0].content.parts or []:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                    serialized_parts.append({"text": part.text})
                    yield TextDelta(part.text)
                elif getattr(part, "function_call", None):
                    call = part.function_call
                    args = dict(call.args) if call.args else {}
                    tool_uses.append(ToolUse(id=call.name, name=call.name, input=args))
                    serialized_parts.append(
                        {"function_call": {"name": call.name, "args": args}}
                    )

        yield LlmResult(
            text="".join(text_parts),
            tool_uses=tool_uses,
            stop_reason="tool_use" if tool_uses else "end_turn",
            assistant_message={"role": "model", "parts": serialized_parts},
        )

    def user_message(self, text: str) -> dict[str, Any]:
        return {"role": "user", "parts": [{"text": text}]}

    def assistant_message(self, text: str) -> dict[str, Any]:
        return {"role": "model", "parts": [{"text": text}]}

    def tool_result_message(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "parts": [
                    {
                        "function_response": {
                            "name": result.name or result.tool_use_id,
                            "response": {"result": result.content},
                        }
                    }
                    for result in results
                ],
            }
        ]
