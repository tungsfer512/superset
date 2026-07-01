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
"""Generic Superset REST resource bridge.

Instead of one function per endpoint, a small set of generic operations
(list/get/create/update/delete) work across an allow-listed set of resources.
Security-sensitive resources (users, roles, RLS, permissions) are intentionally
NOT in the allow-list, so the assistant can never touch them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import prison

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.superset_client import SupersetClient


@dataclass(frozen=True)
class Resource:
    """A Superset REST resource the bridge is allowed to touch."""

    path: str
    writable: bool = False
    # Column used for name search in list(); None disables search filtering.
    search_col: str | None = None


# Allow-list. NB: users/roles/rls/permissions are deliberately excluded.
RESOURCES: dict[str, Resource] = {
    "dashboard": Resource("/api/v1/dashboard/", True, "dashboard_title"),
    "chart": Resource("/api/v1/chart/", True, "slice_name"),
    "dataset": Resource("/api/v1/dataset/", True, "table_name"),
    "database": Resource("/api/v1/database/", True, "database_name"),
    "saved_query": Resource("/api/v1/saved_query/", True, "label"),
    "tag": Resource("/api/v1/tag/", True, "name"),
    "annotation_layer": Resource("/api/v1/annotation_layer/", True, "name"),
    "report": Resource("/api/v1/report/", True, "name"),
    "css_template": Resource("/api/v1/css_template/", True, "template_name"),
    # Read-only reference resources:
    "query": Resource("/api/v1/query/", False, None),
}


class ResourceError(ValueError):
    """Raised for an unknown resource or a disallowed write."""


# --- Generic API passthrough (covers every endpoint except the deny-list) ---

_API_PREFIX = "/api/v1/"

# Paths the assistant must never touch: security, users/roles/permissions/RLS,
# logs, and raw SQL execution (must go through the guarded run_select_sql).
_DENY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/security\b"),
    re.compile(r"/roles?\b"),
    re.compile(r"/permissions?\b"),
    re.compile(r"/permissions[-_]resources?\b"),
    re.compile(r"/rowlevelsecurity\b"),
    re.compile(r"/rls\b"),
    re.compile(r"/users?\b"),  # /me is allowed (does not match)
    re.compile(r"/logs?\b"),
    re.compile(r"/activity\b"),
    re.compile(r"/sqllab/execute\b"),  # DDL/DML risk -> use run_select_sql
    re.compile(r"/csv_upload\b"),
    re.compile(r"/excel_upload\b"),
)

_WRITE_METHODS = {"POST", "PUT", "DELETE"}


def _normalize_path(path: str) -> str:
    """Strip any host/scheme and query, return a clean /api/v1/... path."""
    cleaned = path.strip()
    cleaned = re.sub(r"^https?://[^/]+", "", cleaned)
    cleaned = cleaned.split("?", 1)[0]
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return cleaned


def check_api_path(path: str) -> str:
    """Validate a raw API path against the allow prefix and deny-list."""
    normalized = _normalize_path(path)
    if not normalized.startswith(_API_PREFIX):
        raise ResourceError(f"Only {_API_PREFIX}* paths are allowed.")
    lowered = normalized.lower()
    for pattern in _DENY_PATTERNS:
        if pattern.search(lowered):
            raise ResourceError(
                f"Path '{normalized}' is blocked (security/users/logs or unsafe)."
            )
    return normalized


async def api_get(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    path: str,
    query: str | None = None,
) -> dict[str, Any]:
    """GET any allowed Superset API path (e.g. database tables, chart data)."""
    safe_path = check_api_path(path)
    params = {"q": query} if query else None
    return await client.api_get(auth, safe_path, params=params)


async def api_request(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Call any allowed write endpoint (POST/PUT/DELETE), deny-list enforced."""
    verb = method.upper()
    if verb not in _WRITE_METHODS:
        raise ResourceError(f"Unsupported method '{method}'.")
    safe_path = check_api_path(path)
    if verb == "DELETE":
        if not confirm:
            raise ResourceError(
                f"Refusing to DELETE '{safe_path}' without confirm=true."
            )
        return await client.api_delete(auth, safe_path)
    if verb == "POST":
        return await client.api_post(auth, safe_path, body or {})
    return await client.api_put(auth, safe_path, body or {})


def _resource(name: str) -> Resource:
    resource = RESOURCES.get(name)
    if resource is None:
        allowed = ", ".join(sorted(RESOURCES))
        raise ResourceError(f"Unknown resource '{name}'. Allowed: {allowed}.")
    return resource


def resource_names() -> list[str]:
    """Names of all bridgeable resources (for tool descriptions)."""
    return sorted(RESOURCES)


async def list_resource(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    resource: str,
    search: str | None = None,
    page: int = 0,
    page_size: int = 25,
) -> dict[str, Any]:
    """List objects of a resource (paginated), optionally filtered by name."""
    res = _resource(resource)
    query: dict[str, Any] = {"page": page, "page_size": page_size}
    if search and res.search_col:
        query["filters"] = [{"col": res.search_col, "opr": "ct", "value": search}]
    payload = await client.api_get(auth, res.path, params={"q": prison.dumps(query)})
    return {
        "count": payload.get("count"),
        "ids": payload.get("ids"),
        "result": payload.get("result", []),
    }


async def get_resource(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    resource: str,
    object_id: int,
) -> dict[str, Any]:
    """Get one object by id."""
    res = _resource(resource)
    return await client.api_get(auth, f"{res.path}{object_id}")


async def create_resource(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    resource: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Create an object. Requires a writable resource."""
    res = _resource(resource)
    if not res.writable:
        raise ResourceError(f"Resource '{resource}' is read-only.")
    return await client.api_post(auth, res.path, payload)


async def update_resource(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    resource: str,
    object_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Update an object by id. Requires a writable resource."""
    res = _resource(resource)
    if not res.writable:
        raise ResourceError(f"Resource '{resource}' is read-only.")
    return await client.api_put(auth, f"{res.path}{object_id}", payload)


async def delete_resource(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    resource: str,
    object_id: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete an object by id. Requires writable resource and confirm=True."""
    res = _resource(resource)
    if not res.writable:
        raise ResourceError(f"Resource '{resource}' is read-only.")
    if not confirm:
        raise ResourceError(
            f"Refusing to delete {resource} {object_id} without confirm=true."
        )
    return await client.api_delete(auth, f"{res.path}{object_id}")
