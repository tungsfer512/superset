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
"""Q&A orchestration: drive the LLM tool-use loop and the SQL helpers.

The loop is provider-neutral (depends only on :class:`LlmClient`) so it is
unit-testable with a fake LLM. Tool calls run as the caller via token
pass-through, so RBAC/RLS are enforced by Superset.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import Settings
from superset_ai.guards import truncate_for_llm
from superset_ai.llm.base import LlmClient, LlmResult, TextDelta, ToolResult
from superset_ai.prompts.system import (
    ASK_SYSTEM_PROMPT,
    EXPLAIN_SQL_SYSTEM_PROMPT,
    FIX_SQL_SYSTEM_PROMPT,
    GENERATE_SQL_SYSTEM_PROMPT,
)
from superset_ai.sql.guard import assert_select_only
from superset_ai.superset_client import SupersetClient
from superset_ai.tools import data_tools
from superset_ai.tools.registry import execute_tool, get_tool_schemas

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


@dataclass
class AskResult:
    """Final result of an /ask turn."""

    answer: str
    conversation_id: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)


def _strip_fences(text: str) -> str:
    return _FENCE_RE.sub("", text.strip()).strip()


async def _ground_question(
    grounding: Any,
    client: SupersetClient,
    auth: SupersetAuth,
    question: str,
) -> str:
    """Prepend retrieved schema/glossary context to the question, if available."""
    if grounding is None:
        return question
    try:
        context = await grounding.context_for(client, auth, question)
    except Exception:  # noqa: BLE001 - grounding is best-effort, never fatal
        return question
    if not context:
        return question
    return f"{question}\n\n---\n{context}"


async def _turn(
    llm: LlmClient,
    settings: Settings,
    messages: list[dict[str, Any]],
    *,
    stream: bool,
) -> AsyncIterator[tuple[str, dict[str, Any]] | LlmResult]:
    """Produce one assistant turn, streaming token events when supported.

    Yields ``("token", {...})`` deltas (only when streaming) and finally the
    :class:`LlmResult` for that turn.
    """
    tools = get_tool_schemas(settings.allow_write_tools)
    if stream and hasattr(llm, "complete_stream"):
        async for chunk in llm.complete_stream(
            system=ASK_SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
            max_tokens=settings.llm_max_tokens,
        ):
            if isinstance(chunk, TextDelta):
                yield "token", {"text": chunk.text}
            else:
                yield chunk
        return
    yield await llm.complete(
        system=ASK_SYSTEM_PROMPT,
        messages=messages,
        tools=tools,
        max_tokens=settings.llm_max_tokens,
    )


async def _run_events(
    llm: LlmClient,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
    messages: list[dict[str, Any]],
    *,
    stream: bool = False,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Run the tool-use loop, yielding (event_type, payload) as it progresses."""
    artifacts: list[dict[str, Any]] = []

    for _ in range(settings.max_tool_iterations):
        result: LlmResult | None = None
        async for item in _turn(llm, settings, messages, stream=stream):
            if isinstance(item, LlmResult):
                result = item
            else:
                yield item
        assert result is not None
        messages.append(result.assistant_message)

        if result.stop_reason != "tool_use" or not result.tool_uses:
            yield "answer", {"text": result.text}
            yield "done", {"artifacts": artifacts}
            return

        tool_results: list[ToolResult] = []
        for tool_use in result.tool_uses:
            yield "tool", {"name": tool_use.name, "input": tool_use.input}
            output = await execute_tool(
                tool_use.name,
                tool_use.input,
                client=client,
                auth=auth,
                settings=settings,
            )
            if (
                tool_use.name in ("run_select_sql", "create_chart", "create_dashboard")
                and "error" not in output
            ):
                artifacts.append(output)
            tool_results.append(
                ToolResult(
                    tool_use.id,
                    truncate_for_llm(
                        json.dumps(output, default=str),
                        settings.response_token_guard,
                    ),
                    name=tool_use.name,
                )
            )
        messages.extend(llm.tool_result_message(tool_results))

    yield (
        "answer",
        {
            "text": (
                "Mình chưa hoàn tất được yêu cầu sau nhiều bước xử lý. "
                "Bạn thử thu hẹp hoặc làm rõ câu hỏi giúp mình nhé."
            )
        },
    )
    yield "done", {"artifacts": artifacts}


async def ask(
    llm: LlmClient,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
    *,
    question: str,
    store: Any,
    conversation_id: str | None = None,
    grounding: Any = None,
) -> AskResult:
    """Answer a question, running tools as needed; persists the transcript."""
    cid = conversation_id or uuid4().hex
    history = store.get(cid)
    grounded = await _ground_question(grounding, client, auth, question)
    messages: list[dict[str, Any]] = [*history, llm.user_message(grounded)]
    base_len = len(history)

    answer = ""
    artifacts: list[dict[str, Any]] = []
    tool_trace: list[dict[str, Any]] = []
    async for event_type, payload in _run_events(llm, client, auth, settings, messages):
        if event_type == "tool":
            tool_trace.append(payload)
        elif event_type == "answer":
            answer = payload["text"]
        elif event_type == "done":
            artifacts = payload["artifacts"]

    store.append(cid, messages[base_len:])
    return AskResult(
        answer=answer,
        conversation_id=cid,
        artifacts=artifacts,
        tool_trace=tool_trace,
    )


async def stream_ask(
    llm: LlmClient,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
    *,
    question: str,
    store: Any,
    conversation_id: str | None = None,
    grounding: Any = None,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Stream the same flow as :func:`ask` as (event_type, payload) tuples."""
    cid = conversation_id or uuid4().hex
    history = store.get(cid)
    grounded = await _ground_question(grounding, client, auth, question)
    messages: list[dict[str, Any]] = [*history, llm.user_message(grounded)]
    base_len = len(history)

    yield "start", {"conversation_id": cid}
    async for event_type, payload in _run_events(
        llm, client, auth, settings, messages, stream=True
    ):
        yield event_type, payload

    store.append(cid, messages[base_len:])


async def generate_sql(
    llm: LlmClient,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
    *,
    question: str,
    dataset_id: int | None = None,
    dialect: str | None = None,
) -> str:
    """Translate a question into a validated, read-only SELECT statement."""
    context = ""
    if dataset_id is not None:
        schema = await data_tools.get_dataset_schema(client, auth, dataset_id)
        context = json.dumps(schema, default=str)

    user = f"Schema:\n{context}\n\nQuestion: {question}" if context else question
    result = await llm.complete(
        system=GENERATE_SQL_SYSTEM_PROMPT,
        messages=[llm.user_message(user)],
        max_tokens=settings.llm_max_tokens,
    )
    sql = _strip_fences(result.text)
    assert_select_only(sql, dialect=dialect)  # fail closed if not read-only
    return sql


async def explain_sql(
    llm: LlmClient,
    settings: Settings,
    *,
    sql: str,
    dialect: str | None = None,
) -> str:
    """Return a natural-language explanation of a SQL query."""
    result = await llm.complete(
        system=EXPLAIN_SQL_SYSTEM_PROMPT,
        messages=[llm.user_message(f"Dialect: {dialect or 'generic'}\nSQL:\n{sql}")],
        max_tokens=settings.llm_max_tokens,
    )
    return result.text


async def fix_sql(
    llm: LlmClient,
    settings: Settings,
    *,
    sql: str,
    error: str,
    dialect: str | None = None,
) -> str:
    """Return a corrected, still read-only SELECT for a failing query."""
    user = f"Dialect: {dialect or 'generic'}\nSQL:\n{sql}\n\nError:\n{error}"
    result = await llm.complete(
        system=FIX_SQL_SYSTEM_PROMPT,
        messages=[llm.user_message(user)],
        max_tokens=settings.llm_max_tokens,
    )
    fixed = _strip_fences(result.text)
    assert_select_only(fixed, dialect=dialect)  # fail closed
    return fixed
