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
"""Errors raised by the Superset client, with secret sanitization."""

from __future__ import annotations

import re

# Patterns redacted from any message before it can reach an LLM or the client.
_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    # SQLAlchemy / DB connection URIs (postgresql://user:pass@host/db, etc.)
    (re.compile(r"[a-zA-Z0-9+]+://[^\s\"']+"), "<redacted-uri>"),
    # password=... / pwd=... key-value pairs
    (
        re.compile(r"(?i)(password|pwd|secret|token|api[_-]?key)\s*=\s*\S+"),
        r"\1=<redacted>",
    ),
    # Bare IPv4 addresses
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<redacted-ip>"),
)


def sanitize(message: str, *, max_length: int = 500) -> str:
    """Strip connection strings, secrets and IPs, then truncate."""
    cleaned = message
    for pattern, replacement in _REDACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "…"
    return cleaned


class SupersetApiError(RuntimeError):
    """A non-2xx response from the Superset REST API.

    The ``message`` is always sanitized so DB strings / secrets are never
    surfaced to the caller or an LLM.
    """

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = sanitize(message)
        super().__init__(f"Superset API error {status_code}: {self.message}")
