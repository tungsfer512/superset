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
"""Redis-backed conversation store for multi-worker deployments.

Implements the same :class:`~superset_ai.store.conversations.ConversationStore`
protocol as the in-memory store, so the orchestrator is unchanged. A client can
be injected for testing; otherwise one is built from the URL.
"""

from __future__ import annotations

import json
import time
from typing import Any


def _title_from(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") == "user" and message.get("text"):
            return str(message["text"])[:80]
    return "Chat"


class RedisConversationStore:
    """Durable, user-scoped conversation store backed by Redis (multi-worker).

    Layout: ``conv:<id>`` holds the JSON display messages, ``convmeta:<id>`` the
    metadata (owner/title/timestamps), and ``convindex:<user_key>`` the user's
    list of conversation ids.
    """

    def __init__(
        self,
        url: str | None = None,
        *,
        client: Any = None,
        ttl_seconds: int = 86400,
    ) -> None:
        if client is None:
            import redis  # imported lazily so redis is optional

            client = redis.from_url(url, decode_responses=True)
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def _msg_key(conversation_id: str) -> str:
        return f"conv:{conversation_id}"

    @staticmethod
    def _meta_key(conversation_id: str) -> str:
        return f"convmeta:{conversation_id}"

    @staticmethod
    def _index_key(user_key: str) -> str:
        return f"convindex:{user_key}"

    def _read_json(self, key: str, default: Any) -> Any:
        raw = self._client.get(key)
        return json.loads(raw) if raw else default

    def get_messages(
        self, conversation_id: str, user_key: str
    ) -> list[dict[str, Any]]:
        meta = self._read_json(self._meta_key(conversation_id), None)
        if meta is None or meta.get("user_key") != user_key:
            return []
        messages: list[dict[str, Any]] = self._read_json(
            self._msg_key(conversation_id), []
        )
        return messages

    def append_messages(
        self,
        conversation_id: str,
        user_key: str,
        messages: list[dict[str, Any]],
    ) -> None:
        meta = self._read_json(self._meta_key(conversation_id), None)
        if meta is not None and meta.get("user_key") != user_key:
            return
        data: list[dict[str, Any]] = self._read_json(
            self._msg_key(conversation_id), []
        )
        data.extend(messages)
        now = time.time()
        if meta is None:
            meta = {
                "user_key": user_key,
                "title": _title_from(messages),
                "created_at": now,
            }
            index = self._read_json(self._index_key(user_key), [])
            if conversation_id not in index:
                index.append(conversation_id)
                self._client.set(
                    self._index_key(user_key), json.dumps(index), ex=self._ttl
                )
        meta["updated_at"] = now
        meta["message_count"] = len(data)
        self._client.set(
            self._msg_key(conversation_id), json.dumps(data, default=str), ex=self._ttl
        )
        self._client.set(
            self._meta_key(conversation_id), json.dumps(meta), ex=self._ttl
        )

    def list_conversations(self, user_key: str) -> list[dict[str, Any]]:
        index = self._read_json(self._index_key(user_key), [])
        items = []
        for cid in index:
            meta = self._read_json(self._meta_key(cid), None)
            if meta is None or meta.get("user_key") != user_key:
                continue
            items.append(
                {
                    "id": cid,
                    "title": meta.get("title"),
                    "updated_at": meta.get("updated_at", meta.get("created_at", 0)),
                    "message_count": meta.get("message_count", 0),
                }
            )
        return sorted(items, key=lambda i: i["updated_at"], reverse=True)
