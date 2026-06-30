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
"""Tests for Phase-5 hardening: rate limiting, response guard, identity."""

from fastapi.testclient import TestClient

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.deps import get_llm, get_superset_client
from superset_ai.guards import truncate_for_llm
from superset_ai.main import create_app
from superset_ai.ratelimit import RateLimiter
from tests.fakes import FakeLLM, FakeSupersetClient, text_turn, tool_turn

AUTH = {"Authorization": "Bearer caller"}


def test_rate_limiter_blocks_after_quota():
    limiter = RateLimiter(max_per_minute=2)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    # A different caller has an independent budget.
    assert limiter.allow("b") is True


def test_rate_limiter_disabled_when_zero():
    limiter = RateLimiter(max_per_minute=0)
    assert all(limiter.allow("a") for _ in range(100))


def test_truncate_for_llm():
    assert truncate_for_llm("short", 1000) == "short"
    out = truncate_for_llm("x" * 100, 1)  # budget ~4 chars
    assert out.startswith("xxxx")
    assert "truncated" in out


def test_auth_identity_is_stable_and_non_reversible():
    a = SupersetAuth(authorization="Bearer secret")
    b = SupersetAuth(authorization="Bearer secret")
    c = SupersetAuth(authorization="Bearer other")
    assert a.identity() == b.identity()
    assert a.identity() != c.identity()
    assert "secret" not in a.identity()


def test_ask_returns_429_when_rate_limited():
    llm = FakeLLM(
        [
            tool_turn("t1", "run_select_sql", {"database_id": 7, "sql": "SELECT 1"}),
            text_turn("ok"),
        ]
    )
    app = create_app()
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_superset_client] = lambda: FakeSupersetClient()
    with TestClient(app) as client:
        app.state.rate_limiter = RateLimiter(max_per_minute=1)
        first = client.post("/ask", json={"question": "q1"}, headers=AUTH)
        second = client.post("/ask", json={"question": "q2"}, headers=AUTH)
    assert first.status_code == 200
    assert second.status_code == 429
