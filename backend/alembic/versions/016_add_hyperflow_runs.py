"""Add hyperflow_runs table (HyperFlow P0-1 — mission graph runs)

Revision ID: 016
Revises: 015
Create Date: 2026-06-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hyperflow_runs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("flow_name", sa.String(length=128), nullable=False),
        sa.Column("flow_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="running"),
        sa.Column("current_node", sa.String(length=128), nullable=True),
        sa.Column(
            "state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hyperflow_runs_flow_name", "hyperflow_runs", ["flow_name"], unique=False)
    op.create_index("ix_hyperflow_runs_status", "hyperflow_runs", ["status"], unique=False)
    op.create_index(
        "ix_hyperflow_runs_created_at",
        "hyperflow_runs",
        [sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_hyperflow_runs_created_at", table_name="hyperflow_runs")
    op.drop_index("ix_hyperflow_runs_status", table_name="hyperflow_runs")
    op.drop_index("ix_hyperflow_runs_flow_name", table_name="hyperflow_runs")
    op.drop_table("hyperflow_runs")
