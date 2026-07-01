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
"""Q&A endpoints: /ask (JSON) and /ask/stream (Server-Sent Events)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from superset_ai import orchestrator
from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import get_settings
from superset_ai.deps import AuthDep, ClientDep, GroundingDep, LlmDep, StoreDep
from superset_ai.llm.base import LlmClient
from superset_ai.llm.errors import classify_llm_error
from superset_ai.smart.grounding import GroundingService
from superset_ai.store import ConversationStore
from superset_ai.superset_client import SupersetClient

router = APIRouter(tags=["ai"])


class AskRequest(BaseModel):
    """Body for /ask and /ask/stream."""

    question: str = Field(..., min_length=1)
    conversation_id: str | None = Field(default=None)


class AskResponse(BaseModel):
    """JSON answer plus any data artifacts the assistant produced."""

    answer: str
    conversation_id: str
    artifacts: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]


@router.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
    llm: LlmClient = LlmDep,
    store: ConversationStore = StoreDep,
    grounding: GroundingService | None = GroundingDep,
) -> AskResponse:
    """Answer a natural-language question (runs tools as needed)."""
    try:
        result = await orchestrator.ask(
            llm,
            client,
            auth,
            get_settings(),
            question=body.question,
            store=store,
            conversation_id=body.conversation_id,
            grounding=grounding,
        )
    except Exception as err:  # noqa: BLE001 - map provider errors to clean HTTP
        status_code, message = classify_llm_error(err)
        raise HTTPException(status_code=status_code, detail=message) from err
    return AskResponse(
        answer=result.answer,
        conversation_id=result.conversation_id,
        artifacts=result.artifacts,
        tool_trace=result.tool_trace,
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/ask/stream")
async def ask_stream(
    body: AskRequest,
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
    llm: LlmClient = LlmDep,
    store: ConversationStore = StoreDep,
    grounding: GroundingService | None = GroundingDep,
) -> StreamingResponse:
    """Stream the assistant's progress as Server-Sent Events.

    Event types: ``start`` (conversation_id), ``tool`` (a tool is running),
    ``answer`` (final text), ``done`` (artifacts).
    """

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event_type, payload in orchestrator.stream_ask(
                llm,
                client,
                auth,
                get_settings(),
                question=body.question,
                store=store,
                conversation_id=body.conversation_id,
                grounding=grounding,
            ):
                yield _sse(event_type, payload)
        except Exception as err:  # noqa: BLE001 - surface provider errors as an event
            _, message = classify_llm_error(err)
            yield _sse("error", {"detail": message})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
