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
"""Phase-1 data tools.

These return compact, LLM-friendly shapes (small dicts) rather than raw
Superset payloads, and run the SELECT-only guard before any SQL reaches
Superset. They are pure async functions so they can later be registered as
LLM tools without change.
"""

from __future__ import annotations

from typing import Any

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.sql.guard import assert_select_only, enforce_limit
from superset_ai.superset_client import SupersetClient


async def list_datasets(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    search: str | None = None,
    page: int = 0,
    page_size: int = 100,
) -> dict[str, Any]:
    """List datasets the caller can see, in a compact shape."""
    payload = await client.list_datasets(
        auth, search=search, page=page, page_size=page_size
    )
    datasets = [
        {
            "id": item.get("id"),
            "name": item.get("table_name"),
            "schema": item.get("schema"),
            "database": (item.get("database") or {}).get("database_name"),
        }
        for item in payload.get("result", [])
    ]
    return {"count": payload.get("count", len(datasets)), "datasets": datasets}


async def get_dataset_schema(
    client: SupersetClient, auth: SupersetAuth, dataset_id: int
) -> dict[str, Any]:
    """Return a dataset's columns plus the info needed to query it."""
    payload = await client.get_dataset(auth, dataset_id)
    result = payload.get("result", {})
    columns = [
        {
            "name": col.get("column_name"),
            "type": col.get("type"),
            "description": col.get("description"),
        }
        for col in result.get("columns", [])
    ]
    database = result.get("database") or {}
    return {
        "dataset_id": dataset_id,
        "table_name": result.get("table_name"),
        "schema": result.get("schema"),
        "database_id": database.get("id"),
        "backend": database.get("backend"),
        "columns": columns,
    }


async def run_select_sql(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    database_id: int,
    sql: str,
    schema: str | None = None,
    row_limit: int = 1000,
    dialect: str | None = None,
) -> dict[str, Any]:
    """Run a guarded, read-only query and return columns + rows.

    Raises :class:`~superset_ai.sql.guard.UnsafeSqlError` if ``sql`` is not a
    single SELECT statement.
    """
    assert_select_only(sql, dialect=dialect)
    safe_sql = enforce_limit(sql, row_limit, dialect=dialect)
    payload = await client.execute_sql(
        auth,
        database_id=database_id,
        sql=safe_sql,
        schema=schema,
        row_limit=row_limit,
    )
    return {
        "executed_sql": safe_sql,
        "columns": payload.get("columns", []),
        "rows": payload.get("data", []),
        "row_count": len(payload.get("data", [])),
    }
