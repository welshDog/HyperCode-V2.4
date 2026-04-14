"""008_phase_10g_stripe_schema

Revision ID: 008
Revises: 007
Create Date: 2026-04-14

Phase 10G — Stripe webhook DB writes.

Adds:
  users: subscription_tier, subscription_status, stripe_customer_id, broski_tokens
  payments table  (stripe_session_id UNIQUE — dedup guard)
  token_transactions table  (stripe_payment_intent_id UNIQUE — dedup guard)

All ALTER TABLE operations use IF NOT EXISTS guards via inspector so the
migration is safe to re-run on a partially-migrated DB.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def _col_exists(inspector, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspector.get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # ── 1. users — add Stripe + subscription columns ──────────────────────────
    if not _col_exists(inspector, "users", "subscription_tier"):
        op.add_column(
            "users",
            sa.Column(
                "subscription_tier",
                sa.String(32),
                nullable=False,
                server_default="free",
            ),
        )

    if not _col_exists(inspector, "users", "subscription_status"):
        op.add_column(
            "users",
            sa.Column(
                "subscription_status",
                sa.String(32),
                nullable=False,
                server_default="free",
            ),
        )

    if not _col_exists(inspector, "users", "stripe_customer_id"):
        op.add_column(
            "users",
            sa.Column("stripe_customer_id", sa.String(64), nullable=True),
        )

    if not _col_exists(inspector, "users", "broski_tokens"):
        op.add_column(
            "users",
            sa.Column(
                "broski_tokens",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    # ── 2. payments table ──────────────────────────────────────────────────────
    if not inspector.has_table("payments"):
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            # user_id stored as text — passed from Stripe metadata as a string
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("user_email", sa.Text(), nullable=True),
            sa.Column("amount_pence", sa.Integer(), nullable=False),
            sa.Column(
                "currency",
                sa.String(3),
                nullable=False,
                server_default="gbp",
            ),
            # stripe_session_id is the dedup key — must be UNIQUE
            sa.Column("stripe_session_id", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default="completed",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.UniqueConstraint("stripe_session_id", name="uq_payments_stripe_session_id"),
        )
        op.create_index("ix_payments_id", "payments", ["id"])
        op.create_index("ix_payments_user_id", "payments", ["user_id"])
        op.create_index(
            "ix_payments_stripe_session_id", "payments", ["stripe_session_id"], unique=True
        )

    # ── 3. token_transactions table ───────────────────────────────────────────
    if not inspector.has_table("token_transactions"):
        op.create_table(
            "token_transactions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            # user_id stored as text — matches how Stripe metadata passes it
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(128), nullable=False),
            # stripe_payment_intent_id used as dedup key (stores session ID in practice)
            sa.Column("stripe_payment_intent_id", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "stripe_payment_intent_id",
                name="uq_token_transactions_stripe_payment_intent_id",
            ),
        )
        op.create_index("ix_token_transactions_id", "token_transactions", ["id"])
        op.create_index("ix_token_transactions_user_id", "token_transactions", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("token_transactions"):
        op.drop_table("token_transactions")

    if inspector.has_table("payments"):
        op.drop_table("payments")

    if _col_exists(inspector, "users", "broski_tokens"):
        op.drop_column("users", "broski_tokens")

    if _col_exists(inspector, "users", "stripe_customer_id"):
        op.drop_column("users", "stripe_customer_id")

    if _col_exists(inspector, "users", "subscription_status"):
        op.drop_column("users", "subscription_status")

    if _col_exists(inspector, "users", "subscription_tier"):
        op.drop_column("users", "subscription_tier")
