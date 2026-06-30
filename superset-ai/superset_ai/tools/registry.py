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
"""LLM tool definitions and dispatch.

Schemas are provider-neutral (``name`` / ``description`` / ``parameters`` where
``parameters`` is a JSON Schema). Each LLM connector translates them to its own
format. :func:`execute_tool` maps a tool call onto the Phase-1 data tools,
running as the caller (token pass-through). Errors are returned (not raised) so
the model can self-correct.
"""

from __future__ import annotations

from typing import Any

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import Settings
from superset_ai.sql.guard import UnsafeSqlError
from superset_ai.superset_client import SupersetClient
from superset_ai.superset_client.errors import SupersetApiError
from superset_ai.tools import data_tools

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "list_datasets",
        "description": (
            "List datasets the current user can access. Use to discover what "
            "data exists. Supports a name search and pagination."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Case-insensitive substring of the table name.",
                },
                "page": {"type": "integer", "minimum": 0, "default": 0},
                "page_size": {"type": "integer", "minimum": 1, "default": 100},
            },
        },
    },
    {
        "name": "get_dataset_schema",
        "description": (
            "Get a dataset's columns (name, type) plus the database_id and "
            "schema needed to query it. Call before writing SQL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer"},
            },
            "required": ["dataset_id"],
        },
    },
    {
        "name": "run_select_sql",
        "description": (
            "Run a single read-only SELECT statement and return columns and "
            "rows. Only SELECT is allowed; a LIMIT is enforced automatically."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "database_id": {"type": "integer"},
                "sql": {"type": "string", "description": "A single SELECT query."},
                "schema": {"type": "string"},
                "dialect": {
                    "type": "string",
                    "description": "SQL dialect, e.g. 'mysql', 'postgres'.",
                },
            },
            "required": ["database_id", "sql"],
        },
    },
]


async def execute_tool(
    name: str,
    tool_input: dict[str, Any],
    *,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
) -> dict[str, Any]:
    """Execute one tool call; return a JSON-serializable result or an error."""
    try:
        if name == "list_datasets":
            return await data_tools.list_datasets(
                client,
                auth,
                search=tool_input.get("search"),
                page=int(tool_input.get("page", 0)),
                page_size=int(tool_input.get("page_size", 100)),
            )
        if name == "get_dataset_schema":
            return await data_tools.get_dataset_schema(
                client, auth, int(tool_input["dataset_id"])
            )
        if name == "run_select_sql":
            return await data_tools.run_select_sql(
                client,
                auth,
                database_id=int(tool_input["database_id"]),
                sql=str(tool_input["sql"]),
                schema=tool_input.get("schema"),
                row_limit=settings.sql_row_limit,
                dialect=tool_input.get("dialect"),
            )
    except UnsafeSqlError as err:
        return {"error": f"Unsafe SQL rejected: {err}"}
    except SupersetApiError as err:
        return {"error": err.message}
    except (KeyError, ValueError, TypeError) as err:
        return {"error": f"Invalid tool input: {err}"}
    return {"error": f"Unknown tool: {name}"}
