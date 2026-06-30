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
"""FastAPI application entrypoint for the Superset AI sidecar."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from superset_ai import __version__
from superset_ai.api import ask, data, health, schema, sql
from superset_ai.config import get_settings
from superset_ai.llm.factory import create_llm
from superset_ai.smart.grounding import GroundingService
from superset_ai.smart.schema_indexer import SchemaIndexer
from superset_ai.smart.semantic_layer import Glossary
from superset_ai.store import InMemoryConversationStore
from superset_ai.superset_client import SupersetClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared singletons (Superset client, LLM, conversation store)."""
    settings = get_settings()
    app.state.superset_client = SupersetClient(
        settings.superset_base_url, timeout=settings.superset_api_timeout
    )
    app.state.store = InMemoryConversationStore()
    app.state.grounding = None
    if settings.enable_grounding:
        app.state.grounding = GroundingService(
            SchemaIndexer(cache_ttl=settings.schema_cache_ttl),
            Glossary.load(settings.glossary_path),
            top_k=settings.grounding_top_k,
        )
    try:
        # None if the selected provider has no API key configured.
        app.state.llm = create_llm(settings)
    except ValueError:
        # Unknown provider name: start anyway; AI endpoints return 503.
        app.state.llm = None
    try:
        yield
    finally:
        await app.state.superset_client.aclose()


def create_app() -> FastAPI:
    """Application factory mirroring Superset's ``create_app`` pattern."""
    settings = get_settings()
    app = FastAPI(
        title="Superset AI Sidecar",
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Allow the Superset frontend origin to call the sidecar from the browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.superset_base_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(data.router)
    app.include_router(ask.router)
    app.include_router(sql.router)
    app.include_router(schema.router)
    return app


app = create_app()


def main() -> None:
    """Run the sidecar with uvicorn (used by the console entrypoint)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "superset_ai.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
