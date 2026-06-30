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
"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from superset_ai import __version__
from superset_ai.config import get_settings
from superset_ai.llm.factory import is_configured, resolve_model, resolve_provider

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    """Liveness probe plus a summary of the resolved configuration.

    No secrets are returned: only whether an LLM key is configured.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "llm_provider": resolve_provider(settings),
        "llm_model": resolve_model(settings),
        "llm_configured": is_configured(settings),
        "superset_base_url": settings.superset_base_url,
    }
