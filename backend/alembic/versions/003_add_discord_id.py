"""add discord_id to users — Phase 1 Identity Bridge

Revision ID: 003_add_discord_id
Revises: 002_dashboard_tasks
Create Date: 2026-04-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "003_add_discord_id"
down_revision = "002_dashboard_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = [c["name"] for c in inspector.get_columns("users")]
    if "discord_id" not in cols:
        op.add_column(
            "users",
            sa.Column("discord_id", sa.String(32), nullable=True, unique=True),
        )
        op.create_index("ix_users_discord_id", "users", ["discord_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_discord_id", table_name="users")
    op.drop_column("users", "discord_id")
