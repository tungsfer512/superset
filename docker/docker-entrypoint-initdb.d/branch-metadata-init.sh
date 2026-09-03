#!/usr/bin/env bash

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

# ------------------------------------------------------------------------
# Creates this branch's metadata database when it is not the one Postgres
# bootstrapped the volume with.
#
# The `main` and `embedded` branches have diverging alembic chains, so they
# each need their own metadata database (see DATABASE_DB in docker/.env).
# Postgres only creates POSTGRES_DB on first init, so the other one has to be
# created here -- otherwise a fresh volume leaves the branch without a database
# to migrate into.
# ------------------------------------------------------------------------
set -e

if [ -z "${DATABASE_DB}" ] || [ "${DATABASE_DB}" = "${POSTGRES_DB}" ]; then
  exit 0
fi

psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" <<-EOSQL
  CREATE DATABASE ${DATABASE_DB} OWNER ${POSTGRES_USER};
EOSQL
