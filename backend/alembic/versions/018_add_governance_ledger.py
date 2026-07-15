"""Add governance_ledger table (audit trail for high-impact actions — P1-2)

Revision ID: 018
Revises: 017
Create Date: 2026-06-19

NOTE: AGENT-START suggested "016_governance_ledger" assuming head was 015, but
the live head was 017 (016=hyperflow_runs, 017=broski_identity_agents). This is
018. gen_random_uuid() is available via pgcrypto (enabled in migration 009).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "governance_ledger",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("tool_used", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("decision", sa.Text(), nullable=True),  # ALLOW | BLOCK | ESCALATE | AUTO
        sa.Column("agent_name", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Text(), nullable=True),  # 'auto' or discord user id
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_governance_ledger_user_id", "governance_ledger", ["user_id"], unique=False)
    op.create_index(
        "ix_governance_ledger_timestamp", "governance_ledger", [sa.text("timestamp DESC")], unique=False
    )
    op.create_index("ix_governance_ledger_action", "governance_ledger", ["action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_governance_ledger_action", table_name="governance_ledger")
    op.drop_index("ix_governance_ledger_timestamp", table_name="governance_ledger")
    op.drop_index("ix_governance_ledger_user_id", table_name="governance_ledger")
    op.drop_table("governance_ledger")
