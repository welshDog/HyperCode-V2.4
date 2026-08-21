"""Add mission_evaluations table (Mission Evaluator v1)

Revision ID: 021
Revises: 020
Create Date: 2026-08-21

Read-only observer over mission_proposals -- one row per evaluated
mission, never updated after insert. NOT the audit trail (that's
governance_ledger, untouched here); NOT mission_proposals' own
current-state store either. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §1.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mission_evaluations",
        sa.Column("mission_id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_mission_evaluations_verdict", "mission_evaluations", ["verdict"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_mission_evaluations_verdict", table_name="mission_evaluations")
    op.drop_table("mission_evaluations")
