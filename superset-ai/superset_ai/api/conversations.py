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

import json
import re
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import get_settings
from superset_ai.deps import AuthDep, LlmOptionalDep, StoreDep
from superset_ai.llm.base import LlmClient
from superset_ai.store import ConversationStore

router = APIRouter(tags=["ai"])

# Shown when the user has no history yet (mirrors the frontend fallbacks).
DEFAULT_SUGGESTIONS = [
    "Có những dataset nào tôi xem được?",
    "Đếm số dòng trong dataset đầu tiên.",
    "Vẽ biểu đồ cột từ một dataset và đưa link.",
]

_SUGGESTION_SYSTEM = (
    "Bạn đề xuất câu hỏi gợi ý cho người dùng của một trợ lý dữ liệu (Apache "
    "Superset). Dựa trên các chủ đề người dùng từng hỏi, hãy đề xuất các câu hỏi "
    "tiếp theo mà họ có thể muốn hỏi về dữ liệu của mình. Trả lời DUY NHẤT bằng "
    "một mảng JSON gồm đúng 3 chuỗi tiếng Việt, mỗi chuỗi là một câu hỏi ngắn "
    "gọn (tối đa ~12 từ), không trùng lặp. Không thêm giải thích hay markdown."
)

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n?|\n?```$")


def _parse_suggestions(text: str) -> list[str]:
    """Best-effort parse of the model's reply into a list of question strings."""
    cleaned = _FENCE_RE.sub("", text.strip()).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            items = [str(item).strip() for item in data if str(item).strip()]
            return items[:4]
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: treat non-empty lines as questions, stripping list bullets.
    lines = [
        re.sub(r"^\s*(?:[-*\d.)]+)\s*", "", line).strip()
        for line in cleaned.splitlines()
    ]
    return [line for line in lines if line][:4]


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


class SuggestionsResponse(BaseModel):
    """Suggested prompts for the empty chat state."""

    suggestions: list[str]
    # True when inferred from history by the LLM; False for history-derived or
    # default fallbacks.
    generated: bool


def _recent_titles(
    store: ConversationStore, user_key: str, limit: int = 8
) -> list[str]:
    """Distinct, non-empty titles (the user's past questions), most recent first."""
    titles: list[str] = []
    seen: set[str] = set()
    for row in store.list_conversations(user_key):
        title = (row.get("title") or "").strip()
        key = title.lower()
        if title and key not in seen:
            seen.add(key)
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


@router.get("/suggestions", response_model=SuggestionsResponse)
async def suggestions(
    auth: SupersetAuth = AuthDep,
    store: ConversationStore = StoreDep,
    llm: LlmClient | None = LlmOptionalDep,
) -> SuggestionsResponse:
    """Suggest prompts inferred from the caller's chat history.

    Falls back to a static set when there is no history, and to the raw recent
    questions when the LLM is unavailable or fails.
    """
    titles = _recent_titles(store, auth.identity())
    if not titles:
        return SuggestionsResponse(suggestions=DEFAULT_SUGGESTIONS, generated=False)

    if llm is not None:
        try:
            prompt = "Các câu hỏi gần đây của người dùng:\n" + "\n".join(
                f"- {title}" for title in titles
            )
            result = await llm.complete(
                system=_SUGGESTION_SYSTEM,
                messages=[llm.user_message(prompt)],
                max_tokens=get_settings().llm_max_tokens,
            )
            parsed = _parse_suggestions(result.text)
            if parsed:
                return SuggestionsResponse(suggestions=parsed, generated=True)
        except Exception:  # noqa: BLE001, S110 - best-effort; never fatal
            pass

    # No LLM (or it failed): re-surface the user's own recent questions.
    return SuggestionsResponse(suggestions=titles[:3], generated=False)


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
