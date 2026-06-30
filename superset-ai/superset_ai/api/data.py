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
"""Phase-1 data endpoints.

These expose the building-block tools (list datasets, read a dataset schema,
run a guarded SELECT) directly so they can be exercised and tested before the
LLM orchestrator (Phase 2) is wired in. All run as the caller via token
pass-through.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import get_settings
from superset_ai.deps import AuthDep, ClientDep
from superset_ai.sql.guard import UnsafeSqlError
from superset_ai.superset_client import SupersetClient
from superset_ai.superset_client.errors import SupersetApiError
from superset_ai.tools import data_tools

router = APIRouter(tags=["data"])


class RunSqlRequest(BaseModel):
    """Body for ``POST /sql/run``."""

    database_id: int = Field(..., description="Target Superset database id.")
    sql: str = Field(..., description="A single read-only SELECT statement.")
    schema_name: str | None = Field(
        default=None, alias="schema", description="Optional schema/namespace."
    )
    dialect: str | None = Field(
        default=None, description="SQL dialect for parsing (e.g. 'mysql')."
    )


def _to_http(err: SupersetApiError) -> HTTPException:
    # Map upstream auth/permission failures through; collapse the rest to 502.
    status = err.status_code if err.status_code in (401, 403, 404) else 502
    return HTTPException(status_code=status, detail=err.message)


@router.get("/datasets")
async def list_datasets(
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
    search: str | None = None,
    page: int = 0,
    page_size: int = 100,
) -> dict[str, Any]:
    """List datasets visible to the caller."""
    try:
        return await data_tools.list_datasets(
            client, auth, search=search, page=page, page_size=page_size
        )
    except SupersetApiError as err:
        raise _to_http(err) from err


@router.get("/datasets/{dataset_id}/schema")
async def get_dataset_schema(
    dataset_id: int,
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
) -> dict[str, Any]:
    """Return a dataset's columns and how to query it."""
    try:
        return await data_tools.get_dataset_schema(client, auth, dataset_id)
    except SupersetApiError as err:
        raise _to_http(err) from err


@router.post("/sql/run")
async def run_sql(
    body: RunSqlRequest,
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
) -> dict[str, Any]:
    """Run a guarded, read-only SELECT as the caller (RLS enforced)."""
    settings = get_settings()
    try:
        return await data_tools.run_select_sql(
            client,
            auth,
            database_id=body.database_id,
            sql=body.sql,
            schema=body.schema_name,
            row_limit=settings.sql_row_limit,
            dialect=body.dialect,
        )
    except UnsafeSqlError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except SupersetApiError as err:
        raise _to_http(err) from err
