"""Add code_health_scans table for nemoclaw-agent

Revision ID: 012
Revises: 011
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "code_health_scans",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(length=2), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medium_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_issues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("scan_id", name="uq_code_health_scans_scan_id"),
    )
    op.create_index(
        "ix_code_health_scans_scanned_at",
        "code_health_scans",
        [sa.text("scanned_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_code_health_scans_grade",
        "code_health_scans",
        ["grade"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_code_health_scans_grade", table_name="code_health_scans")
    op.drop_index("ix_code_health_scans_scanned_at", table_name="code_health_scans")
    op.drop_table("code_health_scans")
