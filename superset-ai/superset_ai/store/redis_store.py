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
from typing import Any


class RedisConversationStore:
    """Stores each transcript as a JSON document under ``conv:<id>``."""

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
    def _key(conversation_id: str) -> str:
        return f"conv:{conversation_id}"

    def get(self, conversation_id: str) -> list[dict[str, Any]]:
        raw = self._client.get(self._key(conversation_id))
        if not raw:
            return []
        loaded: list[dict[str, Any]] = json.loads(raw)
        return loaded

    def append(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        data = self.get(conversation_id)
        data.extend(messages)
        self._client.set(self._key(conversation_id), json.dumps(data), ex=self._ttl)
