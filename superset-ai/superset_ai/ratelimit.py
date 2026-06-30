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
"""A small in-memory sliding-window rate limiter (per caller).

Protects Superset from being overwhelmed by AI-driven traffic. For multi-worker
deployments, back this with Redis; the call sites only use :meth:`allow`.
"""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """Sliding 60s window allowing ``max_per_minute`` calls per key."""

    def __init__(self, max_per_minute: int, window_seconds: float = 60.0) -> None:
        self._max = max_per_minute
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """Record a call for ``key``; return False if the window is full."""
        if self._max <= 0:
            return True
        now = time.monotonic()
        cutoff = now - self._window
        recent = [ts for ts in self._hits[key] if ts > cutoff]
        if len(recent) >= self._max:
            self._hits[key] = recent
            return False
        recent.append(now)
        self._hits[key] = recent
        return True
