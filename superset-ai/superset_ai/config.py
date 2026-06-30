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
"""Runtime configuration for the Superset AI sidecar.

All settings are read from environment variables (or a local ``.env`` file)
so the service can be configured independently of Superset.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings for the sidecar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SUPERSET_AI_",
        extra="ignore",
    )

    # --- Service ---
    host: str = "0.0.0.0"  # noqa: S104 -- container listens on all interfaces
    port: int = 8800
    debug: bool = False

    # --- Superset connection (data is read ONLY through the REST API) ---
    superset_base_url: str = "http://localhost:8088"
    superset_api_timeout: int = 30

    # --- LLM provider ---
    # Selects which connector to use: "anthropic" | "openai" | "gemini".
    llm_provider: str = "anthropic"
    # Override the model id. If empty, a sensible default per provider is used.
    llm_model: str | None = None
    llm_max_tokens: int = 4096
    # Per-provider API keys (only the selected provider's key is required).
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None

    # --- Guardrails ---
    sql_row_limit: int = 1000
    response_token_guard: int = 25000
    allow_write_tools: bool = False
    max_tool_iterations: int = 6
    rate_limit_per_min: int = 30
    # Extra browser origins allowed to call the sidecar (comma-separated).
    extra_cors_origins: str = ""

    # --- Smart grounding (schema indexer + glossary + retriever) ---
    enable_grounding: bool = True
    grounding_top_k: int = 5
    schema_cache_ttl: int = 300
    glossary_path: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the resolved settings."""
    return Settings()
