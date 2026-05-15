from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_mission_claims",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mission_date", sa.Date(), nullable=False),
        sa.Column("mission_slug", sa.String(length=64), nullable=False),
        sa.Column("awarded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("coins_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_session_id", sa.Integer(), nullable=True),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "mission_date",
            "mission_slug",
            name="uq_daily_mission_claim_user_date_slug",
        ),
    )
    op.create_index(
        "ix_daily_mission_claims_user_date",
        "daily_mission_claims",
        ["user_id", "mission_date"],
        unique=False,
    )
    op.create_index(
        "ix_daily_mission_claims_mission_date",
        "daily_mission_claims",
        ["mission_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_mission_claims_mission_date", table_name="daily_mission_claims")
    op.drop_index("ix_daily_mission_claims_user_date", table_name="daily_mission_claims")
    op.drop_table("daily_mission_claims")

