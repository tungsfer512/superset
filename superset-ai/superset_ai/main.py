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

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from superset_ai import __version__
from superset_ai.api import ask, conversations, data, health, schema, sql
from superset_ai.config import Settings, get_settings
from superset_ai.deps import RateLimitDep
from superset_ai.llm.factory import create_llm
from superset_ai.ratelimit import RateLimiter, RedisRateLimiter
from superset_ai.smart.grounding import GroundingService
from superset_ai.smart.schema_indexer import SchemaIndexer
from superset_ai.smart.semantic_layer import Glossary
from superset_ai.store import (
    InMemoryConversationStore,
    SqliteConversationStore,
)
from superset_ai.superset_client import SupersetClient

logger = logging.getLogger("superset_ai")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared singletons (Superset client, LLM, conversation store)."""
    settings = get_settings()
    app.state.superset_client = SupersetClient(
        settings.superset_base_url, timeout=settings.superset_api_timeout
    )
    # Durable, queryable chat history in a SQLite file (falls back to memory).
    if settings.conversation_db_path:
        app.state.store = SqliteConversationStore(settings.conversation_db_path)
        logger.info(
            "Conversation history persisted to %s", settings.conversation_db_path
        )
    else:
        app.state.store = InMemoryConversationStore()
    if settings.redis_url:
        app.state.rate_limiter = RedisRateLimiter(
            settings.rate_limit_per_min, settings.redis_url
        )
        logger.info("Using Redis backend for rate limiting.")
    else:
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_min)
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


def _cors_origins(settings: Settings) -> tuple[list[str], str | None]:
    """Resolve (allow_origins, allow_origin_regex) for the CORS middleware.

    ``SUPERSET_AI_EXTRA_CORS_ORIGINS=*`` allows ALL origins. Because the sidecar
    uses credentials (session cookies), a literal ``Access-Control-Allow-Origin:
    *`` is rejected by browsers, so we use ``allow_origin_regex=".*"`` which
    echoes the caller's origin back and works with credentials.
    """
    raw = [
        origin.strip()
        for origin in settings.extra_cors_origins.split(",")
        if origin.strip()
    ]
    if "*" in raw:
        return [], ".*"
    return [settings.superset_base_url, *raw], None


def create_app() -> FastAPI:
    """Application factory mirroring Superset's ``create_app`` pattern."""
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    app = FastAPI(
        title="Superset AI Sidecar",
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Allow the Superset frontend origin to call the sidecar from the browser.
    allow_origins, allow_origin_regex = _cors_origins(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        # No secrets logged: only method, path, status, latency.
        logger.info(
            "%s %s -> %s (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(Exception)
    async def on_unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error."}
        )

    # AI endpoints require auth and are rate limited; /health stays open.
    app.include_router(health.router)
    app.include_router(data.router, dependencies=[RateLimitDep])
    app.include_router(ask.router, dependencies=[RateLimitDep])
    app.include_router(sql.router, dependencies=[RateLimitDep])
    app.include_router(schema.router, dependencies=[RateLimitDep])
    app.include_router(conversations.router, dependencies=[RateLimitDep])
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
