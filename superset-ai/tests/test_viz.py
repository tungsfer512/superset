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
"""Tests for chart creation tool + write-tool gating."""

import asyncio
import json

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import Settings
from superset_ai.tools import viz_tools
from superset_ai.tools.registry import execute_tool, get_tool_schemas
from tests.fakes import FakeSupersetClient

AUTH = SupersetAuth(authorization="Bearer x")


def test_create_chart_returns_explore_link():
    client = FakeSupersetClient()
    result = asyncio.run(
        viz_tools.create_chart(
            client,
            AUTH,
            dataset_id=31,
            chart_name="Orders by day",
            viz_type="echarts_timeseries_bar",
            params={"metrics": ["count"]},
        )
    )
    assert result["chart_id"] == 42
    assert result["url"] == "/explore/?slice_id=42"
    # datasource + viz_type must be injected into the form_data so it renders.
    form_data = client.last_chart["params"]
    assert form_data["datasource"] == "31__table"
    assert form_data["viz_type"] == "echarts_timeseries_bar"
    assert form_data["metrics"] == ["count"]


def test_legacy_viz_types_are_normalized():
    assert viz_tools.normalize_viz_type("bar") == "echarts_timeseries_bar"
    assert viz_tools.normalize_viz_type("line") == "echarts_timeseries_line"
    assert viz_tools.normalize_viz_type("big_number") == "big_number_total"
    # histogram's registered key in this build is histogram_v2
    assert viz_tools.normalize_viz_type("histogram") == "histogram_v2"
    assert viz_tools.normalize_viz_type("heatmap") == "heatmap_v2"
    # modern keys pass through unchanged
    assert viz_tools.normalize_viz_type("pie") == "pie"
    assert viz_tools.normalize_viz_type("table") == "table"
    # unknown/unsupported -> safe fallback that always renders
    assert viz_tools.normalize_viz_type("some_made_up_viz") == "table"


def test_create_chart_normalizes_viz_type_in_form_data():
    client = FakeSupersetClient()
    result = asyncio.run(
        viz_tools.create_chart(
            client,
            AUTH,
            dataset_id=1,
            chart_name="x",
            viz_type="bar",  # legacy -> must be normalized
            params={"x_axis": "tz", "metrics": ["count"]},
        )
    )
    assert result["viz_type"] == "echarts_timeseries_bar"
    assert client.last_chart["viz_type"] == "echarts_timeseries_bar"
    assert client.last_chart["params"]["viz_type"] == "echarts_timeseries_bar"


def test_bar_chart_promotes_groupby_to_x_axis():
    client = FakeSupersetClient()
    asyncio.run(
        viz_tools.create_chart(
            client,
            AUTH,
            dataset_id=1,
            chart_name="by role",
            viz_type="bar",  # -> echarts_timeseries_bar, needs x_axis
            params={"groupby": ["role", "team"], "metrics": ["count"]},
        )
    )
    fd = client.last_chart["params"]
    assert fd["x_axis"] == "role"  # first groupby promoted
    assert fd["groupby"] == ["team"]  # remainder kept as series


def _form_data_for(viz_type, params):
    client = FakeSupersetClient()
    asyncio.run(
        viz_tools.create_chart(
            client,
            AUTH,
            dataset_id=1,
            chart_name="x",
            viz_type=viz_type,
            params=params,
        )
    )
    return client.last_chart["params"]


def test_per_viz_required_params_filled():
    # pie: dimension -> groupby, default metric
    pie = _form_data_for("pie", {"groupby": ["country"]})
    assert pie["groupby"] == ["country"]
    assert pie["metric"] == "count"
    # big number: default metric
    assert _form_data_for("big_number_total", {})["metric"] == "count"
    # histogram: column derived from dimension hint
    hist = _form_data_for("histogram", {"groupby": ["age"]})
    assert hist["viz_type"] == "histogram_v2"
    assert hist["column"] == "age"
    # world map: entity + metric
    wm = _form_data_for("world_map", {"groupby": ["country_code"]})
    assert wm["entity"] == "country_code"
    assert wm["metric"] == "count"
    # table: raw mode when no metric/dim
    tbl = _form_data_for("table", {"all_columns": ["a", "b"]})
    assert tbl["query_mode"] == "raw"
    assert tbl["all_columns"] == ["a", "b"]


def test_no_duplicate_x_axis_and_groupby():
    # x_axis already set AND same column repeated in groupby -> must be removed.
    fd = _form_data_for(
        "echarts_timeseries_bar",
        {"x_axis": "region", "groupby": ["region", "team", "team"]},
    )
    assert fd["x_axis"] == "region"
    assert fd["groupby"] == ["team"]  # region (=x_axis) and duplicate removed


def test_no_duplicate_entity_in_groupby():
    fd = _form_data_for(
        "world_map",
        {"entity": "country", "groupby": ["country", "region"]},
    )
    assert fd["entity"] == "country"
    assert "country" not in (fd.get("groupby") or [])


def test_list_viz_types_covers_supported():
    specs = viz_tools.supported_viz_types()
    assert "histogram_v2" in specs
    assert "echarts_timeseries_bar" in specs
    assert specs["pie"] == ["groupby", "metric"]


def test_create_dashboard_builds_layout_and_link():
    client = FakeSupersetClient()
    result = asyncio.run(
        viz_tools.create_dashboard(client, AUTH, title="Users", chart_ids=[10, 11])
    )
    assert result["dashboard_id"] == 99
    assert result["url"] == "/superset/dashboard/99/"
    layout = json.loads(client.last_post["position_json"])  # dashboard POST body
    # both charts referenced in the layout
    chart_ids = [
        node["meta"]["chartId"]
        for node in layout.values()
        if isinstance(node, dict) and node.get("type") == "CHART"
    ]
    assert sorted(chart_ids) == [10, 11]


def test_create_chart_adds_to_dashboards():
    client = FakeSupersetClient()
    asyncio.run(
        viz_tools.create_chart(
            client,
            AUTH,
            dataset_id=1,
            chart_name="x",
            viz_type="pie",
            params={"metric": "count", "groupby": ["country"]},
            dashboard_ids=[3, 5],
        )
    )
    assert client.last_chart["dashboards"] == [3, 5]


def test_write_tools_hidden_unless_enabled():
    names_ro = {t["name"] for t in get_tool_schemas(allow_write=False)}
    names_rw = {t["name"] for t in get_tool_schemas(allow_write=True)}
    assert "create_chart" not in names_ro
    assert "create_chart" in names_rw


def test_execute_create_chart_blocked_when_write_disabled():
    result = asyncio.run(
        execute_tool(
            "create_chart",
            {"dataset_id": 1, "chart_name": "x", "viz_type": "table"},
            client=FakeSupersetClient(),
            auth=AUTH,
            settings=Settings(allow_write_tools=False),
        )
    )
    assert "error" in result


def test_execute_create_chart_allowed_when_write_enabled():
    result = asyncio.run(
        execute_tool(
            "create_chart",
            {"dataset_id": 1, "chart_name": "x", "viz_type": "table"},
            client=FakeSupersetClient(),
            auth=AUTH,
            settings=Settings(allow_write_tools=True),
        )
    )
    assert result["chart_id"] == 42
