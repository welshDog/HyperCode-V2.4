"""Add pet_provision_events table

Revision ID: 011
Revises: 010
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pet_provision_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("discord_id", sa.String(length=32), nullable=False),
        sa.Column("pet_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source_id", name="uq_pet_provision_source_id"),
    )
    op.create_index(op.f("ix_pet_provision_events_id"), "pet_provision_events", ["id"], unique=False)
    op.create_index(op.f("ix_pet_provision_events_source_id"), "pet_provision_events", ["source_id"], unique=False)
    op.create_index(op.f("ix_pet_provision_events_discord_id"), "pet_provision_events", ["discord_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pet_provision_events_discord_id"), table_name="pet_provision_events")
    op.drop_index(op.f("ix_pet_provision_events_source_id"), table_name="pet_provision_events")
    op.drop_index(op.f("ix_pet_provision_events_id"), table_name="pet_provision_events")
    op.drop_table("pet_provision_events")
