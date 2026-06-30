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
"""A small dependency-free lexical retriever (TF-IDF scoring).

Used to pick the datasets most relevant to a question for grounding, without a
vector database or remote embedding calls. The token regex is Unicode-aware so
Vietnamese words are indexed too. Can be swapped for an embedding-based store
later behind the same ``index``/``search`` surface.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase Unicode word tokenizer."""
    return _TOKEN_RE.findall(text.lower())


@dataclass
class _Doc:
    doc_id: str
    tf: Counter[str]
    length: int
    payload: dict[str, Any]


@dataclass
class Retriever:
    """In-memory TF-IDF retriever rebuilt per query set."""

    _docs: list[_Doc] = field(default_factory=list)
    _df: Counter[str] = field(default_factory=Counter)

    def index(self, documents: list[tuple[str, str, dict[str, Any]]]) -> None:
        """Index ``(doc_id, text, payload)`` tuples, replacing any prior set."""
        self._docs = []
        self._df = Counter()
        for doc_id, text, payload in documents:
            tokens = tokenize(text)
            tf: Counter[str] = Counter(tokens)
            self._docs.append(_Doc(doc_id, tf, len(tokens), payload))
            self._df.update(tf.keys())

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Return up to ``k`` payloads ranked by TF-IDF overlap with ``query``."""
        query_tokens = tokenize(query)
        total = len(self._docs) or 1
        scored: list[tuple[float, dict[str, Any]]] = []
        for doc in self._docs:
            score = 0.0
            for token in query_tokens:
                term_freq = doc.tf.get(token, 0)
                if not term_freq:
                    continue
                idf = math.log(1 + total / (1 + self._df.get(token, 0)))
                score += idf * (term_freq / (doc.length or 1))
            if score > 0:
                scored.append((score, doc.payload))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [payload for _, payload in scored[:k]]
