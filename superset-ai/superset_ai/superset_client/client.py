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
"""Async HTTP client wrapping a subset of the Superset REST API.

Every call is made *as the caller* via :class:`SupersetAuth` (token
pass-through), so Superset enforces RBAC and Row Level Security. Cookie-based
sessions automatically fetch a CSRF token before unsafe (POST) requests.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import prison

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.superset_client.errors import SupersetApiError

CSRF_PATH = "/api/v1/security/csrf_token/"
DATASET_PATH = "/api/v1/dataset/"
DATABASE_PATH = "/api/v1/database/"
SQLLAB_EXECUTE_PATH = "/api/v1/sqllab/execute/"
CHART_PATH = "/api/v1/chart/"


class SupersetClient:
    """Thin async wrapper over the Superset REST API."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        )

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        await self._client.aclose()

    # -- low-level ---------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        auth: SupersetAuth,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        needs_csrf: bool = False,
    ) -> dict[str, Any]:
        headers = auth.to_headers()
        if needs_csrf and auth.uses_cookie:
            await self._ensure_csrf(auth)
            headers = auth.to_headers()
            headers["Referer"] = f"{self._base_url}/"

        try:
            response = await self._client.request(
                method, path, params=params, json=json, headers=headers
            )
        except httpx.HTTPError as err:
            raise SupersetApiError(502, f"Cannot reach Superset: {err}") from err

        if response.status_code >= 400:
            raise SupersetApiError(response.status_code, response.text)

        payload: dict[str, Any] = response.json()
        return payload

    async def _ensure_csrf(self, auth: SupersetAuth) -> None:
        if auth.csrf_token is not None:
            return
        response = await self._client.get(CSRF_PATH, headers=auth.to_headers())
        if response.status_code >= 400:
            raise SupersetApiError(response.status_code, response.text)
        auth.csrf_token = response.json().get("result")

    # -- endpoints ---------------------------------------------------------

    async def list_datasets(
        self,
        auth: SupersetAuth,
        *,
        search: str | None = None,
        page: int = 0,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """List datasets (paginated). Mirrors ``GET /api/v1/dataset/``."""
        query: dict[str, Any] = {"page": page, "page_size": page_size}
        if search:
            query["filters"] = [{"col": "table_name", "opr": "ct", "value": search}]
        params = {"q": prison.dumps(query)}
        return await self._request("GET", DATASET_PATH, auth, params=params)

    async def get_dataset(self, auth: SupersetAuth, dataset_id: int) -> dict[str, Any]:
        """Get a dataset's detail incl. columns. ``GET /api/v1/dataset/{id}``."""
        return await self._request("GET", f"{DATASET_PATH}{dataset_id}", auth)

    async def execute_sql(
        self,
        auth: SupersetAuth,
        *,
        database_id: int,
        sql: str,
        schema: str | None = None,
        row_limit: int | None = None,
    ) -> dict[str, Any]:
        """Run SQL synchronously via SQL Lab. ``POST /api/v1/sqllab/execute/``.

        SQL Lab applies the caller's RLS, so callers must still pass a guarded,
        read-only statement (see :mod:`superset_ai.sql.guard`).
        """
        body: dict[str, Any] = {
            "database_id": database_id,
            "sql": sql,
            "runAsync": False,
            "json": True,
        }
        if schema:
            body["schema"] = schema
        if row_limit is not None:
            body["queryLimit"] = row_limit
        return await self._request(
            "POST", SQLLAB_EXECUTE_PATH, auth, json=body, needs_csrf=True
        )

    # -- generic REST helpers (used by the resource bridge) ---------------

    async def api_get(
        self,
        auth: SupersetAuth,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """GET an arbitrary Superset API path."""
        return await self._request("GET", path, auth, params=params)

    async def api_post(
        self, auth: SupersetAuth, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """POST to an arbitrary Superset API path (with CSRF)."""
        return await self._request("POST", path, auth, json=body, needs_csrf=True)

    async def api_put(
        self, auth: SupersetAuth, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """PUT to an arbitrary Superset API path (with CSRF)."""
        return await self._request("PUT", path, auth, json=body, needs_csrf=True)

    async def api_delete(self, auth: SupersetAuth, path: str) -> dict[str, Any]:
        """DELETE an arbitrary Superset API path (with CSRF)."""
        return await self._request("DELETE", path, auth, needs_csrf=True)

    async def create_chart(
        self,
        auth: SupersetAuth,
        *,
        slice_name: str,
        datasource_id: int,
        viz_type: str,
        params: dict[str, Any],
        datasource_type: str = "table",
        dashboards: list[int] | None = None,
    ) -> dict[str, Any]:
        """Create a chart (slice). ``POST /api/v1/chart/`` (runs as the user)."""
        body: dict[str, Any] = {
            "slice_name": slice_name,
            "datasource_id": datasource_id,
            "datasource_type": datasource_type,
            "viz_type": viz_type,
            "params": json.dumps(params),
        }
        if dashboards:
            body["dashboards"] = dashboards
        return await self._request("POST", CHART_PATH, auth, json=body, needs_csrf=True)
