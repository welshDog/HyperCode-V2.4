"""add access_provisions — Phase 3 Agent Access + Shop Bridge

Revision ID: 005_add_access_provisions
Revises: 004_add_course_sync_events
Create Date: 2026-04-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "005_add_access_provisions"
down_revision = "004_add_course_sync_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "access_provisions" not in inspector.get_table_names():
        op.create_table(
            "access_provisions",
            sa.Column("id",                   sa.Integer(),                              nullable=False),
            sa.Column("user_id",              sa.Integer(),                              nullable=True),
            sa.Column("discord_id",           sa.String(32),                             nullable=True),
            sa.Column("api_key",              sa.Text(),                                 nullable=False),
            sa.Column("provision_type",       sa.String(64),  server_default="agent_sandbox", nullable=False),
            sa.Column("source_id",            sa.Text(),                                 nullable=True),
            sa.Column("mission_control_url",  sa.Text(),                                 nullable=True),
            sa.Column("is_active",            sa.Boolean(),   server_default="true",     nullable=False),
            sa.Column("created_at",           sa.DateTime(timezone=True),
                      server_default=sa.func.now(),                                      nullable=True),
            sa.Column("expires_at",           sa.DateTime(timezone=True),                nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_access_provisions_user_id"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("api_key",    name="uq_access_provisions_api_key"),
            sa.UniqueConstraint("source_id",  name="uq_access_provisions_source_id"),
        )
        op.create_index("ix_access_provisions_id",         "access_provisions", ["id"],         unique=False)
        op.create_index("ix_access_provisions_discord_id", "access_provisions", ["discord_id"], unique=False)
        op.create_index("ix_access_provisions_user_id",    "access_provisions", ["user_id"],    unique=False)


def downgrade() -> None:
    op.drop_index("ix_access_provisions_user_id",    table_name="access_provisions")
    op.drop_index("ix_access_provisions_discord_id", table_name="access_provisions")
    op.drop_index("ix_access_provisions_id",         table_name="access_provisions")
    op.drop_table("access_provisions")
