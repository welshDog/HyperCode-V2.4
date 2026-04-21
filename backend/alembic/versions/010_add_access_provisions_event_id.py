"""Add event_id column + unique constraint to access_provisions (M3.2)

Revision ID: 010
Revises: 009
Create Date: 2026-04-21

Adds a nullable Text `event_id` column to `access_provisions` with a
UNIQUE constraint. This UUID is generated at provision time and returned
in the ProvisionResponse so the Course side can store it in
shop_purchases.fulfillment_metadata for cross-system traceability.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add event_id column (nullable — existing rows keep NULL)
    op.add_column(
        "access_provisions",
        sa.Column("event_id", sa.Text(), nullable=True),
    )
    # Unique constraint — prevents duplicate provision_event_id across rows
    op.create_unique_constraint(
        "uq_access_provisions_event_id",
        "access_provisions",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_access_provisions_event_id",
        "access_provisions",
        type_="unique",
    )
    op.drop_column("access_provisions", "event_id")
