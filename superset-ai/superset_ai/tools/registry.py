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
from superset_ai.tools import data_tools, rest_tools, viz_tools
from superset_ai.tools.rest_tools import ResourceError, resource_names

_RESOURCES_DESC = ", ".join(resource_names())

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
    {
        "name": "superset_list",
        "description": (
            "List objects of a Superset resource (paginated), optionally "
            f"filtered by name. Resources: {_RESOURCES_DESC}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {"type": "string"},
                "search": {"type": "string"},
                "page": {"type": "integer", "minimum": 0, "default": 0},
                "page_size": {"type": "integer", "minimum": 1, "default": 25},
            },
            "required": ["resource"],
        },
    },
    {
        "name": "superset_get",
        "description": (
            "Get one object of a Superset resource by id. "
            f"Resources: {_RESOURCES_DESC}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {"type": "string"},
                "object_id": {"type": "integer"},
            },
            "required": ["resource", "object_id"],
        },
    },
    {
        "name": "list_viz_types",
        "description": (
            "List the chart viz_types this Superset supports and the params each "
            "one requires. Call this if unsure which viz_type/params to use."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "superset_api_get",
        "description": (
            "GET any read-only Superset API endpoint for things the specific "
            "tools don't cover — e.g. '/api/v1/database/1/tables/', "
            "'/api/v1/dashboard/2/charts', '/api/v1/database/1/function_names/'. "
            "Provide the full '/api/v1/...' path. Security, users, roles and logs "
            "are blocked."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "e.g. /api/v1/chart/"},
                "query": {
                    "type": "string",
                    "description": "Optional RISON value for the ?q= parameter.",
                },
            },
            "required": ["path"],
        },
    },
]

# Write tools, only advertised when SUPERSET_AI_ALLOW_WRITE_TOOLS is enabled.
WRITE_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "superset_create",
        "description": (
            "Create an object of a Superset resource. Provide the full payload "
            "(call superset_get on a similar object first to learn the shape). "
            f"Writable resources: {_RESOURCES_DESC}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {"type": "string"},
                "payload": {"type": "object"},
            },
            "required": ["resource", "payload"],
        },
    },
    {
        "name": "superset_update",
        "description": (
            "Update an object by id with a partial payload of changed fields."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {"type": "string"},
                "object_id": {"type": "integer"},
                "payload": {"type": "object"},
            },
            "required": ["resource", "object_id", "payload"],
        },
    },
    {
        "name": "superset_delete",
        "description": (
            "Delete an object by id. Destructive — requires confirm=true and the "
            "user's explicit approval."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {"type": "string"},
                "object_id": {"type": "integer"},
                "confirm": {"type": "boolean", "default": False},
            },
            "required": ["resource", "object_id", "confirm"],
        },
    },
    {
        "name": "superset_api_request",
        "description": (
            "Call any write Superset API endpoint the specific tools don't cover "
            "(POST/PUT/DELETE) — e.g. publish a dashboard, refresh a dataset, "
            "run a report. Provide method, full '/api/v1/...' path and body. "
            "DELETE requires confirm=true. Security, users, roles, logs and raw "
            "SQL execution are blocked."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["POST", "PUT", "DELETE"]},
                "path": {"type": "string"},
                "body": {"type": "object"},
                "confirm": {"type": "boolean", "default": False},
            },
            "required": ["method", "path"],
        },
    },
    {
        "name": "create_dashboard",
        "description": (
            "Create a dashboard and lay out charts on it. Typically: create the "
            "charts first with create_chart, collect their chart_ids, then call "
            "this with the title and chart_ids. Returns a link to the dashboard."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "chart_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Chart ids to place on the dashboard.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "create_chart",
        "description": (
            "Create a Superset chart on a dataset and return a link. Call "
            "get_dataset_schema first for the real column names. `datasource` "
            "and `viz_type` are added automatically — do NOT put them in params. "
            "Provide params matching the viz_type. Examples:\n"
            '- table (aggregate): {"query_mode":"aggregate",'
            '"groupby":["country"],"metrics":["count"]}\n'
            '- table (raw rows): {"query_mode":"raw",'
            '"all_columns":["col_a","col_b"]}\n'
            '- pie: {"groupby":["country"],"metric":"count"}\n'
            "- echarts_timeseries_bar / echarts_timeseries_line: "
            '{"x_axis":"order_date","metrics":["count"],'
            '"groupby":["country"]}\n'
            '- big_number_total: {"metric":"count"}\n'
            'Metrics may be a saved metric name (e.g. "count") or a column '
            "aggregation. Optionally add the chart to dashboards."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "integer"},
                "chart_name": {"type": "string"},
                "viz_type": {
                    "type": "string",
                    "description": (
                        "Registered keys: table, pivot_table_v2, pie, "
                        "big_number_total, echarts_timeseries_bar, "
                        "echarts_timeseries_line, echarts_area, "
                        "echarts_timeseries_scatter, histogram_v2, heatmap_v2, "
                        "funnel, gauge_chart, radar, treemap_v2, sunburst_v2, "
                        "box_plot, world_map. Common/legacy names "
                        "(bar/line/area/histogram/big_number/pivot...) are "
                        "auto-mapped; unknown types fall back to a table. For "
                        "bar/line you MUST set 'x_axis' + 'metrics'; for "
                        "histogram_v2 set 'column' (a numeric column)."
                    ),
                },
                "params": {
                    "type": "object",
                    "description": "Viz config (metrics, groupby, x_axis, ...).",
                },
                "dashboard_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Optional dashboard ids to add the chart to.",
                },
            },
            "required": ["dataset_id", "chart_name", "viz_type"],
        },
    },
]


def get_tool_schemas(allow_write: bool) -> list[dict[str, Any]]:
    """Return the tool schemas advertised to the model for this request."""
    if allow_write:
        return [*TOOL_SCHEMAS, *WRITE_TOOL_SCHEMAS]
    return TOOL_SCHEMAS


async def execute_tool(
    name: str,
    tool_input: dict[str, Any],
    *,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
) -> dict[str, Any]:
    """Execute one tool call; return a JSON-serializable result or an error."""
    write_tools = {
        "create_chart",
        "create_dashboard",
        "superset_create",
        "superset_update",
        "superset_delete",
        "superset_api_request",
    }
    try:
        if name in write_tools:
            if not settings.allow_write_tools:
                return {"error": "Write operations are disabled on this server."}
            return await _dispatch_write(name, tool_input, client=client, auth=auth)
        result = await _dispatch_read(
            name, tool_input, client=client, auth=auth, settings=settings
        )
        if result is not None:
            return result
    except UnsafeSqlError as err:
        return {"error": f"Unsafe SQL rejected: {err}"}
    except ResourceError as err:
        return {"error": str(err)}
    except SupersetApiError as err:
        return {"error": err.message}
    except (KeyError, ValueError, TypeError) as err:
        return {"error": f"Invalid tool input: {err}"}
    return {"error": f"Unknown tool: {name}"}


async def _dispatch_read(
    name: str,
    tool_input: dict[str, Any],
    *,
    client: SupersetClient,
    auth: SupersetAuth,
    settings: Settings,
) -> dict[str, Any] | None:
    """Run a read-only tool; return None if ``name`` is not a read tool."""
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
    if name == "superset_list":
        return await rest_tools.list_resource(
            client,
            auth,
            resource=str(tool_input["resource"]),
            search=tool_input.get("search"),
            page=int(tool_input.get("page", 0)),
            page_size=int(tool_input.get("page_size", 25)),
        )
    if name == "superset_get":
        return await rest_tools.get_resource(
            client,
            auth,
            resource=str(tool_input["resource"]),
            object_id=int(tool_input["object_id"]),
        )
    if name == "superset_api_get":
        return await rest_tools.api_get(
            client,
            auth,
            path=str(tool_input["path"]),
            query=tool_input.get("query"),
        )
    if name == "list_viz_types":
        return {"viz_types": viz_tools.supported_viz_types()}
    return None


async def _dispatch_write(
    name: str,
    tool_input: dict[str, Any],
    *,
    client: SupersetClient,
    auth: SupersetAuth,
) -> dict[str, Any]:
    if name == "create_chart":
        return await viz_tools.create_chart(
            client,
            auth,
            dataset_id=int(tool_input["dataset_id"]),
            chart_name=str(tool_input["chart_name"]),
            viz_type=str(tool_input["viz_type"]),
            params=tool_input.get("params"),
            dashboard_ids=tool_input.get("dashboard_ids"),
        )
    if name == "create_dashboard":
        return await viz_tools.create_dashboard(
            client,
            auth,
            title=str(tool_input["title"]),
            chart_ids=tool_input.get("chart_ids"),
        )
    if name == "superset_api_request":
        return await rest_tools.api_request(
            client,
            auth,
            method=str(tool_input["method"]),
            path=str(tool_input["path"]),
            body=tool_input.get("body"),
            confirm=bool(tool_input.get("confirm", False)),
        )
    resource = str(tool_input["resource"])
    if name == "superset_create":
        return await rest_tools.create_resource(
            client, auth, resource=resource, payload=dict(tool_input["payload"])
        )
    if name == "superset_update":
        return await rest_tools.update_resource(
            client,
            auth,
            resource=resource,
            object_id=int(tool_input["object_id"]),
            payload=dict(tool_input["payload"]),
        )
    # superset_delete
    return await rest_tools.delete_resource(
        client,
        auth,
        resource=resource,
        object_id=int(tool_input["object_id"]),
        confirm=bool(tool_input.get("confirm", False)),
    )
