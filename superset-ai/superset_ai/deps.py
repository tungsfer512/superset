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
"""FastAPI dependencies (request-scoped wiring)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from superset_ai.auth.passthrough import SupersetAuth, extract_auth
from superset_ai.llm.base import LlmClient
from superset_ai.smart.grounding import GroundingService
from superset_ai.store import ConversationStore
from superset_ai.superset_client import SupersetClient


def get_superset_client(request: Request) -> SupersetClient:
    """Return the shared Superset client created at app startup."""
    client: SupersetClient | None = getattr(request.app.state, "superset_client", None)
    if client is None:  # pragma: no cover - misconfiguration guard
        raise HTTPException(status_code=503, detail="Superset client not ready.")
    return client


def get_llm(request: Request) -> LlmClient:
    """Return the configured LLM client, or 503 if no API key was provided."""
    llm: LlmClient | None = getattr(request.app.state, "llm", None)
    if llm is None:
        raise HTTPException(
            status_code=503,
            detail="AI provider is not configured (missing API key).",
        )
    return llm


def get_store(request: Request) -> ConversationStore:
    """Return the shared conversation store."""
    store: ConversationStore | None = getattr(request.app.state, "store", None)
    if store is None:  # pragma: no cover - misconfiguration guard
        raise HTTPException(status_code=503, detail="Conversation store not ready.")
    return store


def get_grounding(request: Request) -> GroundingService | None:
    """Return the grounding service, or None if grounding is disabled."""
    return getattr(request.app.state, "grounding", None)


def get_auth(request: Request) -> SupersetAuth:
    """Extract the caller's forwardable credentials, requiring authentication."""
    auth = extract_auth(request.headers)
    if not auth.is_authenticated:
        raise HTTPException(
            status_code=401,
            detail="Missing Superset credentials (Authorization or Cookie).",
        )
    return auth


AuthDep = Depends(get_auth)


def enforce_rate_limit(request: Request, auth: SupersetAuth = AuthDep) -> None:
    """Reject the request with 429 if the caller exceeded their quota."""
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is not None and not limiter.allow(auth.identity()):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down and try again.",
        )


ClientDep = Depends(get_superset_client)
LlmDep = Depends(get_llm)
StoreDep = Depends(get_store)
GroundingDep = Depends(get_grounding)
RateLimitDep = Depends(enforce_rate_limit)
