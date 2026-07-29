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
"""add translation_dictionary

Revision ID: a1b2c3d4e5f6
Revises: c233f5365c9e
Create Date: 2026-07-27 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "c233f5365c9e"


def upgrade():
    bind = op.get_bind()
    if "translation_dictionary" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "translation_dictionary",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("msgcontext", sa.String(length=255), nullable=True),
        sa.Column("msgid", sa.Text(), nullable=False),
        sa.Column("msgid_hash", sa.String(length=64), nullable=False),
        sa.Column("msgstr", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("updated_on", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "locale",
            "msgcontext",
            "msgid_hash",
            name="uq_translation_locale_ctx_hash",
        ),
    )
    op.create_index(
        "ix_translation_dictionary_locale",
        "translation_dictionary",
        ["locale"],
        unique=False,
    )


def downgrade():
    bind = op.get_bind()
    if "translation_dictionary" not in sa.inspect(bind).get_table_names():
        return
    op.drop_index(
        "ix_translation_dictionary_locale",
        table_name="translation_dictionary",
    )
    op.drop_table("translation_dictionary")
