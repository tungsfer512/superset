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
"""Classify provider (LLM) errors into clean HTTP responses.

Provider SDKs raise their own exception types (rate limits, auth, etc.). Rather
than couple to each, we inspect the message so a quota error surfaces as a 429
with a friendly note instead of a raw 500.
"""

from __future__ import annotations

from superset_ai.superset_client.errors import sanitize


def classify_llm_error(exc: Exception) -> tuple[int, str]:
    """Map an LLM provider exception to an (HTTP status, safe message)."""
    text = str(exc)
    low = text.lower()
    if (
        "429" in text
        or "resource_exhausted" in low
        or "quota" in low
        or "rate limit" in low
        or "rate_limit" in low
    ):
        return (
            429,
            "AI provider rate limit/quota exceeded. Please wait and try again.",
        )
    if (
        "401" in text
        or "403" in text
        or "api key" in low
        or "unauthorized" in low
        or "permission" in low
    ):
        return 502, "AI provider authentication/permission error."
    return 502, f"AI provider error: {sanitize(text)}"
