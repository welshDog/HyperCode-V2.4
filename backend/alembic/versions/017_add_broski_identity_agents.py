"""Add broski_identity_agents table (BROski Identity Agent per user — P1-1)

Revision ID: 017
Revises: 016
Create Date: 2026-06-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broski_identity_agents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("discord_id", sa.String(length=32), nullable=True),
        sa.Column(
            "state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_broski_identity_agents_user_id"),
    )
    op.create_index(
        "ix_broski_identity_agents_user_id", "broski_identity_agents", ["user_id"], unique=False
    )
    op.create_index(
        "ix_broski_identity_agents_discord_id", "broski_identity_agents", ["discord_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_broski_identity_agents_discord_id", table_name="broski_identity_agents")
    op.drop_index("ix_broski_identity_agents_user_id", table_name="broski_identity_agents")
    op.drop_table("broski_identity_agents")
