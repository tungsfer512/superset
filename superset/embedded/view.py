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
from typing import Callable
import re

from flask import abort, current_app, request
from flask_appbuilder import expose
from flask_login import AnonymousUserMixin, login_user
from flask_wtf.csrf import same_origin

from superset import event_logger, is_feature_enabled
from superset.daos.dashboard import EmbeddedDashboardDAO
from superset.superset_typing import FlaskResponse
from superset.utils import json
from superset.views.base import BaseSupersetView, common_bootstrap_payload


class EmbeddedView(BaseSupersetView):
    """The views for embedded resources to be rendered in an iframe"""

    route_base = "/embedded"

    @expose("/<uuid>")
    @event_logger.log_this_with_extra_payload
    def embedded(
        self,
        uuid: str,
        add_extra_log_payload: Callable[..., None] = lambda **kwargs: None,
    ) -> FlaskResponse:
        """
        Server side rendering for the embedded dashboard page
        :param uuid: identifier for embedded dashboard
        :param add_extra_log_payload: added by `log_this_with_manual_updates`, set a
            default value to appease pylint
        """
        if not is_feature_enabled("EMBEDDED_SUPERSET"):
            abort(404)

        embedded = EmbeddedDashboardDAO.find_by_id(uuid)

        if not embedded:
            abort(404)

        assert embedded is not None

        # validate request referrer in allowed domains
        is_referrer_allowed = not embedded.allowed_domains
        for domain in embedded.allowed_domains:
            if same_origin(request.referrer, domain):
                is_referrer_allowed = True
                break

        if not is_referrer_allowed:
            abort(403)

        # Log in as an anonymous user, just for this view.
        # This view needs to be visible to all users,
        # and building the page fails if g.user and/or ctx.user aren't present.
        login_user(AnonymousUserMixin(), force=True)

        add_extra_log_payload(
            embedded_dashboard_id=uuid,
            dashboard_version="v2",
        )

        bootstrap_data = {
            "config": {
                "GUEST_TOKEN_HEADER_NAME": current_app.config["GUEST_TOKEN_HEADER_NAME"]
            },
            "common": common_bootstrap_payload(),
            "embedded": {
                "dashboard_id": embedded.dashboard_id,
            },
        }

        # Allow locale override via ?lang= for embedded dashboards.
        # Cross-origin iframes may not share cookies, so session-based locale
        # selection is unreliable in embedded mode.
        lang_param = request.args.get("lang", "")
        if lang_param and re.fullmatch(r"[a-zA-Z]{2,8}(?:_[a-zA-Z]{2,8})?", lang_param):
            configured_languages = current_app.config.get("LANGUAGES", {})
            if not configured_languages or lang_param in configured_languages:
                common = bootstrap_data["common"]
                navbar_right = common.get("navbar_right")
                menu_data = common.get("menu_data")
                menu_navbar_right = (
                    menu_data.get("navbar_right")
                    if isinstance(menu_data, dict)
                    else None
                )
                bootstrap_data["common"] = {
                    **common,
                    "locale": lang_param,
                    **(
                        {"navbar_right": {**navbar_right, "locale": lang_param}}
                        if isinstance(navbar_right, dict)
                        else {}
                    ),
                    **(
                        {
                            "menu_data": {
                                **menu_data,
                                "navbar_right": {
                                    **menu_navbar_right,
                                    "locale": lang_param,
                                },
                            }
                        }
                        if isinstance(menu_data, dict)
                        and isinstance(menu_navbar_right, dict)
                        else {}
                    ),
                }

        return self.render_template(
            "superset/spa.html",
            entry="embedded",
            bootstrap_data=json.dumps(
                bootstrap_data, default=json.pessimistic_json_iso_dttm_ser
            ),
        )
