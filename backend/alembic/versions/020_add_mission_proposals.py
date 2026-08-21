"""Add mission_proposals table (Mission Director Phase 1)

Revision ID: 020
Revises: 019
Create Date: 2026-08-21

Backend-owned point-lookup store for mission-director's propose/review
flow -- NOT the audit trail (that's governance_ledger, untouched here).
See docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §6.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mission_proposals",
        sa.Column("mission_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("truth_snapshot_ref", sa.Text(), nullable=True),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plan_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("superseded_from", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_mission_proposals_status", "mission_proposals", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_mission_proposals_status", table_name="mission_proposals")
    op.drop_table("mission_proposals")
