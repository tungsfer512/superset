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
"""Tests for Phase-3 smart modules (no network)."""

import asyncio
import json

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.smart.grounding import GroundingService
from superset_ai.smart.retriever import Retriever
from superset_ai.smart.schema_indexer import SchemaIndexer
from superset_ai.smart.semantic_layer import Glossary, GlossaryEntry
from tests.fakes import FakeSupersetClient

AUTH = SupersetAuth(authorization="Bearer t")


def test_retriever_ranks_relevant_doc_first():
    r = Retriever()
    r.index(
        [
            ("1", "orders sales revenue", {"id": 1, "name": "orders"}),
            ("2", "customers profile address", {"id": 2, "name": "customers"}),
        ]
    )
    hits = r.search("how many orders", k=1)
    assert hits
    assert hits[0]["name"] == "orders"


def test_retriever_returns_empty_on_no_overlap():
    r = Retriever()
    r.index([("1", "orders", {"id": 1})])
    assert r.search("zzz", k=3) == []


def test_glossary_load_and_expand(tmp_path):
    path = tmp_path / "glossary.json"
    path.write_text(
        json.dumps(
            [
                {"term": "doanh thu", "table": "orders", "column": "amount"},
                {"term": "khách hàng", "table": "customers"},
            ]
        ),
        encoding="utf-8",
    )
    glossary = Glossary.load(str(path))
    hits = glossary.expand("Tính doanh thu theo tháng")
    assert len(hits) == 1
    assert hits[0].table == "orders"
    assert glossary.referenced_tables(hits) == {"orders"}


def test_glossary_missing_file_is_empty():
    assert Glossary.load(None).entries == []
    assert Glossary.load("/no/such/file.json").entries == []


def test_schema_indexer_caches_schema():
    indexer = SchemaIndexer(cache_ttl=300)
    client = FakeSupersetClient()
    first = asyncio.run(indexer.get_schema(client, AUTH, 1))
    second = asyncio.run(indexer.get_schema(client, AUTH, 1))
    assert first is second  # second call served from cache (same object)


def test_infer_relations():
    schemas = [
        {"table_name": "orders", "columns": [{"name": "customer_id"}]},
        {"table_name": "customers", "columns": [{"name": "id"}]},
    ]
    relations = SchemaIndexer.infer_relations(schemas)
    assert {
        "from_table": "orders",
        "from_column": "customer_id",
        "to_table": "customers",
    } in relations


def test_grounding_builds_context_with_schema_and_glossary():
    glossary = Glossary(
        entries=[GlossaryEntry(term="đơn hàng", table="orders", column="id")]
    )
    grounding = GroundingService(SchemaIndexer(), glossary, top_k=5)
    context = asyncio.run(
        grounding.context_for(
            FakeSupersetClient(), AUTH, "Thống kê đơn hàng theo orders"
        )
    )
    assert "orders" in context
    assert "đơn hàng" in context  # glossary term surfaced
