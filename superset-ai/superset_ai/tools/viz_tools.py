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
"""Visualization tools (chart creation). Gated behind ``allow_write_tools``."""

from __future__ import annotations

import json
import re
from typing import Any

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.superset_client import SupersetClient

_AGG_RE = re.compile(r"^(SUM|AVG|MIN|MAX|COUNT)\s*\(\s*(.+?)\s*\)$", re.IGNORECASE)

# Charts that plot a metric over an x axis; they need `x_axis` to build a query.
_TIMESERIES_VIZ = {
    "echarts_timeseries_bar",
    "echarts_timeseries_line",
    "echarts_area",
    "echarts_timeseries_scatter",
    "echarts_timeseries_smooth",
    "echarts_timeseries_step",
    "echarts_timeseries",
    "mixed_timeseries",
}
# Charts of one metric split by a single dimension (uses `metric` + `groupby`).
_CATEGORY_METRIC_VIZ = {
    "pie",
    "funnel",
    "rose",
    "treemap_v2",
    "sunburst_v2",
    "gauge_chart",
}
# Charts that just need one metric.
_SINGLE_METRIC_VIZ = {"big_number_total", "big_number"}

# Per-viz required params — surfaced to the model via list_viz_types so it knows
# what to provide (and what to ask the user about when unsure).
_VIZ_REQUIRED: dict[str, list[str]] = {
    "table": ["(aggregate) groupby+metrics OR (raw) all_columns"],
    "pivot_table_v2": ["groupby", "metrics"],
    "big_number_total": ["metric"],
    "big_number": ["metric"],
    "pie": ["groupby", "metric"],
    "funnel": ["groupby", "metric"],
    "rose": ["groupby", "metric"],
    "gauge_chart": ["metric"],
    "radar": ["groupby", "metrics"],
    "treemap_v2": ["groupby", "metric"],
    "sunburst_v2": ["groupby", "metric"],
    "echarts_timeseries_bar": ["x_axis", "metrics"],
    "echarts_timeseries_line": ["x_axis", "metrics"],
    "echarts_area": ["x_axis", "metrics"],
    "echarts_timeseries_scatter": ["x_axis", "metrics"],
    "histogram_v2": ["column"],
    "heatmap_v2": ["x_axis", "groupby", "metric"],
    "box_plot": ["groupby", "metrics"],
    "world_map": ["entity", "metric"],
    "country_map": ["entity", "metric"],
}

# Viz keys ACTUALLY registered by this Superset frontend build.
# Ground truth: superset-frontend/.../chart/types/VizType.ts + the plugins
# registered in superset-frontend/src/visualizations/presets/MainPreset.js.
# If you upgrade/patch the frontend, update this set to match.
_SUPPORTED_VIZ_TYPES: frozenset[str] = frozenset(
    {
        "table",
        "pivot_table_v2",
        "big_number",
        "big_number_total",
        "pop_kpi",
        "pie",
        "rose",
        "echarts_timeseries_bar",
        "echarts_timeseries_line",
        "echarts_timeseries_smooth",
        "echarts_timeseries_step",
        "echarts_timeseries_scatter",
        "echarts_timeseries",
        "echarts_area",
        "mixed_timeseries",
        "histogram_v2",
        "box_plot",
        "bubble_v2",
        "bullet",
        "funnel",
        "gauge_chart",
        "graph_chart",
        "radar",
        "heatmap_v2",
        "treemap_v2",
        "sunburst_v2",
        "sankey_v2",
        "waterfall",
        "word_cloud",
        "world_map",
        "country_map",
        "chord",
        "tree_chart",
        "compare",
        "time_table",
        "time_pivot",
        "calendar",
        "cal_heatmap",
    }
)

# Common / legacy names -> the registered key. Legacy NVD3 'bar'/'line'/'area'
# and old keys like 'histogram' render "visualization type not supported".
_VIZ_ALIASES: dict[str, str] = {
    "bar": "echarts_timeseries_bar",
    "bar_chart": "echarts_timeseries_bar",
    "column": "echarts_timeseries_bar",
    "dist_bar": "echarts_timeseries_bar",
    "time_series_bar": "echarts_timeseries_bar",
    "line": "echarts_timeseries_line",
    "line_chart": "echarts_timeseries_line",
    "time_series_line": "echarts_timeseries_line",
    "smooth_line": "echarts_timeseries_smooth",
    "step": "echarts_timeseries_step",
    "area": "echarts_area",
    "area_chart": "echarts_area",
    "scatter": "echarts_timeseries_scatter",
    "bubble": "bubble_v2",
    "big_number": "big_number_total",
    "bignumber": "big_number_total",
    "number": "big_number_total",
    "pie_chart": "pie",
    "piechart": "pie",
    "donut": "pie",
    "histogram": "histogram_v2",
    "hist": "histogram_v2",
    "heatmap": "heatmap_v2",
    "treemap": "treemap_v2",
    "sunburst": "sunburst_v2",
    "sankey": "sankey_v2",
    "boxplot": "box_plot",
    "box": "box_plot",
    "gauge": "gauge_chart",
    "graph": "graph_chart",
    "tree": "tree_chart",
    "wordcloud": "word_cloud",
    "pivot": "pivot_table_v2",
    "pivot_table": "pivot_table_v2",
    "map": "world_map",
}

# When a requested type is unknown/unsupported, fall back to this (always renders).
_FALLBACK_VIZ_TYPE = "table"


def supported_viz_types() -> dict[str, list[str]]:
    """Map every supported viz_type to its required params (for guidance)."""
    return {
        viz: _VIZ_REQUIRED.get(viz, ["metric or columns"])
        for viz in sorted(_SUPPORTED_VIZ_TYPES)
    }


def normalize_viz_type(viz_type: str) -> str:
    """Return a viz_type this Superset build supports.

    Maps common/legacy names to registered keys; anything still unsupported
    falls back to a table so the chart at least renders.
    """
    key = (viz_type or "").strip().lower()
    key = _VIZ_ALIASES.get(key, key)
    if key not in _SUPPORTED_VIZ_TYPES:
        return _FALLBACK_VIZ_TYPE
    return key


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _dimensions(form_data: dict[str, Any]) -> list[Any]:
    """Collect dimension columns from whatever key the model used."""
    for key in ("groupby", "dimensions", "columns", "series", "category"):
        value = form_data.get(key)
        if value:
            return _as_list(value)
    return []


def _has_metric(form_data: dict[str, Any]) -> bool:
    return bool(form_data.get("metric") or form_data.get("metrics"))


def _build_form_data(  # noqa: C901 - a per-viz switch, kept flat for clarity
    dataset_id: int, viz_type: str, params: dict[str, Any] | None
) -> dict[str, Any]:
    """Build valid form_data for ``viz_type``, filling required fields.

    Injects ``datasource``/``viz_type`` (without them Explore is blank) and, per
    viz type, derives the required query fields from whatever hints the model
    provided so the chart is not an "empty query".
    """
    form_data: dict[str, Any] = {
        "row_limit": 1000,
        "adhoc_filters": [],
        "time_range": "No filter",
        **(params or {}),
        # These must win over anything the caller passed:
        "datasource": f"{dataset_id}__table",
        "viz_type": viz_type,
    }
    dims = _dimensions(form_data)

    if viz_type in _TIMESERIES_VIZ:
        if not form_data.get("x_axis") and dims:
            form_data["x_axis"] = dims[0]
            form_data["groupby"] = dims[1:]
        if not _has_metric(form_data):
            form_data["metrics"] = ["count"]
    elif viz_type in _CATEGORY_METRIC_VIZ or viz_type == "radar":
        if not form_data.get("groupby") and dims:
            form_data["groupby"] = dims
        if not _has_metric(form_data):
            # radar wants a list; the single-dimension charts want one metric.
            form_data["metrics" if viz_type == "radar" else "metric"] = "count"
    elif viz_type in _SINGLE_METRIC_VIZ:
        if not _has_metric(form_data):
            form_data["metric"] = "count"
    elif viz_type == "histogram_v2":
        if not form_data.get("column"):
            cols = form_data.get("all_columns") or dims
            if cols:
                form_data["column"] = _as_list(cols)[0]
    elif viz_type == "heatmap_v2":
        if not form_data.get("x_axis") and dims:
            form_data["x_axis"] = dims[0]
            if len(dims) > 1 and not form_data.get("groupby"):
                form_data["groupby"] = dims[1]
        if not _has_metric(form_data):
            form_data["metric"] = "count"
    elif viz_type in ("world_map", "country_map"):
        if not form_data.get("entity") and dims:
            form_data["entity"] = dims[0]
        if not _has_metric(form_data):
            form_data["metric"] = "count"
    elif viz_type in ("table", "pivot_table_v2"):
        if not form_data.get("query_mode"):
            form_data["query_mode"] = (
                "aggregate" if (_has_metric(form_data) or dims) else "raw"
            )
        if form_data["query_mode"] == "aggregate":
            if dims and not form_data.get("groupby"):
                form_data["groupby"] = dims
            if not _has_metric(form_data):
                form_data["metrics"] = ["count"]
        elif not form_data.get("all_columns"):
            form_data["all_columns"] = dims
    _dedupe_dimensions(form_data)
    return form_data


def _dedupe_dimensions(form_data: dict[str, Any]) -> None:
    """Prevent Superset's "Duplicate column/metric labels" error.

    A column used as ``x_axis`` (or ``entity``) must not also appear in
    ``groupby``, and ``groupby`` itself must have no repeats.
    """
    axis = {
        form_data.get("x_axis"),
        form_data.get("entity"),
    }
    axis.discard(None)
    groupby = form_data.get("groupby")
    if isinstance(groupby, list):
        seen: set[Any] = set()
        deduped: list[Any] = []
        for col in groupby:
            if col in axis or col in seen:
                continue
            seen.add(col)
            deduped.append(col)
        form_data["groupby"] = deduped


async def _dataset_meta(
    client: SupersetClient, auth: SupersetAuth, dataset_id: int
) -> tuple[set[str], set[str]]:
    """Return (column names, saved metric names) for a dataset; empty on error."""
    try:
        detail = await client.get_dataset(auth, dataset_id)
    except Exception:  # noqa: BLE001 - validation is best effort
        return set(), set()
    result = detail.get("result", {}) if isinstance(detail, dict) else {}
    columns = {
        c.get("column_name") for c in result.get("columns", []) if c.get("column_name")
    }
    metrics = {
        m.get("metric_name") for m in result.get("metrics", []) if m.get("metric_name")
    }
    return columns, metrics


def _adhoc_sql(expression: str, label: str) -> dict[str, Any]:
    return {
        "expressionType": "SQL",
        "sqlExpression": expression,
        "label": label,
        "hasCustomLabel": True,
    }


def _adhoc_simple(aggregate: str, column: str, label: str) -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "aggregate": aggregate,
        "column": {"column_name": column},
        "label": label,
        "hasCustomLabel": True,
    }


def _normalize_metric(metric: Any, saved: set[str], columns: set[str]) -> Any:
    """Turn a metric that isn't a saved metric into a valid adhoc metric.

    Prevents "metric does not exist" errors when the model passes a saved-metric
    name (e.g. "count") that the dataset doesn't actually define.
    """
    if isinstance(metric, dict):
        return metric  # already an adhoc/structured metric
    text = str(metric).strip()
    if text in saved:
        return text  # a real saved metric
    compact = text.lower().replace(" ", "")
    if compact in ("count", "count(*)", "count(1)", "*"):
        return _adhoc_sql("COUNT(*)", "count")
    match = _AGG_RE.match(text)
    if match:
        agg, col = match.group(1).upper(), match.group(2).strip().strip('"')
        if col == "*":
            return _adhoc_sql(f"{agg}(*)", text)
        if col in columns:
            return _adhoc_simple(agg, col, text)
        return _adhoc_sql(text, text)  # custom SQL over unknown token
    if text in columns:
        # A bare column as a metric: COUNT it (valid for any column type).
        return _adhoc_simple("COUNT", text, f"COUNT({text})")
    # Anything else: treat as a custom SQL expression.
    return _adhoc_sql(text, text)


def _normalize_metrics(
    form_data: dict[str, Any], saved: set[str], columns: set[str]
) -> None:
    if isinstance(form_data.get("metrics"), list):
        form_data["metrics"] = [
            _normalize_metric(m, saved, columns) for m in form_data["metrics"]
        ]
    if form_data.get("metric") is not None:
        form_data["metric"] = _normalize_metric(form_data["metric"], saved, columns)


def _invalid_columns(form_data: dict[str, Any], columns: set[str]) -> dict[str, Any]:
    """Return the referenced columns that don't exist in the dataset."""
    bad: dict[str, Any] = {}
    for key in ("x_axis", "entity", "column"):
        value = form_data.get(key)
        if isinstance(value, str) and value and value not in columns:
            bad[key] = value
    for key in ("groupby", "all_columns"):
        value = form_data.get(key)
        if isinstance(value, list):
            missing = [c for c in value if c not in columns]
            if missing:
                bad[key] = missing
    return bad


async def create_chart(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    dataset_id: int,
    chart_name: str,
    viz_type: str,
    params: dict[str, Any] | None = None,
    dashboard_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Create a Superset chart, validating the config first.

    Columns are checked against the dataset (returns an error to retry if any
    are wrong), and metrics that aren't saved metrics are converted to valid
    adhoc metrics so the chart never fails on a missing saved metric.
    """
    viz_type = normalize_viz_type(viz_type)
    columns, saved = await _dataset_meta(client, auth, dataset_id)
    form_data = _build_form_data(dataset_id, viz_type, params)

    if columns:
        invalid = _invalid_columns(form_data, columns)
        if invalid:
            return {
                "error": ("These columns are not in the dataset — fix them and retry."),
                "invalid_columns": invalid,
                "valid_columns": sorted(columns),
            }
        _normalize_metrics(form_data, saved, columns)

    payload = await client.create_chart(
        auth,
        slice_name=chart_name,
        datasource_id=dataset_id,
        viz_type=viz_type,
        params=form_data,
        dashboards=dashboard_ids,
    )
    chart_id = payload.get("id")
    return {
        "chart_id": chart_id,
        "chart_name": chart_name,
        "viz_type": viz_type,
        "added_to_dashboards": dashboard_ids or [],
        # Relative link — open it on the same Superset origin.
        "url": f"/explore/?slice_id={chart_id}" if chart_id else None,
    }


def _dashboard_position(title: str, chart_ids: list[int]) -> dict[str, Any]:
    """Build a minimal vertical-stack dashboard layout (position_json)."""
    layout: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [],
            "parents": ["ROOT_ID"],
        },
        "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": title}},
    }
    for index, chart_id in enumerate(chart_ids, start=1):
        row_id = f"ROW-{index}"
        chart_component = f"CHART-{index}"
        layout["GRID_ID"]["children"].append(row_id)
        layout[row_id] = {
            "type": "ROW",
            "id": row_id,
            "children": [chart_component],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
            "parents": ["ROOT_ID", "GRID_ID"],
        }
        layout[chart_component] = {
            "type": "CHART",
            "id": chart_component,
            "children": [],
            "meta": {"chartId": chart_id, "width": 12, "height": 50},
            "parents": ["ROOT_ID", "GRID_ID", row_id],
        }
    return layout


async def create_dashboard(
    client: SupersetClient,
    auth: SupersetAuth,
    *,
    title: str,
    chart_ids: list[int] | None = None,
    published: bool = True,
) -> dict[str, Any]:
    """Create a dashboard and lay out the given charts on it."""
    charts = chart_ids or []
    payload: dict[str, Any] = {
        "dashboard_title": title,
        "published": published,
        "position_json": json.dumps(_dashboard_position(title, charts)),
    }
    result = await client.api_post(auth, "/api/v1/dashboard/", payload)
    dashboard_id = result.get("id")

    # position_json lays the charts out, but the chart<->dashboard link must be
    # set on each chart too, or they won't actually appear on the dashboard.
    if dashboard_id is not None:
        for chart_id in charts:
            await _link_chart_to_dashboard(client, auth, chart_id, dashboard_id)

    return {
        "dashboard_id": dashboard_id,
        "title": title,
        "chart_ids": charts,
        "url": (f"/superset/dashboard/{dashboard_id}/" if dashboard_id else None),
    }


async def _link_chart_to_dashboard(
    client: SupersetClient,
    auth: SupersetAuth,
    chart_id: int,
    dashboard_id: int,
) -> None:
    """Add ``dashboard_id`` to a chart's dashboards (preserving existing ones)."""
    existing: list[int] = []
    try:
        detail = await client.api_get(auth, f"/api/v1/chart/{chart_id}")
        result = detail.get("result")
        if isinstance(result, dict):
            existing = [d["id"] for d in result.get("dashboards", []) if "id" in d]
    except Exception:  # noqa: BLE001 - best effort; fall back to just this id
        existing = []
    if dashboard_id not in existing:
        existing.append(dashboard_id)
    await client.api_put(auth, f"/api/v1/chart/{chart_id}", {"dashboards": existing})
