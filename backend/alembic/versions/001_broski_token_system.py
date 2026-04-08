"""broski token system

Revision ID: 001_broski_token_system
Revises: 0b8c1f7f3f0b
Create Date: 2026-03-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '001_broski_token_system'
down_revision = '0b8c1f7f3f0b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # broski_wallets
    if not inspector.has_table('broski_wallets'):
        op.create_table(
            'broski_wallets',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('coins', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('xp', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('level_name', sa.String(), nullable=False, server_default='BROski Recruit'),
            sa.Column('last_daily_login', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_first_task_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id'),
        )
        op.create_index('ix_broski_wallets_id', 'broski_wallets', ['id'])
        op.create_index('ix_broski_wallets_user_id', 'broski_wallets', ['user_id'])

    # broski_transactions
    transaction_type = sa.Enum('earn', 'spend', 'bonus', name='transactiontype')
    transaction_type.create(bind, checkfirst=True)
    if not inspector.has_table('broski_transactions'):
        op.create_table(
            'broski_transactions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('wallet_id', sa.Integer(), sa.ForeignKey('broski_wallets.id'), nullable=False),
            sa.Column('amount', sa.Integer(), nullable=False),
            sa.Column('type', sa.Enum('earn', 'spend', 'bonus', name='transactiontype'), nullable=False),
            sa.Column('reason', sa.String(255), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_broski_transactions_id', 'broski_transactions', ['id'])
        op.create_index('ix_broski_transactions_wallet_id', 'broski_transactions', ['wallet_id'])

    # broski_achievements
    if not inspector.has_table('broski_achievements'):
        op.create_table(
            'broski_achievements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('slug', sa.String(64), nullable=False),
            sa.Column('name', sa.String(128), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('xp_reward', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('coin_reward', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('icon', sa.String(32), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('slug'),
        )
        op.create_index('ix_broski_achievements_id', 'broski_achievements', ['id'])
        op.create_index('ix_broski_achievements_slug', 'broski_achievements', ['slug'])

    # broski_user_achievements
    if not inspector.has_table('broski_user_achievements'):
        op.create_table(
            'broski_user_achievements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('wallet_id', sa.Integer(), sa.ForeignKey('broski_wallets.id'), nullable=False),
            sa.Column('achievement_slug', sa.String(64), sa.ForeignKey('broski_achievements.slug'), nullable=False),
            sa.Column('earned_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_broski_user_achievements_id', 'broski_user_achievements', ['id'])
        op.create_index('ix_broski_user_achievements_wallet_id', 'broski_user_achievements', ['wallet_id'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table('broski_user_achievements'):
        op.drop_table('broski_user_achievements')
    if inspector.has_table('broski_achievements'):
        op.drop_table('broski_achievements')
    if inspector.has_table('broski_transactions'):
        op.drop_table('broski_transactions')
    if inspector.has_table('broski_wallets'):
        op.drop_index('ix_broski_wallets_user_id', 'broski_wallets')
        op.drop_index('ix_broski_wallets_id', 'broski_wallets')
        op.drop_table('broski_wallets')

    sa.Enum(name='transactiontype').drop(bind, checkfirst=True)
