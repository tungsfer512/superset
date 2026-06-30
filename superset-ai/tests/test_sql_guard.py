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
"""Tests for the SELECT-only SQL guard."""

import pytest

from superset_ai.sql.guard import UnsafeSqlError, assert_select_only, enforce_limit

ALLOWED = [
    "SELECT 1",
    "SELECT * FROM orders WHERE amount > 10",
    "WITH t AS (SELECT 1 AS n) SELECT n FROM t",
    "SELECT a FROM x UNION SELECT b FROM y",
]

BLOCKED = [
    "DROP TABLE orders",
    "DELETE FROM orders",
    "INSERT INTO orders (id) VALUES (1)",
    "UPDATE orders SET amount = 0",
    "TRUNCATE TABLE orders",
    "ALTER TABLE orders ADD COLUMN x INT",
    "GRANT SELECT ON orders TO bob",
    "SELECT 1; DROP TABLE orders",
    "",
    "   ",
    "not even sql ;;;",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allows_read_only(sql):
    assert assert_select_only(sql) is not None


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocks_non_select(sql):
    with pytest.raises(UnsafeSqlError):
        assert_select_only(sql)


def test_enforce_limit_appends_when_missing():
    out = enforce_limit("SELECT * FROM orders", 500)
    assert "LIMIT" in out.upper()
    assert "500" in out


def test_enforce_limit_keeps_existing():
    out = enforce_limit("SELECT * FROM orders LIMIT 5", 500)
    assert "5" in out
    assert "500" not in out
