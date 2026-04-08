"""expand_quest_and_achievements

Revision ID: bb5dc8bb4cb3
Revises: aa4cb7aa3ba2
Create Date: 2026-03-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb5dc8bb4cb3'
down_revision: Union[str, Sequence[str], None] = 'aa4cb7aa3ba2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns to quests table
    op.add_column('quests', sa.Column('type', sa.String(length=50), server_default='standard', nullable=False))
    op.add_column('quests', sa.Column('time_limit_minutes', sa.Integer(), nullable=True))
    op.add_column('quests', sa.Column('next_quest_id', sa.BigInteger(), nullable=True))
    
    # Add foreign key for tiered quests (self-referential)
    op.create_foreign_key(
        'fk_quests_next_quest_id_quests',
        'quests', 'quests',
        ['next_quest_id'], ['id']
    )
    
    # Add columns to achievements table
    op.add_column('achievements', sa.Column('trigger_type', sa.String(length=50), server_default='standard', nullable=False))
    op.add_column('achievements', sa.Column('trigger_value', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from achievements table
    op.drop_column('achievements', 'trigger_value')
    op.drop_column('achievements', 'trigger_type')
    
    # Remove columns from quests table
    op.drop_constraint('fk_quests_next_quest_id_quests', 'quests', type_='foreignkey')
    op.drop_column('quests', 'next_quest_id')
    op.drop_column('quests', 'time_limit_minutes')
    op.drop_column('quests', 'type')
