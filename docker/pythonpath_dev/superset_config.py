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
