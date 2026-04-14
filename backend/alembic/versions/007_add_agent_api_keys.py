"""007_add_agent_api_keys

Revision ID: 007
Revises: 006
Create Date: 2026-04-14

Phase 10D — Per-agent API key table.
One row per internal agent. key_hash stores SHA-256 of the raw hc_ key.
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'agent_api_keys',
        sa.Column('id',             sa.Integer,                  primary_key=True),
        sa.Column('agent_name',     sa.String(64),               nullable=False),
        sa.Column('key_prefix',     sa.String(16),               nullable=False),
        sa.Column('key_hash',       sa.String(64),               nullable=False),
        sa.Column('rate_limit_rpm', sa.Integer,                  nullable=False, server_default='200'),
        sa.Column('is_active',      sa.Boolean,                  nullable=False, server_default='true'),
        sa.Column('created_at',     sa.DateTime(timezone=True),  server_default=sa.func.now()),
        sa.Column('last_used_at',   sa.DateTime(timezone=True),  nullable=True),
        sa.UniqueConstraint('agent_name', name='uq_agent_api_keys_agent_name'),
        sa.UniqueConstraint('key_hash',   name='uq_agent_api_keys_key_hash'),
    )
    op.create_index('ix_agent_api_keys_agent_name', 'agent_api_keys', ['agent_name'])
    op.create_index('ix_agent_api_keys_key_hash',   'agent_api_keys', ['key_hash'])


def downgrade():
    op.drop_index('ix_agent_api_keys_key_hash',   table_name='agent_api_keys')
    op.drop_index('ix_agent_api_keys_agent_name', table_name='agent_api_keys')
    op.drop_table('agent_api_keys')
