# Override default Superset config with env vars for easier configuration in docker-compose

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
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os

logger = logging.getLogger()

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

SQLALCHEMY_EXAMPLES_URI = (
    f"{DATABASE_DIALECT}://"
    f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
    f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
)

FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "GUEST_TOKEN": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_NATIVE_FILTERS_SET": True,
    "DASHBOARD_NATIVE_FILTERS_USE_CACHE": False,
    # Exposes a live JSON theme editor in the navbar for tuning the theme below
    "ENABLE_THEME_EDITOR": True,
}

# ---------------------------------------------------
# UI Theme — "Teal modern" brand (TOGGLE)
# Flip APPLY_BRAND_THEME to True to enable the teal brand theme, logo and font.
# All definitions are kept below so it's easy to re-enable / tweak later.
# Live-editable via the navbar Theme Editor (ENABLE_THEME_EDITOR).
# ---------------------------------------------------
APPLY_BRAND_THEME = False

_BRAND_LIGHT = "#0E9F9F"
_BRAND_DARK = "#2DD4BF"
_FONT_STACK = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

_BRAND_TEXT = "#0A201E"

_LOGO_TOKENS = {
    "brandLogoUrl": "/static/assets/images/brand-logo.svg",
    "brandLogoHref": "/",
    "brandLogoAlt": "Dashboard",
    "brandLogoHeight": "30px",
    "brandLogoMargin": "16px",
}

_BRAND_THEME_DEFAULT = {
    "token": {
        "colorPrimary": _BRAND_LIGHT,
        "colorInfo": _BRAND_LIGHT,
        "colorLink": _BRAND_LIGHT,
        "colorSuccess": "#15924E",
        "colorWarning": "#C7790B",
        "colorError": "#DC2F44",
        # Higher-contrast neutrals (cool, biased toward the teal accent)
        "colorText": _BRAND_TEXT,
        "colorTextSecondary": "#3E5754",
        "colorBgLayout": "#E7EFEE",
        "colorBgContainer": "#FFFFFF",
        "colorBorder": "#C6D5D2",
        "colorBorderSecondary": "#DAE5E3",
        "borderRadius": 12,
        "borderRadiusLG": 18,
        "borderRadiusSM": 8,
        "controlHeight": 40,
        "fontFamily": _FONT_STACK,
        "fontSize": 14,
        "fontWeightStrong": 700,
        "wireframe": False,
        "boxShadow": "0 1px 2px rgba(10,32,30,.06), 0 12px 28px -12px rgba(10,32,30,.18)",
        "boxShadowSecondary": "0 8px 24px -10px rgba(10,32,30,.18)",
        **_LOGO_TOKENS,
    },
    "components": {
        "Button": {"controlHeight": 40, "fontWeight": 700, "borderRadius": 12, "primaryShadow": "none"},
        "Card": {"borderRadiusLG": 18, "paddingLG": 22},
        "Menu": {"itemBorderRadius": 10, "itemSelectedBg": "#E2F6F4", "itemSelectedColor": "#0B8585"},
        "Table": {
            "headerBg": "#E6F4F2",
            "headerColor": "#0B6E6E",
            "headerSplitColor": "transparent",
            "borderColor": "#E0EAE8",
            "rowHoverBg": "#F0FAF9",
            "cellPaddingBlock": 12,
            "borderRadiusLG": 16,
        },
        "Input": {"controlHeight": 40, "borderRadius": 12, "activeShadow": "0 0 0 3px rgba(14,159,159,.16)"},
        "InputNumber": {"controlHeight": 40, "borderRadius": 12},
        "Select": {"controlHeight": 40, "borderRadius": 12},
        "Tabs": {"inkBarColor": _BRAND_LIGHT, "itemSelectedColor": _BRAND_LIGHT, "itemHoverColor": "#0B8585", "titleFontSize": 14},
        "Modal": {"borderRadiusLG": 18},
        "Tag": {"borderRadiusSM": 8},
        "Segmented": {"borderRadius": 10, "itemSelectedBg": _BRAND_LIGHT, "itemSelectedColor": "#FFFFFF"},
        "Pagination": {"borderRadius": 10, "itemActiveBg": _BRAND_LIGHT},
        "Tooltip": {"borderRadius": 8},
        "Switch": {"colorPrimary": _BRAND_LIGHT},
        "Slider": {"colorPrimary": _BRAND_LIGHT},
    },
}

_BRAND_THEME_DARK = {
    "algorithm": "dark",
    "token": {
        "colorPrimary": _BRAND_DARK,
        "colorInfo": _BRAND_DARK,
        "colorLink": _BRAND_DARK,
        "colorSuccess": "#34D399",
        "colorWarning": "#FBBF24",
        "colorError": "#FB7185",
        "colorText": "#E9F3F1",
        "colorTextSecondary": "#A6C0BC",
        "colorBgLayout": "#070F0E",
        "colorBgContainer": "#0F201E",
        "colorBgElevated": "#152825",
        "colorBorder": "#234440",
        "colorBorderSecondary": "#1A332F",
        "borderRadius": 12,
        "borderRadiusLG": 18,
        "borderRadiusSM": 8,
        "controlHeight": 40,
        "fontFamily": _FONT_STACK,
        "fontSize": 14,
        "fontWeightStrong": 700,
        "wireframe": False,
        "boxShadow": "0 1px 2px rgba(0,0,0,.5), 0 14px 34px -14px rgba(0,0,0,.6)",
        **_LOGO_TOKENS,
    },
    "components": {
        "Button": {"controlHeight": 40, "fontWeight": 700, "borderRadius": 12, "primaryShadow": "none"},
        "Card": {"borderRadiusLG": 18, "paddingLG": 22},
        "Menu": {"itemBorderRadius": 10},
        "Table": {
            "headerBg": "#13302C",
            "headerColor": "#5EEAD4",
            "headerSplitColor": "transparent",
            "rowHoverBg": "#13302C",
            "cellPaddingBlock": 12,
        },
        "Input": {"controlHeight": 40, "borderRadius": 12},
        "InputNumber": {"controlHeight": 40, "borderRadius": 12},
        "Select": {"controlHeight": 40, "borderRadius": 12},
        "Tabs": {"inkBarColor": _BRAND_DARK, "itemSelectedColor": _BRAND_DARK},
        "Modal": {"borderRadiusLG": 18},
        "Tag": {"borderRadiusSM": 8},
        "Segmented": {"borderRadius": 10, "itemSelectedBg": _BRAND_DARK, "itemSelectedColor": "#062322"},
        "Pagination": {"borderRadius": 10},
        "Tooltip": {"borderRadius": 8},
    },
}

# Inter font (loaded at runtime when the brand theme is on)
_BRAND_FONT_URLS = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
]

# Brand logo + chart palette (used when the brand theme is on)
_BRAND_APP_ICON = "/static/assets/images/brand-logo.svg"
_BRAND_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "supersetTeal",
        "label": "Teal Brand",
        "description": "Teal-led brand palette",
        "isDefault": True,
        "colors": [
            "#0E9F9F", "#23C9B9", "#5F6FEF", "#E8A93B", "#E1485B",
            "#14B8A6", "#0B8585", "#818CF8", "#16A34A", "#9333EA",
        ],
    }
]

# ---- Apply the theme based on the toggle above ----
if APPLY_BRAND_THEME:
    THEME_DEFAULT = _BRAND_THEME_DEFAULT
    THEME_DARK = _BRAND_THEME_DARK
    CUSTOM_FONT_URLS = _BRAND_FONT_URLS
    EXTRA_CATEGORICAL_COLOR_SCHEMES = _BRAND_CATEGORICAL_COLOR_SCHEMES
    APP_ICON = _BRAND_APP_ICON
    APP_ICON_WIDTH = 150
    LOGO_TOOLTIP = "Dashboard"
else:
    # Original Superset colors / logo
    THEME_DEFAULT = {"algorithm": "default"}
    THEME_DARK = {"algorithm": "dark"}
    CUSTOM_FONT_URLS = []
    EXTRA_CATEGORICAL_COLOR_SCHEMES = []
    APP_ICON = "/static/assets/images/superset-logo-horiz.png"


# Allow HTML, CSS and Handlebars templates in markdown components
# Must set HTML_SANITIZATION = False to allow CSS Styles box to work
# But still use HTML_SANITIZATION_SCHEMA_EXTENSIONS for controlled sanitization
HTML_SANITIZATION = False

BABEL_DEFAULT_LOCALE = os.getenv("BABEL_DEFAULT_LOCALE", "vi")
BABEL_DEFAULT_TIMEZONE = os.getenv("BABEL_DEFAULT_TIMEZONE", "Asia/Ho_Chi_Minh")

LANGUAGES = {
    "vi": {"flag": "vn", "name": "Tiếng Việt"},
    "en": {"flag": "us", "name": "English"},
    "fr": {"flag": "fr", "name": "French"},
    "pt_BR": {"flag": "br", "name": "Brazilian Portuguese"},
    "es": {"flag": "es", "name": "Spanish"},
    "it": {"flag": "it", "name": "Italian"},
    "zh": {"flag": "cn", "name": "Chinese"},
    "ja": {"flag": "jp", "name": "Japanese"},
    "de": {"flag": "de", "name": "German"},
    "pt": {"flag": "pt", "name": "Portuguese"},
    "ru": {"flag": "ru", "name": "Russian"},
    "ko": {"flag": "kr", "name": "Korean"},
    "sl": {"flag": "si", "name": "Slovenian"},
}

ENVIRONMENT_TAG_CONFIG = {
    "variable": "SUPERSET_ENV",
    "values": {
        "debug": {"color": "", "text": ""},
        "development": {"color": "", "text": ""},
        "production": {"color": "", "text": ""},
    },
}

SECRET_KEY = os.getenv(
    "SUPERSET_SECRET_KEY", "your-super-secret-key-here-please-change-in-production"
)

WTF_CSRF_ENABLED = False

TALISMAN_ENABLED = False

ALLOWED_EMBEDDED_DOMAINS_ENV = os.environ.get("ALLOWED_EMBEDDED_DOMAINS", "").strip()
if ALLOWED_EMBEDDED_DOMAINS_ENV == "*":
    ALLOWED_EMBEDDED_DOMAINS = ["*"]
else:
    ALLOWED_EMBEDDED_DOMAINS = [
        d.strip() for d in ALLOWED_EMBEDDED_DOMAINS_ENV.split(",") if d.strip()
    ]
    if not ALLOWED_EMBEDDED_DOMAINS:
        ALLOWED_EMBEDDED_DOMAINS = ["*"]


OVERRIDE_HTTP_HEADERS = {
    "Content-Security-Policy": "frame-ancestors *;",
}
ENABLE_PROXY_FIX = True


ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": False,
    "origins": [
        "*",
    ],
    "allow_headers": ["*"],
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    "expose_headers": ["*"],
}
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True

PUBLIC_ROLE_LIKE = "Gamma"
GUEST_ROLE_NAME = "Gamma"
GUEST_TOKEN_JWT_PUBLIC_KEY = ""

SQLLAB_ASYNC_TIME_LIMIT_SEC = 60 * 60 * 6  # 6 hours
SQLALCHEMY_POOL_SIZE = 15
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_TIMEOUT = 180

# ------------------------------
# GLOBALS FOR APP Builder
# ------------------------------
# Uncomment to setup Your App name
APP_NAME = os.getenv("APP_NAME", "Dashboard")

# This is an important setting, and should be lower than your
# [load balancer / proxy / envoy / kong / ...] timeout settings.
# You should also make sure to configure your WSGI server
# (gunicorn, nginx, apache, ...) timeout setting to be <= to this setting
SUPERSET_WEBSERVER_TIMEOUT = 60 * 5


# Override the default d3 locale format
# Default values are equivalent to
# D3_FORMAT = {
#     "decimal": ".",           # - decimal place string (e.g., ".").
#     "thousands": ",",         # - group separator string (e.g., ",").
#     "grouping": [3],          # - array of group sizes (e.g., [3]), cycled as needed.
#     "currency": ["$", ""]     # - currency prefix/suffix strings (e.g., ["$", ""])
# }
# https://github.com/d3/d3-format/blob/main/README.md#formatLocale
D3_FORMAT = {
    "decimal": ".",
    "thousands": ",",
    "grouping": [3],
    "currency": ["", "đ"],
}

CURRENCIES = ["VND", "USD", "EUR", "GBP", "INR", "MXN", "JPY", "CNY"]

PREFERRED_DATABASES: list[str] = [
    "StarRocks",
    "ClickHouse Connect (Superset)",
    "PostgreSQL",
    "MySQL",
    "Google Sheets",
    "Trino",
]

# =====================================================================
# Keycloak SSO (OpenID Connect via OAuth) — TOGGLE
# ---------------------------------------------------------------------
# Turn ON by setting env var  ENABLE_KEYCLOAK_SSO=true
# When OFF (default) nothing below runs and Superset keeps its normal
# database login — zero impact.
#
# Env vars (only read when enabled):
#   KEYCLOAK_BASE_URL       e.g. https://keycloak.example.com   (no trailing /)
#   KEYCLOAK_REALM          e.g. myrealm
#   KEYCLOAK_CLIENT_ID      e.g. superset
#   KEYCLOAK_CLIENT_SECRET  confidential client secret
#   KEYCLOAK_DEFAULT_ROLE   Superset role for new users (default: Gamma)
#   KEYCLOAK_ROLE_SYNC      "true" to sync roles from Keycloak each login
#
# Keycloak client setup:
#   - OpenID Connect client, "Client authentication" ON (confidential)
#   - Standard flow enabled
#   - Valid redirect URI:  https://<superset-host>/oauth-authorized/keycloak
#   - (for role sync) add realm/client roles + a "roles" token mapper
# =====================================================================
ENABLE_KEYCLOAK_SSO = os.getenv("ENABLE_KEYCLOAK_SSO", "false").lower() in (
    "true",
    "1",
    "yes",
)

if ENABLE_KEYCLOAK_SSO:
    import logging as _kc_logging

    import sqlalchemy as _sa
    from sqlalchemy.orm import relationship as _sa_relationship
    from urllib.parse import quote as _url_quote

    from flask import flash, g, redirect, request
    from flask_appbuilder import BaseView, Model, ModelView, expose
    from flask_appbuilder._compat import as_unicode
    from flask_appbuilder.models.sqla.interface import SQLAInterface
    from flask_appbuilder.security.forms import LoginForm_db
    from flask_appbuilder.security.manager import AUTH_OAUTH
    from flask_appbuilder.security.views import AuthOAuthView
    from flask_appbuilder.utils.base import get_safe_redirect
    from flask_login import login_user, logout_user

    from superset.security import SupersetSecurityManager

    # ---- DB-backed dynamic role mapping (managed via an admin CRUD page) ----
    class KeycloakRoleMapping(Model):
        """One row = map a Keycloak role name -> an existing Superset role."""

        __tablename__ = "keycloak_role_mapping"
        __table_args__ = {"extend_existing": True}

        id = _sa.Column(_sa.Integer, primary_key=True)
        keycloak_role = _sa.Column(_sa.String(255), nullable=False)
        # FK to the FAB role table -> rendered as a Select2 dropdown of roles
        superset_role_id = _sa.Column(
            _sa.Integer,
            _sa.ForeignKey("ab_role.id", ondelete="CASCADE"),
            nullable=False,
        )
        superset_role = _sa_relationship("Role")

        def __repr__(self) -> str:
            return f"{self.keycloak_role} -> {self.superset_role}"

    _kc_base = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
    _kc_realm = os.getenv("KEYCLOAK_REALM", "master")
    _kc_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "superset")
    _kc_realm_url = f"{_kc_base}/realms/{_kc_realm}"
    _kc_oidc = f"{_kc_realm_url}/protocol/openid-connect"

    class KeycloakAuthOAuthView(AuthOAuthView):
        """Single Logout: clear the local Superset session AND end the Keycloak
        SSO session, so logging out truly logs the user out (next login prompts
        for credentials again instead of silently re-authenticating)."""

        @expose("/logout/")
        def logout(self):
            logout_user()  # drop the local Flask/Superset session
            # RP-initiated logout at Keycloak, returning to Superset afterwards.
            post_logout = request.url_root
            kc_logout = (
                f"{_kc_oidc}/logout?client_id={_kc_client_id}"
                f"&post_logout_redirect_uri={_url_quote(post_logout, safe='')}"
            )
            return redirect(kc_logout)

    AUTH_TYPE = AUTH_OAUTH

    OAUTH_PROVIDERS = [
        {
            "name": "keycloak",
            "icon": "fa-key",
            "token_key": "access_token",
            "remote_app": {
                "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "superset"),
                "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET", ""),
                "server_metadata_url": (
                    f"{_kc_realm_url}/.well-known/openid-configuration"
                ),
                "api_base_url": f"{_kc_oidc}/",
                "access_token_url": f"{_kc_oidc}/token",
                "authorize_url": f"{_kc_oidc}/auth",
                "jwks_uri": f"{_kc_oidc}/certs",
                "client_kwargs": {"scope": "openid email profile"},
            },
        }
    ]

    # Auto-create a Superset user on first SSO login
    AUTH_USER_REGISTRATION = os.getenv("AUTH_USER_REGISTRATION", "False").lower() in ("true", "1", "yes")
    AUTH_USER_REGISTRATION_ROLE = os.getenv("AUTH_USER_REGISTRATION_ROLE", "Gamma")

    # Optional: sync Superset roles from Keycloak roles on each login.
    # Keep OFF until AUTH_ROLES_MAPPING is configured, otherwise users may end
    # up with no roles. New users always get AUTH_USER_REGISTRATION_ROLE.
    AUTH_ROLES_SYNC_AT_LOGIN = os.getenv("KEYCLOAK_ROLE_SYNC", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    # Map a Keycloak (realm or client) role -> Superset role(s)
    AUTH_ROLES_MAPPING = {
        "superset_admin": ["Admin"],
        "superset_alpha": ["Alpha"],
        "superset_gamma": ["Gamma"],
    }

    class _DBLoginPostView(BaseView):
        """Restore username/password (DB) login while AUTH_TYPE=AUTH_OAUTH.

        The React login page already renders BOTH the DB form and the Keycloak
        button, but under OAUTH the framework registers no POST handler for
        /login/. This view adds that POST handler so both methods work together
        (GET /login/ stays the normal React page; OAuth uses /login/<provider>).
        """

        route_base = ""

        @expose("/login/", methods=["POST"])
        def login_db_post(self):  # noqa: D401
            if g.user is not None and g.user.is_authenticated:
                return redirect(self.appbuilder.get_url_for_index)
            next_url = get_safe_redirect(request.args.get("next", ""))
            form = LoginForm_db()
            if form.validate_on_submit():
                user = self.appbuilder.sm.auth_user_db(
                    form.username.data, form.password.data
                )
                if user:
                    login_user(user, remember=False)
                    return redirect(next_url or self.appbuilder.get_url_for_index)
                flash(as_unicode("Invalid login. Please try again."), "warning")
            return redirect(self.appbuilder.get_url_for_login)

    class KeycloakSecurityManager(SupersetSecurityManager):
        """Map Keycloak user info + roles onto Superset accounts and keep the
        database login working alongside the Keycloak SSO button."""

        # Use the SLO-aware OAuth view so /logout/ also ends the Keycloak session.
        authoauthview = KeycloakAuthOAuthView

        def register_views(self):
            super().register_views()
            # add the POST /login/ DB-auth handler (GET /login/ = React page)
            self.appbuilder.add_view_no_menu(_DBLoginPostView())
            # ensure the mapping table exists
            try:
                from superset import db

                KeycloakRoleMapping.__table__.create(
                    bind=db.engine, checkfirst=True
                )
            except Exception as ex:  # noqa: BLE001
                _kc_logging.getLogger(__name__).warning(
                    "Keycloak role-mapping table not ready: %s", ex
                )

            # --- React admin page: REST API + SPA view + Security menu link ---
            from flask_appbuilder.security.decorators import (
                has_access,
                permission_name,
            )
            from superset.constants import (
                MODEL_API_RW_METHOD_PERMISSION_MAP,
                RouteMethod,
            )
            from superset.views.base import BaseSupersetView
            from superset.views.base_api import BaseSupersetModelRestApi

            class KeycloakRoleMappingRestApi(BaseSupersetModelRestApi):
                datamodel = SQLAInterface(KeycloakRoleMapping)
                resource_name = "keycloak_role_mapping"
                allow_browser_login = True
                class_permission_name = "KeycloakRoleMapping"
                method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP
                include_route_methods = (
                    RouteMethod.REST_MODEL_VIEW_CRUD_SET | {RouteMethod.RELATED}
                )
                list_columns = [
                    "id",
                    "keycloak_role",
                    "superset_role.id",
                    "superset_role.name",
                ]
                show_columns = list_columns
                add_columns = ["keycloak_role", "superset_role"]
                edit_columns = add_columns
                order_columns = ["keycloak_role"]
                search_columns = ["keycloak_role"]
                base_order = ("keycloak_role", "asc")
                allowed_rel_fields = {"superset_role"}

            class KeycloakRoleMappingPageView(BaseSupersetView):
                route_base = "/"
                class_permission_name = "security"

                @expose("/keycloak-role-mapping/")
                @has_access
                @permission_name("read")
                def list(self):
                    return super().render_app_template()

            self.appbuilder.add_api(KeycloakRoleMappingRestApi)
            self.appbuilder.add_view(
                KeycloakRoleMappingPageView,
                "Keycloak Role Mapping",
                label="Keycloak Role Mapping",
                category="Security",
                category_label="Security",
                icon="fa-exchange",
            )

        def _oauth_calculate_user_roles(self, userinfo):
            """Dynamic role mapping (only used when KEYCLOAK_ROLE_SYNC=true).

            Keeps the explicit AUTH_ROLES_MAPPING + registration role, then ALSO
            auto-assigns any Keycloak role whose name matches an existing
            Superset role name. So adding a new role only requires creating it
            in Superset + Keycloak with the same name — no config change.
            """
            roles = super()._oauth_calculate_user_roles(userinfo)
            seen = {r.name for r in roles}
            kc_roles = set(userinfo.get("role_keys", []))

            def _add(superset_role_name):
                role = self.find_role(superset_role_name)
                if role and role.name not in seen:
                    roles.append(role)
                    seen.add(role.name)

            # (a) dynamic: Keycloak role name == Superset role name
            for role_key in kc_roles:
                _add(role_key)

            # (b) mappings configured via the admin CRUD page (DB table)
            try:
                from superset import db

                for mapping in db.session.query(KeycloakRoleMapping).all():
                    if mapping.keycloak_role in kc_roles and mapping.superset_role:
                        _add(mapping.superset_role.name)
            except Exception as ex:  # noqa: BLE001
                _kc_logging.getLogger(__name__).warning(
                    "Keycloak role-mapping lookup failed: %s", ex
                )
            return roles

        def auth_user_oauth(self, userinfo):
            """Auto-provision the Keycloak user on SSO login.

            FAB only auto-creates OAuth users when AUTH_USER_REGISTRATION is
            True. We keep that global flag False (so no OTHER path can
            self-register) yet still create the account for anyone who
            authenticates through Keycloak. This mirrors FAB's own
            ``auth_user_oauth`` minus the registration gate.
            """
            username = userinfo.get("username") or userinfo.get("email")
            if not username:
                _kc_logging.getLogger(__name__).error(
                    "Keycloak SSO: userinfo missing username/email: %s", userinfo
                )
                return None

            user = self.find_user(username=username)
            if user and not user.is_active:
                return None

            # Keep roles in sync for existing users (when enabled).
            if user and self.auth_roles_sync_at_login:
                user.roles = self._oauth_calculate_user_roles(userinfo)

            # New user: create it regardless of AUTH_USER_REGISTRATION.
            if not user:
                user = self.add_user(
                    username=username,
                    first_name=userinfo.get("first_name", ""),
                    last_name=userinfo.get("last_name", ""),
                    email=userinfo.get("email", "") or f"{username}@email.notfound",
                    role=self._oauth_calculate_user_roles(userinfo),
                )
                if not user:
                    _kc_logging.getLogger(__name__).error(
                        "Keycloak SSO: failed to auto-create user %s", username
                    )
                    return None

            self.update_user_auth_stat(user)
            return user

        def oauth_user_info(self, provider, response=None):
            if provider != "keycloak":
                return {}
            userinfo = self.oauth_remotes[provider].get("userinfo").json()
            roles: list[str] = []
            try:
                import jwt as _jwt

                claims = _jwt.decode(
                    response["access_token"],
                    options={"verify_signature": False},
                )
                roles += (claims.get("realm_access") or {}).get("roles", [])
                for _client_access in (claims.get("resource_access") or {}).values():
                    roles += (_client_access or {}).get("roles", [])
            except Exception as ex:  # noqa: BLE001
                _kc_logging.getLogger(__name__).warning(
                    "Keycloak SSO: could not parse roles from token: %s", ex
                )
            return {
                "username": userinfo.get("preferred_username")
                or userinfo.get("email"),
                "email": userinfo.get("email", ""),
                "first_name": userinfo.get("given_name", ""),
                "last_name": userinfo.get("family_name", ""),
                "role_keys": roles,
            }

    CUSTOM_SECURITY_MANAGER = KeycloakSecurityManager
