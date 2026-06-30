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
"""Schema indexer: discover datasets and cache their column schemas.

Dataset *visibility* is fetched fresh per call (it runs as the user, so RBAC is
respected), while per-dataset column schemas — which are not user-specific — are
cached with a TTL to avoid repeated round trips. Also infers simple foreign-key
style relationships from ``<table>_id`` column names.
"""

from __future__ import annotations

import time
from typing import Any

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.superset_client import SupersetClient
from superset_ai.tools import data_tools


class SchemaIndexer:
    """Caches dataset schemas and builds a lightweight architecture map."""

    def __init__(self, cache_ttl: int = 300) -> None:
        self._cache_ttl = cache_ttl
        self._schema_cache: dict[int, tuple[float, dict[str, Any]]] = {}

    async def list_visible(
        self,
        client: SupersetClient,
        auth: SupersetAuth,
        *,
        search: str | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """List datasets the caller can see (not cached: respects RBAC/RLS)."""
        payload = await data_tools.list_datasets(
            client, auth, search=search, page_size=page_size
        )
        return payload.get("datasets", [])

    async def get_schema(
        self, client: SupersetClient, auth: SupersetAuth, dataset_id: int
    ) -> dict[str, Any]:
        """Return a dataset's schema, using the TTL cache when fresh."""
        cached = self._schema_cache.get(dataset_id)
        now = time.monotonic()
        if cached and (now - cached[0]) < self._cache_ttl:
            return cached[1]
        schema = await data_tools.get_dataset_schema(client, auth, dataset_id)
        self._schema_cache[dataset_id] = (now, schema)
        return schema

    @staticmethod
    def infer_relations(schemas: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Infer ``table.col -> other_table`` links from ``<name>_id`` columns."""
        names = {
            (s.get("table_name") or "").lower(): s.get("table_name") for s in schemas
        }
        relations: list[dict[str, str]] = []
        for schema in schemas:
            table = schema.get("table_name")
            for column in schema.get("columns", []):
                col = (column.get("name") or "").lower()
                if not col.endswith("_id"):
                    continue
                target = col[:-3]
                # match singular/plural-ish forms
                for candidate in (target, f"{target}s", target.rstrip("s")):
                    if candidate in names and names[candidate] != table:
                        relations.append(
                            {
                                "from_table": str(table),
                                "from_column": str(column.get("name")),
                                "to_table": str(names[candidate]),
                            }
                        )
                        break
        return relations

    def invalidate(self) -> None:
        """Clear the schema cache (e.g. after a known schema change)."""
        self._schema_cache.clear()
