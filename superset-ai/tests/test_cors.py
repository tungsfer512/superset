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
"""CORS origin resolution for the sidecar."""

from superset_ai.config import Settings
from superset_ai.main import _cors_origins


def test_wildcard_allows_all_origins_with_credentials():
    origins, regex = _cors_origins(Settings(extra_cors_origins="*"))
    # A regex (not a literal "*") so it works alongside allow_credentials=True.
    assert origins == []
    assert regex == ".*"


def test_wildcard_wins_even_mixed_with_explicit_origins():
    origins, regex = _cors_origins(Settings(extra_cors_origins="https://a.com, *"))
    assert origins == []
    assert regex == ".*"


def test_explicit_origins_include_superset_base_url():
    settings = Settings(
        superset_base_url="http://superset:8088",
        extra_cors_origins="https://a.com, https://b.com",
    )
    origins, regex = _cors_origins(settings)
    assert regex is None
    assert origins == [
        "http://superset:8088",
        "https://a.com",
        "https://b.com",
    ]
