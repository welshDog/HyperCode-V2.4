"""initial schema: check_definitions, check_results, alert_policies, self_heal_policies

Revision ID: 001
Revises: 
Create Date: 2026-06-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create alert_policies table
    op.create_table(
        'alert_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('severity_map', postgresql.JSON(), nullable=False),
        sa.Column('channels', postgresql.JSON(), nullable=False),
        sa.Column('dedupe_window_seconds', sa.Integer(), nullable=False),
        sa.Column('escalation_chain', postgresql.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create self_heal_policies table
    op.create_table(
        'self_heal_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('trigger_condition', sa.Text(), nullable=False),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('action_params', postgresql.JSON(), nullable=False),
        sa.Column('max_retries_per_window', sa.Integer(), nullable=False),
        sa.Column('window_seconds', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('require_approval', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create check_definitions table
    op.create_table(
        'check_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('target', sa.String(length=512), nullable=False),
        sa.Column('environment', sa.String(length=64), nullable=False),
        sa.Column('interval_seconds', sa.Integer(), nullable=False),
        sa.Column('thresholds', postgresql.JSON(), nullable=False),
        sa.Column('alert_policy_id', sa.Integer(), nullable=True),
        sa.Column('self_heal_policy_id', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['alert_policy_id'], ['alert_policies.id'], ),
        sa.ForeignKeyConstraint(['self_heal_policy_id'], ['self_heal_policies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create check_results table
    op.create_table(
        'check_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('check_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('environment', sa.String(length=64), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['check_id'], ['check_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_check_definitions_enabled', 'check_definitions', ['enabled'])
    op.create_index('ix_check_definitions_environment', 'check_definitions', ['environment'])
    op.create_index('ix_check_results_check_id', 'check_results', ['check_id'])
    op.create_index('ix_check_results_status', 'check_results', ['status'])
    op.create_index('ix_check_results_started_at', 'check_results', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_check_results_started_at', table_name='check_results')
    op.drop_index('ix_check_results_status', table_name='check_results')
    op.drop_index('ix_check_results_check_id', table_name='check_results')
    op.drop_index('ix_check_definitions_environment', table_name='check_definitions')
    op.drop_index('ix_check_definitions_enabled', table_name='check_definitions')
    op.drop_table('check_results')
    op.drop_table('check_definitions')
    op.drop_table('self_heal_policies')
    op.drop_table('alert_policies')
