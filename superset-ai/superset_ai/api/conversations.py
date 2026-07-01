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
"""History endpoints: list past conversations and load one to review/continue.

All results are scoped to the caller's identity, so a user only ever sees their
own chat history.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.deps import AuthDep, StoreDep
from superset_ai.store import ConversationStore

router = APIRouter(tags=["ai"])


class ConversationSummary(BaseModel):
    """A row in the history list."""

    id: str
    title: str | None
    updated_at: float
    message_count: int


class ConversationDetail(BaseModel):
    """A full conversation's display messages for review/continuation."""

    id: str
    messages: list[dict[str, Any]]


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    auth: SupersetAuth = AuthDep,
    store: ConversationStore = StoreDep,
) -> list[ConversationSummary]:
    """List the caller's saved conversations, most recent first."""
    rows = store.list_conversations(auth.identity())
    return [ConversationSummary(**row) for row in rows]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    auth: SupersetAuth = AuthDep,
    store: ConversationStore = StoreDep,
) -> ConversationDetail:
    """Return one conversation's messages (empty if not owned/absent)."""
    messages = store.get_messages(conversation_id, auth.identity())
    return ConversationDetail(id=conversation_id, messages=messages)
