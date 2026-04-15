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
import json
import logging
import os
import sys

from typing import Callable, TypedDict

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
    # When using a recent version of Druid that supports JOINs turn this on
    "DRUID_JOINS": False,
    "DYNAMIC_PLUGINS": False,
    "ENABLE_TEMPLATE_PROCESSING": False,
    # Allow for javascript controls components
    # this enables programmers to customize certain charts (like the
    # geospatial ones) by inputting javascript in controls. This exposes
    # an XSS security vulnerability
    "ENABLE_JAVASCRIPT_CONTROLS": True,  # deprecated
    # When this feature is enabled, nested types in Presto will be
    # expanded into extra columns and/or arrays. This is experimental,
    # and doesn't work with all nested types.
    "PRESTO_EXPAND_DATA": False,
    # Exposes API endpoint to compute thumbnails
    "THUMBNAILS": True,
    # Enables the endpoints to cache and retrieve dashboard screenshots via webdriver.
    # Requires configuring Celery and a cache using THUMBNAIL_CACHE_CONFIG.
    "ENABLE_DASHBOARD_SCREENSHOT_ENDPOINTS": True,
    # Generate screenshots (PDF or JPG) of dashboards using the web driver.
    # When disabled, screenshots are generated on the fly by the browser.
    # This feature flag is used by the download feature in the dashboard view.
    # It is dependent on ENABLE_DASHBOARD_SCREENSHOT_ENDPOINT being enabled.
    "ENABLE_DASHBOARD_DOWNLOAD_WEBDRIVER_SCREENSHOT": True,
    "TAGGING_SYSTEM": False,
    "SQLLAB_BACKEND_PERSISTENCE": True,
    "LISTVIEWS_DEFAULT_CARD_VIEW": False,
    # When True, this escapes HTML (rather than rendering it) in Markdown components
    "ESCAPE_MARKDOWN_HTML": False,
    "DASHBOARD_VIRTUALIZATION": True,
    # Defer data loading for invisible charts when DASHBOARD_VIRTUALIZATION is enabled
    # Improves backend performance by only loading data for visible charts
    "DASHBOARD_VIRTUALIZATION_DEFER_DATA": False,
    # This feature flag is stil in beta and is not recommended for production use.
    "GLOBAL_ASYNC_QUERIES": False,
    "EMBEDDED_SUPERSET": True,
    # Enables Alerts and reports new implementation
    "ALERT_REPORTS": True,
    "ALERT_REPORT_TABS": False,
    "ALERT_REPORT_SLACK_V2": False,
    "DASHBOARD_RBAC": True,
    "ENABLE_ADVANCED_DATA_TYPES": True,
    # Enabling ALERTS_ATTACH_REPORTS, the system sends email and slack message
    # with screenshot and link
    # Disables ALERTS_ATTACH_REPORTS, the system DOES NOT generate screenshot
    # for report with type 'alert' and sends email and slack message with only link;
    # for report with type 'report' still send with email and slack message with
    # screenshot and link
    "ALERTS_ATTACH_REPORTS": True,
    # Allow users to export full CSV of table viz type.
    # This could cause the server to run out of memory or compute.
    "ALLOW_FULL_CSV_EXPORT": False,
    "ALLOW_ADHOC_SUBQUERY": False,
    "USE_ANALOGOUS_COLORS": False,
    # Apply RLS rules to SQL Lab queries. This requires parsing and manipulating the
    # query, and might break queries and/or allow users to bypass RLS. Use with care!
    "RLS_IN_SQLLAB": True,
    # Try to optimize SQL queries — for now only predicate pushdown is supported.
    "OPTIMIZE_SQL": False,
    # When impersonating a user, use the email prefix instead of the username
    "IMPERSONATE_WITH_EMAIL_PREFIX": False,
    # Enable caching per impersonation key (e.g username) in a datasource where user
    # impersonation is enabled
    "CACHE_IMPERSONATION": False,
    # Enable caching per user key for Superset cache (not database cache impersonation)
    "CACHE_QUERY_BY_USER": False,
    # Enable sharing charts with embedding
    "EMBEDDABLE_CHARTS": True,
    "DRILL_TO_DETAIL": True,  # deprecated
    "DRILL_BY": True,
    "DATAPANEL_CLOSED_BY_DEFAULT": False,
    # When you open the dashboard, the filter panel will be closed
    "FILTERBAR_CLOSED_BY_DEFAULT": True,
    # The feature is off by default, and currently only supported in Presto and Postgres,  # noqa: E501
    # and Bigquery.
    # It also needs to be enabled on a per-database basis, by adding the key/value pair
    # `cost_estimate_enabled: true` to the database `extra` attribute.
    "ESTIMATE_QUERY_COST": False,
    # Allow users to enable ssh tunneling when creating a DB.
    # Users must check whether the DB engine supports SSH Tunnels
    # otherwise enabling this flag won't have any effect on the DB.
    "SSH_TUNNELING": False,
    "AVOID_COLORS_COLLISION": True,
    # Do not show user info in the menu
    "MENU_HIDE_USER_INFO": False,
    # Allows users to add a ``superset://`` DB that can query across databases. This is
    # an experimental feature with potential security and performance risks, so use with
    # caution. If the feature is enabled you can also set a limit for how much data is
    # returned from each database in the ``SUPERSET_META_DB_LIMIT`` configuration value
    # in this file.
    "ENABLE_SUPERSET_META_DB": False,
    # Set to True to replace Selenium with Playwright to execute reports and thumbnails.
    # Unlike Selenium, Playwright reports support deck.gl visualizations
    # Enabling this feature flag requires installing "playwright" pip package
    "PLAYWRIGHT_REPORTS_AND_THUMBNAILS": False,
    # Set to True to enable experimental chart plugins
    "CHART_PLUGINS_EXPERIMENTAL": True,
    # Regardless of database configuration settings, force SQLLAB to run async
    # using Celery
    "SQLLAB_FORCE_RUN_ASYNC": False,
    # Set to True to to enable factory resent CLI command
    "ENABLE_FACTORY_RESET_COMMAND": False,
    # Whether Superset should use Slack avatars for users.
    # If on, you'll want to add "https://avatars.slack-edge.com" to the list of allowed
    # domains in your TALISMAN_CONFIG
    "SLACK_ENABLE_AVATARS": False,
    # Adds a theme editor as a modal dialog in the navbar. Allows people to type in JSON
    # Enables CSS Templates functionality in Settings menu and dashboard forms.
    # When disabled, users can still add custom CSS to dashboards but cannot use
    # pre-built CSS templates.
    "CSS_TEMPLATES": True,
    # Allow users to optionally specify date formats in email subjects, which will
    # be parsed if enabled
    "DATE_FORMAT_IN_EMAIL_SUBJECT": False,
    # Allow metrics and columns to be grouped into (potentially nested) folders in the
    # chart builder
    "DATASET_FOLDERS": False,
    # Enable Table V2 Viz plugin
    "AG_GRID_TABLE_ENABLED": True,
    # Enable Table v2 time comparison feature
    "TABLE_V2_TIME_COMPARISON_ENABLED": True,
    # Enable support for date range timeshifts (e.g., "2015-01-03 : 2015-01-04")
    # in addition to relative timeshifts (e.g., "1 day ago")
    "DATE_RANGE_TIMESHIFTS_ENABLED": True,
}

log_level_text = os.getenv("SUPERSET_LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level_text.upper(), logging.INFO)

# Allow HTML, CSS and Handlebars templates in markdown components
# Must set HTML_SANITIZATION = False to allow CSS Styles box to work
# But still use HTML_SANITIZATION_SCHEMA_EXTENSIONS for controlled sanitization
HTML_SANITIZATION = False
HTML_SANITIZATION_SCHEMA_EXTENSIONS = {
    "attributes": {
        "*": ["style", "class", "className", "id"],
    },
    "tagNames": [
        "style",
        "div",
        "span",
        "ul",
        "li",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ],
    "strip": False,
}

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
    "origins": "*",
    "allow_headers": ["*"],
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    "expose_headers": ["*"],
}
SESSION_COOKIE_SAMESITE = None
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False

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

# Specify the App icon
APP_ICON = os.getenv("APP_ICON", "/static/assets/images/superset-logo-horiz.png")

# Specify where clicking the logo would take the user'
# Default value of None will take you to '/superset/welcome'
# You can also specify a relative URL e.g. '/superset/welcome' or '/dashboards/list'
# or you can specify a full URL e.g. 'https://foo.bar'
LOGO_TARGET_PATH = os.getenv("LOGO_TARGET_PATH", "/superset/welcome")

# Specify tooltip that should appear when hovering over the App Icon/Logo
LOGO_TOOLTIP = os.getenv("LOGO_TOOLTIP", "Dashboard")

# Specify any text that should appear to the right of the logo
LOGO_RIGHT_TEXT: Callable[[], str] | str = os.getenv("LOGO_RIGHT_TEXT", "Dashboard")

# Multiple favicons can be specified here. The "href" property
# is mandatory, but "sizes," "type," and "rel" are optional.
# For example:
# {
#     "href": "/static/assets/images/favicon.png",
#     "sizes": "16x16",
#     "type": "image/png"
#     "rel": "icon"
# },
FAVICONS = json.loads(
    str(os.getenv("FAVICONS", [{"href": "/static/assets/images/favicon.png"}]))
)

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
class D3Format(TypedDict, total=False):
    decimal: str
    thousands: str
    grouping: list[int]
    currency: list[str]


D3_FORMAT: D3Format = {
    "decimal": ".",
    "thousands": ",",
    "grouping": [3],
    "currency": ["", "đ"],
}

# Override the default d3 locale for time format
# Default values are equivalent to
# D3_TIME_FORMAT = {
#     "dateTime": "%x, %X",
#     "date": "%-m/%-d/%Y",
#     "time": "%-I:%M:%S %p",
#     "periods": ["AM", "PM"],
#     "days": ["Sunday", "Monday", "Tuesday", "Wednesday",
#              "Thursday", "Friday", "Saturday"],
#     "shortDays": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
#     "months": ["January", "February", "March", "April",
#                "May", "June", "July", "August",
#                "September", "October", "November", "December"],
#     "shortMonths": ["Jan", "Feb", "Mar", "Apr",
#                     "May", "Jun", "Jul", "Aug",
#                     "Sep", "Oct", "Nov", "Dec"]
# }
# https://github.com/d3/d3-time-format/tree/main#locales
class D3TimeFormat(TypedDict, total=False):
    date: str
    dateTime: str
    time: str
    periods: list[str]
    days: list[str]
    shortDays: list[str]
    months: list[str]
    shortMonths: list[str]


D3_TIME_FORMAT: D3TimeFormat = {
    "dateTime": "%x, %X",
    "date": "%-m/%-d/%Y",
    "time": "%-I:%M:%S %p",
    "periods": ["AM", "PM"],
    "days": [
        "Chủ nhật",
        "Thứ hai",
        "Thứ ba",
        "Thứ tư",
        "Thứ năm",
        "Thứ sáu",
        "Thứ bảy",
    ],
    "shortDays": [
        "Chủ nhật",
        "Thứ hai",
        "Thứ ba",
        "Thứ tư",
        "Thứ năm",
        "Thứ sáu",
        "Thứ bảy",
    ],
    "months": [
        "Tháng một",
        "Tháng hai",
        "Tháng ba",
        "Tháng tư",
        "Tháng năm",
        "Tháng sáu",
        "Tháng bảy",
        "Tháng tám",
        "Tháng chín",
        "Tháng mười",
        "Tháng mười một",
        "Tháng mười hai",
    ],
    "shortMonths": [
        "Tháng một",
        "Tháng hai",
        "Tháng ba",
        "Tháng tư",
        "Tháng năm",
        "Tháng sáu",
        "Tháng bảy",
        "Tháng tám",
        "Tháng chín",
        "Tháng mười",
        "Tháng mười một",
        "Tháng mười hai",
    ],
}

CURRENCIES = ["VND", "USD", "EUR", "GBP", "INR", "MXN", "JPY", "CNY"]

PREFERRED_DATABASES: list[str] = [
    "PostgreSQL",
    "Presto",
    "MySQL",
    "SQLite",
    # etc.
]

#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa: F403

    logger.info(
        f"Loaded your Docker configuration at [{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")
