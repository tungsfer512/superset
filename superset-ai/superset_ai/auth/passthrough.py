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
"""Token pass-through.

The sidecar never holds its own Superset credentials. Instead it forwards the
caller's auth (a JWT ``Authorization`` header and/or the Superset session
cookie) to the Superset REST API so every call runs *as that user* — which is
what lets Superset apply the correct RBAC and Row Level Security.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass
class SupersetAuth:
    """Caller credentials forwarded verbatim to Superset."""

    authorization: str | None = None
    cookie: str | None = None
    csrf_token: str | None = None

    @property
    def is_authenticated(self) -> bool:
        """Whether any credential was supplied by the caller."""
        return bool(self.authorization or self.cookie)

    @property
    def uses_cookie(self) -> bool:
        """Cookie-based sessions need CSRF protection for unsafe methods."""
        return self.cookie is not None and self.authorization is None

    def to_headers(self) -> dict[str, str]:
        """Build the outgoing header set for a Superset request."""
        headers: dict[str, str] = {}
        if self.authorization:
            headers["Authorization"] = self.authorization
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf_token:
            headers["X-CSRFToken"] = self.csrf_token
        return headers


def extract_auth(headers: Mapping[str, str]) -> SupersetAuth:
    """Pull forwardable credentials from an incoming request's headers."""
    return SupersetAuth(
        authorization=headers.get("authorization"),
        cookie=headers.get("cookie"),
    )
