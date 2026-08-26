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
"""add display_time_zone to user_attribute

Revision ID: b7e1c9a4d302
Revises: a1b2c3d4e5f6
Create Date: 2026-08-24 00:00:00.000000
"""

import sqlalchemy as sa

from superset.migrations.shared.utils import add_columns, drop_columns

# revision identifiers, used by Alembic.
revision = "b7e1c9a4d302"
down_revision = "a1b2c3d4e5f6"


def upgrade():
    add_columns(
        "user_attribute",
        sa.Column("display_time_zone", sa.String(length=64), nullable=True),
    )


def downgrade():
    drop_columns("user_attribute", "display_time_zone")
