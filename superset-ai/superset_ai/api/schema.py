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
"""Schema/grounding inspection endpoints (useful for debugging Phase-3)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from superset_ai.auth.passthrough import SupersetAuth
from superset_ai.deps import AuthDep, ClientDep, GroundingDep
from superset_ai.smart.grounding import GroundingService
from superset_ai.superset_client import SupersetClient

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/grounding")
async def grounding_context(
    question: str,
    client: SupersetClient = ClientDep,
    auth: SupersetAuth = AuthDep,
    grounding: GroundingService | None = GroundingDep,
) -> dict[str, str]:
    """Return the grounding context the assistant would use for a question."""
    if grounding is None:
        raise HTTPException(status_code=404, detail="Grounding is disabled.")
    context = await grounding.context_for(client, auth, question)
    return {"question": question, "context": context}
