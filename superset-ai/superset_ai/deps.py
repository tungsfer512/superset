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
from superset_ai.superset_client import SupersetClient


def get_superset_client(request: Request) -> SupersetClient:
    """Return the shared Superset client created at app startup."""
    client: SupersetClient | None = getattr(request.app.state, "superset_client", None)
    if client is None:  # pragma: no cover - misconfiguration guard
        raise HTTPException(status_code=503, detail="Superset client not ready.")
    return client


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
ClientDep = Depends(get_superset_client)
