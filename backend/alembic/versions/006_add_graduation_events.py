"""006_add_graduation_events

Revision ID: 006
Revises: 005
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'graduation_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('discord_id', sa.String(32), nullable=True),
        sa.Column('source_id', sa.Text(), unique=True, nullable=False),  # idempotency key
        sa.Column('badge_slug', sa.String(64), nullable=True, default='hyper-graduate'),
        sa.Column('tokens_awarded', sa.Integer(), nullable=True, default=500),
        sa.Column('portfolio_url', sa.Text(), nullable=True),
        sa.Column('discord_role_assigned', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
    )
    op.create_index('ix_graduation_events_source_id', 'graduation_events', ['source_id'], unique=True)
    op.create_index('ix_graduation_events_discord_id', 'graduation_events', ['discord_id'])


def downgrade():
    op.drop_index('ix_graduation_events_discord_id')
    op.drop_index('ix_graduation_events_source_id')
    op.drop_table('graduation_events')
