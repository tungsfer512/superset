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
"""Select and build an LLM connector from configuration.

The active provider is chosen via ``SUPERSET_AI_LLM_PROVIDER`` (anthropic /
openai / gemini). Each provider's SDK is imported lazily so installing or
configuring only the one you use is enough.
"""

from __future__ import annotations

from superset_ai.config import Settings
from superset_ai.llm.base import LlmClient

# Sensible default model per provider when ``llm_model`` is not set.
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o",
    "gemini": "gemini-2.5-flash",
}


def resolve_provider(settings: Settings) -> str:
    """Return the normalized provider name."""
    return (settings.llm_provider or "").strip().lower()


def resolve_model(settings: Settings) -> str:
    """Return the model id to use (explicit override or provider default)."""
    if settings.llm_model:
        return settings.llm_model
    return DEFAULT_MODELS.get(resolve_provider(settings), "")


def _api_key(settings: Settings, provider: str) -> str | None:
    return {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "gemini": settings.gemini_api_key,
    }.get(provider)


def is_configured(settings: Settings) -> bool:
    """Whether the selected provider is known and has an API key."""
    provider = resolve_provider(settings)
    return provider in DEFAULT_MODELS and bool(_api_key(settings, provider))


def create_llm(settings: Settings) -> LlmClient | None:
    """Build the configured LLM client, or ``None`` if no key is set.

    Raises ``ValueError`` for an unknown provider name.
    """
    provider = resolve_provider(settings)
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unknown LLM provider: {provider!r}")

    api_key = _api_key(settings, provider)
    if not api_key:
        return None

    model = resolve_model(settings)
    if provider == "anthropic":
        from superset_ai.llm.anthropic_client import AnthropicClient

        return AnthropicClient(api_key, model, settings.llm_max_tokens)
    if provider == "openai":
        from superset_ai.llm.openai_client import OpenAIClient

        return OpenAIClient(api_key, model, settings.llm_max_tokens)
    # provider == "gemini"
    from superset_ai.llm.gemini_client import GeminiClient

    return GeminiClient(api_key, model, settings.llm_max_tokens)
