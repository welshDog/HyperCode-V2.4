"""Add mod_actions audit table (Server Guardian Phase 3)

Revision ID: 015
Revises: 014
Create Date: 2026-05-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mod_actions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("action_type", sa.String(length=16), nullable=False),
        sa.Column("target_discord_id", sa.String(length=32), nullable=False),
        sa.Column("target_username", sa.String(length=128), nullable=True),
        sa.Column("severity", sa.String(length=8), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="auto_done"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("executes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_mod_actions_created_at",
        "mod_actions",
        [sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_mod_actions_status", "mod_actions", ["status"], unique=False)
    op.create_index(
        "ix_mod_actions_target_discord_id",
        "mod_actions",
        ["target_discord_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mod_actions_target_discord_id", table_name="mod_actions")
    op.drop_index("ix_mod_actions_status", table_name="mod_actions")
    op.drop_index("ix_mod_actions_created_at", table_name="mod_actions")
    op.drop_table("mod_actions")
