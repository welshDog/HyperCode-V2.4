"""initial_schema

Revision ID: d3f8669e746a
Revises: 
Create Date: 2026-03-04 23:22:49.788558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f8669e746a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('discriminator', sa.String(length=10), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_messages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create economy table
    op.create_table(
        'economy',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('lifetime_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lifetime_spent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_daily_claim', sa.DateTime(timezone=True), nullable=True),
        sa.Column('daily_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_daily_streak', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memory_crystals', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create focus_sessions table
    op.create_table(
        'focus_sessions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('project_name', sa.String(length=255), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('tokens_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_hyperfocus', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_focus_sessions_user_id'), 'focus_sessions', ['user_id'], unique=False)

    # Create quests table
    op.create_table(
        'quests',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('requirement_type', sa.String(length=100), nullable=False),
        sa.Column('requirement_count', sa.Integer(), nullable=False),
        sa.Column('token_reward', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('xp_reward', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memory_crystal_reward', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_quests table
    op.create_table(
        'user_quests',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('quest_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.Enum('AVAILABLE', 'IN_PROGRESS', 'COMPLETED', 'EXPIRED', name='queststatus'), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['quest_id'], ['quests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_quests_user_id'), 'user_quests', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_quests_quest_id'), 'user_quests', ['quest_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user_quests')
    op.execute('DROP TYPE queststatus')
    op.drop_table('quests')
    op.drop_table('focus_sessions')
    op.drop_table('economy')
    op.drop_table('users')
