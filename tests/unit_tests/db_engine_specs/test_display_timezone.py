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
"""SQL generated for the ``DISPLAY_TIME_ZONE`` setting."""

import pytest
from sqlalchemy import column, types
from sqlalchemy.dialects import postgresql

TZ = "Asia/Ho_Chi_Minh"


def _compile(expr) -> str:
    return str(expr.compile(None, dialect=postgresql.dialect()))


def test_no_time_zone_is_a_noop() -> None:
    from superset.db_engine_specs.postgres import PostgresEngineSpec

    expr = PostgresEngineSpec.get_timestamp_expr(column("ts"), None, None, None)
    assert _compile(expr) == "ts"


def test_postgres_naive_column() -> None:
    from superset.db_engine_specs.postgres import PostgresEngineSpec

    expr = PostgresEngineSpec.get_timestamp_expr(column("ts"), None, None, TZ)
    assert _compile(expr) == "(ts AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh')"


def test_postgres_tz_aware_column_is_not_double_converted() -> None:
    from superset.db_engine_specs.postgres import PostgresEngineSpec

    col = column("ts", type_=types.TIMESTAMP(timezone=True))
    expr = PostgresEngineSpec.get_timestamp_expr(col, None, None, TZ)
    assert _compile(expr) == "(ts AT TIME ZONE 'Asia/Ho_Chi_Minh')"


def test_tz_awareness_comes_from_the_declared_type() -> None:
    """`get_column_spec` maps timestamptz and timestamp to the same SQLA type.

    `TIMESTAMP WITH TIME ZONE` and `TIMESTAMP` both come back as
    `types.TIMESTAMP()` with `timezone=False`, so the SQLAlchemy type cannot
    tell them apart and the database's own type name has to be passed in.
    Without it a zone-aware column is converted twice.
    """
    from superset.db_engine_specs.postgres import PostgresEngineSpec

    # what `get_column_spec` actually hands back for a timestamptz column
    col = column("ts", type_=types.TIMESTAMP())
    assert PostgresEngineSpec.get_column_spec("TIMESTAMP WITH TIME ZONE")
    assert (
        getattr(
            PostgresEngineSpec.get_column_spec("TIMESTAMP WITH TIME ZONE").sqla_type,
            "timezone",
            False,
        )
        is False
    )

    expr = PostgresEngineSpec.get_timestamp_expr(
        col, None, None, TZ, native_type="TIMESTAMP WITH TIME ZONE"
    )
    assert _compile(expr) == "(ts AT TIME ZONE 'Asia/Ho_Chi_Minh')"

    # ...while a naive column of the same SQLA type still gets both steps
    expr = PostgresEngineSpec.get_timestamp_expr(
        col, None, None, TZ, native_type="TIMESTAMP"
    )
    assert _compile(expr) == "(ts AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh')"


def test_grain_is_applied_after_the_conversion() -> None:
    """A "day" must be a day in the target zone, not in UTC."""
    from superset.db_engine_specs.postgres import PostgresEngineSpec

    expr = PostgresEngineSpec.get_timestamp_expr(column("ts"), None, "P1D", TZ)
    assert _compile(expr) == (
        "DATE_TRUNC('day', (ts AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh'))"
    )


def test_epoch_is_decoded_before_the_conversion() -> None:
    from superset.db_engine_specs.postgres import PostgresEngineSpec

    expr = PostgresEngineSpec.get_timestamp_expr(column("ts"), "epoch_s", None, TZ)
    assert _compile(expr) == (
        "((timestamp 'epoch' + ts * interval '1 second') "
        "AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Ho_Chi_Minh')"
    )


def test_offset_based_engines_substitute_the_offset() -> None:
    """Engines with no time zone database of their own shift by a fixed offset.

    DST is therefore not tracked on these: a zone that observes it is shifted
    by the offset in force when the query was built.
    """
    from superset.db_engine_specs.mssql import MssqlEngineSpec
    from superset.db_engine_specs.sqlite import SqliteEngineSpec

    assert MssqlEngineSpec.get_utc_to_tz_expression(TZ) == (
        "DATEADD(MINUTE, 420, {col})"
    )
    assert SqliteEngineSpec.get_utc_to_tz_expression(TZ) == (
        "DATETIME({col}, '420 minutes')"
    )


def test_mysql_prefers_named_zones_and_falls_back_to_an_offset() -> None:
    """`CONVERT_TZ` needs the server's time zone tables to resolve a name.

    Where they are loaded -- the official images and the managed offerings ship
    them -- the named branch is DST correct. Where they are not, `CONVERT_TZ`
    returns NULL rather than failing, which would blank every timestamp, so the
    offset branch catches it.
    """
    from superset.db_engine_specs.mysql import MySQLEngineSpec
    from superset.db_engine_specs.starrocks import StarRocksEngineSpec

    expected = (
        "COALESCE("
        "CONVERT_TZ({col}, 'UTC', 'Asia/Ho_Chi_Minh'), "
        "CONVERT_TZ({col}, '+00:00', '+07:00')"
        ")"
    )
    assert MySQLEngineSpec.get_utc_to_tz_expression(TZ) == expected
    # StarRocks implements the same function and inherits the template
    assert StarRocksEngineSpec.get_utc_to_tz_expression(TZ) == expected


def test_named_zone_engines_substitute_the_name() -> None:
    from superset.db_engine_specs.clickhouse import ClickHouseEngineSpec
    from superset.db_engine_specs.trino import TrinoEngineSpec

    assert TrinoEngineSpec.get_utc_to_tz_expression(TZ) == (
        "CAST(with_timezone({col}, 'UTC') AT TIME ZONE 'Asia/Ho_Chi_Minh' AS TIMESTAMP)"
    )
    assert ClickHouseEngineSpec.get_utc_to_tz_expression(TZ) == (
        "toTimeZone(toDateTime({col}), 'Asia/Ho_Chi_Minh')"
    )


def test_bigquery_conversion_is_type_preserving() -> None:
    """The grain expressions key off `{func}`/`{type}`, so the type must survive."""
    from superset.db_engine_specs.bigquery import BigQueryEngineSpec

    assert BigQueryEngineSpec.is_tz_aware_column_type("TIMESTAMP") is True
    assert BigQueryEngineSpec.is_tz_aware_column_type("DATETIME") is False

    # DATETIME in, DATETIME out
    assert BigQueryEngineSpec.get_utc_to_tz_expression(TZ) == (
        "DATETIME(CAST({col} AS TIMESTAMP), 'Asia/Ho_Chi_Minh')"
    )
    # TIMESTAMP in, TIMESTAMP out
    assert BigQueryEngineSpec.get_utc_to_tz_expression(TZ, tz_aware=True) == (
        "TIMESTAMP(DATETIME({col}, 'Asia/Ho_Chi_Minh'), 'UTC')"
    )


def test_unsupported_engine_is_left_unconverted() -> None:
    from superset.db_engine_specs.base import BaseEngineSpec

    assert BaseEngineSpec.utc_to_tz_expression is None
    assert BaseEngineSpec.get_utc_to_tz_expression(TZ) is None
    expr = BaseEngineSpec.get_timestamp_expr(column("ts"), None, None, TZ)
    assert _compile(expr) == "ts"


@pytest.mark.parametrize(
    "engine_module,engine_class",
    [
        ("postgres", "PostgresEngineSpec"),
        ("redshift", "RedshiftEngineSpec"),
        ("mysql", "MySQLEngineSpec"),
        ("mssql", "MssqlEngineSpec"),
        ("clickhouse", "ClickHouseEngineSpec"),
        ("trino", "TrinoEngineSpec"),
        ("presto", "PrestoEngineSpec"),
        ("hive", "HiveEngineSpec"),
        ("bigquery", "BigQueryEngineSpec"),
        ("snowflake", "SnowflakeEngineSpec"),
        ("starrocks", "StarRocksEngineSpec"),
        ("sqlite", "SqliteEngineSpec"),
    ],
)
def test_supported_engines_declare_a_template(
    engine_module: str, engine_class: str
) -> None:
    module = __import__(
        f"superset.db_engine_specs.{engine_module}", fromlist=[engine_class]
    )
    spec = getattr(module, engine_class)
    template = spec.get_utc_to_tz_expression(TZ)
    assert template is not None
    assert "{col}" in template
    # no placeholder must survive substitution
    assert "{tz}" not in template
    assert "{offset}" not in template
    assert "{offset_minutes}" not in template
