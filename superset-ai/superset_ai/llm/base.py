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
"""Provider-neutral LLM interface used by the orchestrator.

Keeping the orchestrator behind this small surface means it can be unit-tested
with a fake client (no network) and the provider can be swapped without
touching orchestration logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolUse:
    """A tool call requested by the model."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    """The outcome of executing a :class:`ToolUse`, fed back to the model."""

    tool_use_id: str
    content: str
    # The tool name; some providers (e.g. Gemini) match results by name.
    name: str = ""


@dataclass
class LlmResult:
    """One assistant turn, normalized across providers."""

    text: str
    tool_uses: list[ToolUse] = field(default_factory=list)
    # "end_turn" (final) or "tool_use" (wants tools run, then call again).
    stop_reason: str = "end_turn"
    # Provider-native assistant message to append back to the transcript.
    assistant_message: dict[str, Any] = field(default_factory=dict)


class LlmClient(Protocol):
    """Minimal, provider-neutral LLM contract.

    Each implementation owns its message format. ``tools`` are passed in a
    neutral form (``name``/``description``/``parameters``) and translated to the
    provider's schema inside :meth:`complete`.
    """

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> LlmResult:
        """Produce a single assistant turn for the given transcript."""
        ...

    def user_message(self, text: str) -> dict[str, Any]:
        """Build a provider-native user turn carrying plain text."""
        ...

    def tool_result_message(self, results: list[ToolResult]) -> list[dict[str, Any]]:
        """Build the provider-native message(s) carrying tool results."""
        ...
