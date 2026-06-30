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
"""Grounding service: assemble relevant schema + glossary context for a question.

For a given question it (1) lists the datasets the user can see, (2) ranks them
with the lexical retriever, (3) adds any datasets referenced by matching
glossary terms, (4) fetches those schemas, and (5) renders a compact context
block to prepend to the question — improving Text-to-SQL accuracy and reducing
tool round trips.
"""

from __future__ import annotations

from typing import Any

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.smart.retriever import Retriever
from superset_ai.smart.schema_indexer import SchemaIndexer
from superset_ai.smart.semantic_layer import Glossary
from superset_ai.superset_client import SupersetClient


class GroundingService:
    """Build a schema/glossary context block for a question."""

    def __init__(
        self,
        indexer: SchemaIndexer,
        glossary: Glossary,
        top_k: int = 5,
    ) -> None:
        self._indexer = indexer
        self._glossary = glossary
        self._top_k = top_k

    async def context_for(
        self, client: SupersetClient, auth: SupersetAuth, question: str
    ) -> str:
        """Return a context string (may be empty) grounding the question."""
        datasets = await self._indexer.list_visible(client, auth)
        if not datasets:
            return ""

        # Rank datasets by lexical relevance to the question.
        retriever = Retriever()
        retriever.index(
            [
                (
                    str(ds.get("id")),
                    f"{ds.get('name', '')} {ds.get('schema', '')} "
                    f"{ds.get('database', '')}",
                    ds,
                )
                for ds in datasets
                if ds.get("id") is not None
            ]
        )
        selected = retriever.search(question, k=self._top_k)

        # Add datasets referenced by matching glossary terms.
        glossary_hits = self._glossary.expand(question)
        wanted_tables = self._glossary.referenced_tables(glossary_hits)
        by_id = {ds["id"]: ds for ds in selected}
        for ds in datasets:
            if ds.get("name") in wanted_tables:
                by_id[ds["id"]] = ds

        if not by_id and not glossary_hits:
            return ""

        schemas = [
            await self._indexer.get_schema(client, auth, int(dataset_id))
            for dataset_id in list(by_id)[: self._top_k]
        ]
        return self._render(schemas, glossary_hits)

    @staticmethod
    def _render(schemas: list[dict[str, Any]], glossary_hits: list[Any]) -> str:
        lines: list[str] = []
        if schemas:
            lines.append("Bối cảnh dữ liệu liên quan (do hệ thống gợi ý):")
            for schema in schemas:
                cols = ", ".join(
                    f"{c.get('name')} ({c.get('type')})"
                    for c in schema.get("columns", [])
                )
                lines.append(
                    f"- Dataset {schema.get('table_name')} "
                    f"(dataset_id={schema.get('dataset_id')}, "
                    f"database_id={schema.get('database_id')}): {cols}"
                )
            relations = SchemaIndexer.infer_relations(schemas)
            if relations:
                lines.append("Quan hệ suy luận:")
                for rel in relations:
                    lines.append(
                        f"- {rel['from_table']}.{rel['from_column']} "
                        f"-> {rel['to_table']}"
                    )
        if glossary_hits:
            lines.append("Thuật ngữ nghiệp vụ:")
            for hit in glossary_hits:
                target = hit.table or ""
                if hit.column:
                    target = f"{target}.{hit.column}" if target else hit.column
                lines.append(f'- "{hit.term}" -> {target} {hit.description}'.rstrip())
        return "\n".join(lines)
