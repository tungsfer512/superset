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
"""``?timezone=`` on the embedded page reaches the bootstrap payload.

The page needs it there because the API calls it makes afterwards carry no URL
parameters of their own -- it forwards the value as a request header instead.
"""

from typing import Any
from unittest import mock

import pytest
from flask import current_app
from pytest_mock import MockerFixture

from superset.utils import json

TZ = "Asia/Ho_Chi_Minh"


@pytest.fixture
def rendered_bootstrap(mocker: MockerFixture):
    """Render the embedded view and return its bootstrap payload."""

    def _render(url: str) -> dict[str, Any]:
        from superset.embedded.view import EmbeddedView

        embedded = mocker.MagicMock()
        embedded.dashboard_id = "1"
        embedded.allowed_domains = []
        mocker.patch(
            "superset.embedded.view.EmbeddedDashboardDAO.find_by_id",
            return_value=embedded,
        )
        mocker.patch("superset.embedded.view.is_feature_enabled", return_value=True)
        mocker.patch("superset.embedded.view.login_user")
        mocker.patch("superset.embedded.view.common_bootstrap_payload", return_value={})
        render = mocker.patch.object(EmbeddedView, "render_template")

        with current_app.test_request_context(url):
            EmbeddedView().embedded("some-uuid")

        return json.loads(render.call_args.kwargs["bootstrap_data"])

    return _render


def test_timezone_url_parameter_reaches_the_bootstrap(rendered_bootstrap) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": "UTC"}):
        bootstrap = rendered_bootstrap(f"/embedded/some-uuid?timezone={TZ}")

    config = bootstrap["config"]
    assert config["DISPLAY_TIME_ZONE"] == TZ
    assert config["DISPLAY_TIME_ZONE_HEADER_NAME"] == "X-Superset-Display-Timezone"


def test_unknown_timezone_is_not_echoed_back(rendered_bootstrap) -> None:
    """The parameter is client-supplied, so the page never sees a bad value."""
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": "UTC"}):
        bootstrap = rendered_bootstrap("/embedded/some-uuid?timezone=Not/AZone")

    assert bootstrap["config"]["DISPLAY_TIME_ZONE"] == ""


def test_no_timezone_parameter(rendered_bootstrap) -> None:
    with mock.patch.dict(current_app.config, {"DISPLAY_TIME_ZONE": "UTC"}):
        bootstrap = rendered_bootstrap("/embedded/some-uuid")

    # empty means "send no header", leaving the instance default in place
    assert bootstrap["config"]["DISPLAY_TIME_ZONE"] == ""
