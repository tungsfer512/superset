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
"""Business glossary mapping natural-language terms to schema objects.

Maps domain terms (often Vietnamese, e.g. "doanh thu") to a concrete table
and/or column so the assistant can ground a question that never mentions the
real column names. Loaded from a JSON file (a list of entries).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GlossaryEntry:
    """A single term -> schema-object mapping."""

    term: str
    table: str | None = None
    column: str | None = None
    description: str = ""


@dataclass
class Glossary:
    """Case-insensitive substring lookup of glossary terms in a question."""

    entries: list[GlossaryEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | None) -> Glossary:
        """Load entries from a JSON file; return an empty glossary if absent."""
        if not path:
            return cls()
        file = Path(path)
        if not file.is_file():
            return cls()
        raw = json.loads(file.read_text(encoding="utf-8"))
        entries = [
            GlossaryEntry(
                term=item["term"],
                table=item.get("table"),
                column=item.get("column"),
                description=item.get("description", ""),
            )
            for item in raw
        ]
        return cls(entries=entries)

    def expand(self, question: str) -> list[GlossaryEntry]:
        """Return entries whose term appears (case-insensitive) in the question."""
        lowered = question.lower()
        return [e for e in self.entries if e.term.lower() in lowered]

    def referenced_tables(self, entries: list[GlossaryEntry]) -> set[str]:
        """Return the set of table names referenced by the given entries."""
        return {e.table for e in entries if e.table}
