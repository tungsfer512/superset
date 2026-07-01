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
"""Tests for the Redis-backed store and rate limiter (fake client)."""

from superset_ai.ratelimit import RedisRateLimiter
from superset_ai.store.redis_store import RedisConversationStore


class FakeRedis:
    """Minimal in-memory stand-in for the redis client used by the backends."""

    def __init__(self):
        self.kv = {}
        self.counters = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None):
        self.kv[key] = value

    def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    def expire(self, key, seconds):
        return True


def test_redis_conversation_store_round_trip():
    store = RedisConversationStore(client=FakeRedis())
    assert store.get_messages("c1", "u1") == []
    store.append_messages("c1", "u1", [{"role": "user", "text": "hi"}])
    store.append_messages("c1", "u1", [{"role": "assistant", "text": "hello"}])
    transcript = store.get_messages("c1", "u1")
    assert len(transcript) == 2
    assert transcript[0]["text"] == "hi"
    # Scoped by user: a different user cannot read it.
    assert store.get_messages("c1", "other") == []
    listing = store.list_conversations("u1")
    assert len(listing) == 1
    assert listing[0]["id"] == "c1"
    assert listing[0]["title"] == "hi"


def test_redis_rate_limiter():
    limiter = RedisRateLimiter(max_per_minute=2, client=FakeRedis())
    assert limiter.allow("user") is True
    assert limiter.allow("user") is True
    assert limiter.allow("user") is False


def test_redis_rate_limiter_disabled():
    limiter = RedisRateLimiter(max_per_minute=0, client=FakeRedis())
    assert all(limiter.allow("user") for _ in range(50))
