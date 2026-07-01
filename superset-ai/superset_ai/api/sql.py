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
"""SQL assistant endpoints: generate / explain / fix."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from superset_ai import orchestrator
from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.config import get_settings
from superset_ai.deps import AuthDep, ClientDep, LlmDep
from superset_ai.llm.base import LlmClient
from superset_ai.llm.errors import classify_llm_error
from superset_ai.sql.guard import UnsafeSqlError
from superset_ai.superset_client import SupersetClient


def _llm_http_error(err: Exception) -> HTTPException:
    status_code, message = classify_llm_error(err)
    return HTTPException(status_code=status_code, detail=message)


router = APIRouter(prefix="/sql", tags=["sql"])


class GenerateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    dataset_id: int | None = None
    dialect: str | None = None


class ExplainRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    dialect: str | None = None


class FixRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    error: str = Field(..., min_length=1)
    dialect: str | None = None


@router.post("/generate")
async def generate(
    body: GenerateRequest,
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
    llm: LlmClient = LlmDep,
) -> dict[str, str]:
    """Generate a validated, read-only SELECT from a question."""
    try:
        sql = await orchestrator.generate_sql(
            llm,
            client,
            auth,
            get_settings(),
            question=body.question,
            dataset_id=body.dataset_id,
            dialect=body.dialect,
        )
    except UnsafeSqlError as err:
        raise HTTPException(
            status_code=422, detail=f"Model did not return safe SQL: {err}"
        ) from err
    except Exception as err:  # noqa: BLE001 - map provider errors to clean HTTP
        raise _llm_http_error(err) from err
    return {"sql": sql}


@router.post("/explain")
async def explain(
    body: ExplainRequest,
    llm: LlmClient = LlmDep,
) -> dict[str, str]:
    """Explain a SQL query in natural language."""
    try:
        explanation = await orchestrator.explain_sql(
            llm, get_settings(), sql=body.sql, dialect=body.dialect
        )
    except Exception as err:  # noqa: BLE001 - map provider errors to clean HTTP
        raise _llm_http_error(err) from err
    return {"explanation": explanation}


@router.post("/fix")
async def fix(
    body: FixRequest,
    llm: LlmClient = LlmDep,
) -> dict[str, str]:
    """Fix a failing query, keeping it a read-only SELECT."""
    try:
        fixed = await orchestrator.fix_sql(
            llm,
            get_settings(),
            sql=body.sql,
            error=body.error,
            dialect=body.dialect,
        )
    except UnsafeSqlError as err:
        raise HTTPException(
            status_code=422, detail=f"Model did not return safe SQL: {err}"
        ) from err
    except Exception as err:  # noqa: BLE001 - map provider errors to clean HTTP
        raise _llm_http_error(err) from err
    return {"sql": fixed}
