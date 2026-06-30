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
"""Response-size guard for content sent back into the LLM context.

Large tool results (e.g. wide query outputs) would inflate token cost and can
exceed the model's context window, so they are truncated before being fed back.
The full result is still returned to the UI separately.
"""

from __future__ import annotations

# Rough chars-per-token ratio used to convert a token budget to a char budget.
_CHARS_PER_TOKEN = 4


def truncate_for_llm(text: str, max_tokens: int) -> str:
    """Truncate ``text`` to roughly ``max_tokens`` tokens, with a notice."""
    if max_tokens <= 0:
        return text
    max_chars = max_tokens * _CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"{text[:max_chars]}\n…[truncated {omitted} characters to fit context]"
