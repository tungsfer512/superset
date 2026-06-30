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
"""Shared pytest fixtures.

Tests must be deterministic regardless of a developer's local ``.env`` or
``SUPERSET_AI_*`` environment, so this autouse fixture strips that state and
clears the cached settings around every test.
"""

import os

import pytest

from superset_ai.config import get_settings


@pytest.fixture(autouse=True)
def _hermetic_settings(monkeypatch, tmp_path):
    for key in list(os.environ):
        if key.startswith("SUPERSET_AI_"):
            monkeypatch.delenv(key, raising=False)
    # Settings resolves ``.env`` relative to the cwd; move away from it.
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
