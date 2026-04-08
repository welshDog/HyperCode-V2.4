"""add_transactions_and_achievements

Revision ID: aa4cb7aa3ba2
Revises: d3f8669e746a
Create Date: 2026-03-04 23:58:52.408367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa4cb7aa3ba2'
down_revision: Union[str, Sequence[str], None] = 'd3f8669e746a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create achievements table
    op.create_table(
        'achievements',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=10), server_default='🏆', nullable=True),
        sa.Column('requirement', sa.Integer(), server_default='1', nullable=True),
        sa.Column('reward', sa.Integer(), server_default='50', nullable=True),
        sa.Column('category', sa.String(length=50), server_default='general', nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_achievements table
    op.create_table(
        'user_achievements',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('achievement_id', sa.BigInteger(), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['achievement_id'], ['achievements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'achievement_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_achievements')
    op.drop_table('achievements')
    op.drop_table('transactions')
