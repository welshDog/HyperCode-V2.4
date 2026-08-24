"""Add impact column to mission_proposals (Fleet Dependency Graph, Phase 2)

Revision ID: 022
Revises: 021
Create Date: 2026-08-24

Purely advisory data -- see
docs/superpowers/specs/2026-08-24-fleet-dependency-graph-design.md. Same
nullable-JSONB pattern as plan/plan_response (020).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mission_proposals",
        sa.Column("impact", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mission_proposals", "impact")
