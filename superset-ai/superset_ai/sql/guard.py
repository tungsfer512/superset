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
"""Defense-in-depth guard ensuring the AI can only run read-only SQL.

Two layers, mirroring the safety posture of community Superset MCP servers:

1. A keyword denylist as a fast, dialect-agnostic first pass.
2. AST parsing via :mod:`sqlglot` — exactly one statement, and its top-level
   node must be a read expression (SELECT / set operation). Anything that fails
   to parse is rejected (fail closed).

Use :func:`assert_select_only` before sending SQL to Superset, and
:func:`enforce_limit` to cap the row count.
"""

from __future__ import annotations

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

# Statements that read but are not a bare SELECT (UNION/INTERSECT/EXCEPT).
_READ_EXPRESSIONS: tuple[type[exp.Expression], ...] = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
)

# Mutating / DDL keywords blocked outright (word-boundary, case-insensitive).
_DENY_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "REPLACE",
    "CALL",
    "EXEC",
    "EXECUTE",
    "ATTACH",
    "COPY",
)
_DENY_PATTERN = re.compile(
    r"\b(" + "|".join(_DENY_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


class UnsafeSqlError(ValueError):
    """Raised when SQL is not a single read-only statement."""


def assert_select_only(sql: str, dialect: str | None = None) -> exp.Expression:
    """Validate that ``sql`` is exactly one read-only statement.

    Returns the parsed top-level expression on success; raises
    :class:`UnsafeSqlError` otherwise.
    """
    if not sql or not sql.strip():
        raise UnsafeSqlError("Empty SQL statement.")

    if _DENY_PATTERN.search(sql):
        raise UnsafeSqlError("Only read-only SELECT queries are allowed.")

    try:
        statements = [s for s in sqlglot.parse(sql, dialect=dialect) if s is not None]
    except SqlglotError as err:
        raise UnsafeSqlError(f"Could not parse SQL: {err}") from err

    if not statements:
        raise UnsafeSqlError("Empty SQL statement.")
    if len(statements) > 1:
        raise UnsafeSqlError("Multiple SQL statements are not allowed.")

    statement = statements[0]
    if not isinstance(statement, _READ_EXPRESSIONS):
        raise UnsafeSqlError(
            f"Only SELECT queries are allowed, got {type(statement).__name__.upper()}."
        )
    return statement


def enforce_limit(sql: str, limit: int, dialect: str | None = None) -> str:
    """Return ``sql`` with a row ``limit`` applied if it has none.

    Only plain ``SELECT`` statements are rewritten; set operations are returned
    unchanged (the caller still applies a hard cap server-side).
    """
    statement = sqlglot.parse_one(sql, dialect=dialect)
    if isinstance(statement, exp.Select) and statement.args.get("limit") is None:
        statement = statement.limit(limit)
    return statement.sql(dialect=dialect)
