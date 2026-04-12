"""add course_sync_events — Phase 2 Token Sync dedup table

Revision ID: 004_add_course_sync_events
Revises: 003_add_discord_id
Create Date: 2026-04-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "004_add_course_sync_events"
down_revision = "003_add_discord_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "course_sync_events" not in inspector.get_table_names():
        op.create_table(
            "course_sync_events",
            sa.Column("id",             sa.Integer(),      nullable=False),
            sa.Column("source_id",      sa.Text(),         nullable=False),  # idempotency key
            sa.Column("discord_id",     sa.String(32),     nullable=True),
            sa.Column("tokens_awarded", sa.Integer(),      nullable=False),
            sa.Column("reason",         sa.String(255),    nullable=True),
            sa.Column("created_at",     sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_id", name="uq_course_sync_source_id"),
        )
        op.create_index("ix_course_sync_events_id",         "course_sync_events", ["id"],         unique=False)
        op.create_index("ix_course_sync_events_discord_id", "course_sync_events", ["discord_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_course_sync_events_discord_id", table_name="course_sync_events")
    op.drop_index("ix_course_sync_events_id",         table_name="course_sync_events")
    op.drop_table("course_sync_events")
