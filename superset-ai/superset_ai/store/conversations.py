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
"""Conversation storage.

Stores *display* messages (role/text/artifacts) so past chats can be listed and
reviewed, and the transcript can be replayed for follow-up context. Everything
is scoped by an opaque per-user key so users only ever see their own history.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Protocol

# A display message the UI renders: {"role", "text", "artifacts"}.
Message = dict[str, Any]


class ConversationStore(Protocol):
    """Per-user conversation history."""

    def get_messages(self, conversation_id: str, user_key: str) -> list[Message]:
        """Return a conversation's messages (empty if not owned/absent)."""
        ...

    def append_messages(
        self, conversation_id: str, user_key: str, messages: list[Message]
    ) -> None:
        """Append messages to a conversation (creating it if needed)."""
        ...

    def list_conversations(self, user_key: str) -> list[dict[str, Any]]:
        """List the user's conversations (id, title, updated_at, count)."""
        ...


def _title_from(messages: list[Message]) -> str:
    for message in messages:
        if message.get("role") == "user" and message.get("text"):
            return str(message["text"])[:80]
    return "Chat"


class InMemoryConversationStore:
    """Process-local store (fallback / tests). Lost on restart."""

    def __init__(self) -> None:
        self._messages: dict[str, list[Message]] = {}
        self._meta: dict[str, dict[str, Any]] = {}

    def get_messages(self, conversation_id: str, user_key: str) -> list[Message]:
        meta = self._meta.get(conversation_id)
        if meta is None or meta["user_key"] != user_key:
            return []
        return list(self._messages.get(conversation_id, []))

    def append_messages(
        self, conversation_id: str, user_key: str, messages: list[Message]
    ) -> None:
        meta = self._meta.get(conversation_id)
        if meta is not None and meta["user_key"] != user_key:
            return
        bucket = self._messages.setdefault(conversation_id, [])
        bucket.extend(messages)
        if meta is None:
            meta = {
                "user_key": user_key,
                "title": _title_from(messages),
                "created_at": time.time(),
            }
            self._meta[conversation_id] = meta
        meta["updated_at"] = time.time()
        meta["message_count"] = len(bucket)

    def list_conversations(self, user_key: str) -> list[dict[str, Any]]:
        items = [
            {
                "id": cid,
                "title": meta["title"],
                "updated_at": meta.get("updated_at", meta["created_at"]),
                "message_count": meta.get("message_count", 0),
            }
            for cid, meta in self._meta.items()
            if meta["user_key"] == user_key
        ]
        return sorted(items, key=lambda i: i["updated_at"], reverse=True)


class SqliteConversationStore:
    """Durable, file-backed store — history survives restarts and is queryable."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_key TEXT NOT NULL,
                title TEXT,
                created_at REAL,
                updated_at REAL
            )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT,
                artifacts TEXT,
                created_at REAL
            )"""
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)"
        )
        self._conn.commit()

    def get_messages(self, conversation_id: str, user_key: str) -> list[Message]:
        with self._lock:
            owner = self._conn.execute(
                "SELECT user_key FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if owner is None or owner[0] != user_key:
                return []
            rows = self._conn.execute(
                "SELECT role, text, artifacts FROM messages "
                "WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            ).fetchall()
        return [
            {
                "role": role,
                "text": text or "",
                "artifacts": json.loads(artifacts) if artifacts else [],
            }
            for role, text, artifacts in rows
        ]

    def append_messages(
        self, conversation_id: str, user_key: str, messages: list[Message]
    ) -> None:
        now = time.time()
        with self._lock:
            row = self._conn.execute(
                "SELECT user_key FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO conversations "
                    "(id, user_key, title, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        conversation_id,
                        user_key,
                        _title_from(messages),
                        now,
                        now,
                    ),
                )
            elif row[0] != user_key:
                return  # not the owner; refuse
            else:
                self._conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (now, conversation_id),
                )
            for message in messages:
                self._conn.execute(
                    "INSERT INTO messages "
                    "(conversation_id, role, text, artifacts, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        conversation_id,
                        message.get("role", "assistant"),
                        message.get("text", ""),
                        json.dumps(message.get("artifacts", []), default=str),
                        now,
                    ),
                )
            self._conn.commit()

    def list_conversations(self, user_key: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT c.id, c.title, c.updated_at, "
                "(SELECT COUNT(*) FROM messages m "
                " WHERE m.conversation_id = c.id) "
                "FROM conversations c WHERE c.user_key = ? "
                "ORDER BY c.updated_at DESC LIMIT 100",
                (user_key,),
            ).fetchall()
        return [
            {
                "id": cid,
                "title": title,
                "updated_at": updated_at,
                "message_count": count,
            }
            for cid, title, updated_at, count in rows
        ]
