"""Add focus_sessions table (Layer 3.5 focus → NemoClaw delta → BROski$)

Revision ID: 013
Revises: 012
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "focus_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("discord_id", sa.String(length=32), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("baseline_ready", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("baseline_score", sa.Integer(), nullable=True),
        sa.Column("baseline_grade", sa.String(length=4), nullable=True),
        sa.Column("baseline_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("baseline_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_score", sa.Integer(), nullable=True),
        sa.Column("end_grade", sa.String(length=4), nullable=True),
        sa.Column("end_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("end_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delta_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("delta_score", sa.Integer(), nullable=True),
        sa.Column("delta_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("coins_awarded", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_index(
        "ix_focus_sessions_discord_id",
        "focus_sessions",
        ["discord_id"],
        unique=False,
    )
    op.create_index(
        "ix_focus_sessions_user_id",
        "focus_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_focus_sessions_started_at",
        "focus_sessions",
        [sa.text("started_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_focus_sessions_ended_at",
        "focus_sessions",
        [sa.text("ended_at DESC")],
        unique=False,
    )
    op.create_index(
        "ux_focus_sessions_active_per_discord",
        "focus_sessions",
        ["discord_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_focus_sessions_active_per_discord", table_name="focus_sessions")
    op.drop_index("ix_focus_sessions_ended_at", table_name="focus_sessions")
    op.drop_index("ix_focus_sessions_started_at", table_name="focus_sessions")
    op.drop_index("ix_focus_sessions_user_id", table_name="focus_sessions")
    op.drop_index("ix_focus_sessions_discord_id", table_name="focus_sessions")
    op.drop_table("focus_sessions")

