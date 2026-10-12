"""Add quest_settlements — HyperCrew Quest Settler idempotency + daily-cap ledger

Revision ID: 023
Revises: 022
Create Date: 2026-10-02

``source_id`` (run_id:quest_id) is UNIQUE: the database, not the app, guarantees a run is settled once.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "quest_settlements" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "quest_settlements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("quest_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(255), nullable=False, server_default=""),
        sa.Column("bundle_hash", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", name="uq_quest_settlement_source_id"),
    )
    op.create_index("ix_quest_settlements_id", "quest_settlements", ["id"])
    op.create_index("ix_quest_settlements_source_id", "quest_settlements", ["source_id"])
    op.create_index("ix_quest_settlements_run_id", "quest_settlements", ["run_id"])
    op.create_index("ix_quest_settlements_user_id", "quest_settlements", ["user_id"])


def downgrade() -> None:
    op.drop_table("quest_settlements")
