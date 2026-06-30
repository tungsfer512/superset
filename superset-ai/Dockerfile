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

# Same base image as Apache Superset (Dockerfile ARG PY_VER) to keep the
# sidecar runtime environment as close to Superset as possible.
ARG PY_VER=3.11.13-slim-bookworm
FROM python:${PY_VER}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install -r requirements/base.txt

COPY pyproject.toml README.md ./
COPY superset_ai/ superset_ai/
RUN pip install --no-deps -e .

EXPOSE 8800

# Honors SUPERSET_AI_* env vars (see superset_ai/config.py).
CMD ["uvicorn", "superset_ai.main:app", "--host", "0.0.0.0", "--port", "8800"]
