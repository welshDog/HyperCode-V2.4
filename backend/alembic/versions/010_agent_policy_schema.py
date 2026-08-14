"""agent_policy_schema

Revision ID: 010
Revises: 009
Create Date: 2026-08-14

Part of Track 2: Policy-Aware Crew Orchestrator.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # --- Agent Registry ---
    op.create_table(
        'agent_registry',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('location', sa.Text(), nullable=False),
        sa.Column('trust_score', sa.Integer(), nullable=False, server_default='50'),
        sa.Column(
            'allowed_data_domains',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
        sa.Column(
            'capabilities',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index('ix_agent_registry_name', 'agent_registry', ['name'], unique=True)

    # --- Policy Rules ---
    op.create_table(
        'policy_rules',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column(
            'created_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index('ix_policy_rules_name', 'policy_rules', ['name'], unique=True)
    op.create_index('ix_policy_rules_priority', 'policy_rules', ['priority'])

    # --- Audit Log (tamper-evident) ---
    op.create_table(
        'audit_log',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'timestamp',
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('task_id', sa.Text(), nullable=True),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('data_domain', sa.Text(), nullable=True),
        sa.Column('policy_result', sa.Text(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hash_prev', sa.Text(), nullable=True),
        sa.Column('hash_self', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('ix_audit_log_agent_id', 'audit_log', ['agent_id'])


def downgrade():
    op.drop_index('ix_audit_log_agent_id', table_name='audit_log')
    op.drop_index('ix_audit_log_timestamp', table_name='audit_log')
    op.drop_index('ix_policy_rules_priority', table_name='policy_rules')
    op.drop_index('ix_policy_rules_name', table_name='policy_rules')
    op.drop_table('audit_log')
    op.drop_table('policy_rules')
    op.drop_table('agent_registry')
