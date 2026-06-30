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
"""Conversation transcript storage.

Phase 2 ships an in-memory store (good for a single worker). Swap in a
SQLite/Postgres/Redis-backed implementation of :class:`ConversationStore` for
multi-worker deployments — the orchestrator only depends on the protocol.
"""

from __future__ import annotations

from typing import Any, Protocol


class ConversationStore(Protocol):
    """Append-only transcript keyed by conversation id."""

    def get(self, conversation_id: str) -> list[dict[str, Any]]:
        """Return the stored messages for a conversation (possibly empty)."""
        ...

    def append(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        """Append messages to a conversation's transcript."""
        ...


class InMemoryConversationStore:
    """Process-local store. Lost on restart; not shared across workers."""

    def __init__(self) -> None:
        self._data: dict[str, list[dict[str, Any]]] = {}

    def get(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self._data.get(conversation_id, []))

    def append(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        self._data.setdefault(conversation_id, []).extend(messages)
