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
"""Tests for LLM provider selection via the factory."""

import pytest

from superset_ai.config import Settings
from superset_ai.llm.factory import create_llm, is_configured, resolve_model


def test_default_model_per_provider():
    assert resolve_model(Settings(llm_provider="anthropic")) == "claude-sonnet-4-6"
    assert resolve_model(Settings(llm_provider="openai")) == "gpt-4o"
    assert resolve_model(Settings(llm_provider="gemini")) == "gemini-2.5-flash"


def test_explicit_model_override():
    settings = Settings(llm_provider="openai", llm_model="gpt-4o-mini")
    assert resolve_model(settings) == "gpt-4o-mini"


def test_no_key_means_not_configured_and_none():
    for provider in ("anthropic", "openai", "gemini"):
        settings = Settings(llm_provider=provider)
        assert is_configured(settings) is False
        assert create_llm(settings) is None


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_llm(Settings(llm_provider="llama"))


def test_builds_anthropic_client_when_key_present():
    from superset_ai.llm.anthropic_client import AnthropicClient

    settings = Settings(llm_provider="anthropic", anthropic_api_key="sk-test")
    assert is_configured(settings) is True
    assert isinstance(create_llm(settings), AnthropicClient)


def test_builds_openai_client_when_key_present():
    from superset_ai.llm.openai_client import OpenAIClient

    settings = Settings(llm_provider="openai", openai_api_key="sk-test")
    assert isinstance(create_llm(settings), OpenAIClient)


def test_provider_name_is_case_insensitive():
    settings = Settings(llm_provider="OpenAI", openai_api_key="sk-test")
    assert is_configured(settings) is True
