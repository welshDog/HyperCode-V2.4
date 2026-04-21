"""010_add_access_provisions_event_id

Revision ID: 010
Revises: 009
Create Date: 2026-04-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _col_exists(inspector, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspector.get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "access_provisions" not in inspector.get_table_names():
        return

    if not _col_exists(inspector, "access_provisions", "event_id"):
        op.add_column("access_provisions", sa.Column("event_id", sa.Text(), nullable=True))

    existing = {c["name"] for c in inspector.get_unique_constraints("access_provisions")}
    if "uq_access_provisions_event_id" not in existing:
        op.create_unique_constraint(
            "uq_access_provisions_event_id",
            "access_provisions",
            ["event_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "access_provisions" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_unique_constraints("access_provisions")}
    if "uq_access_provisions_event_id" in existing:
        op.drop_constraint("uq_access_provisions_event_id", "access_provisions", type_="unique")

    if _col_exists(inspector, "access_provisions", "event_id"):
        op.drop_column("access_provisions", "event_id")
