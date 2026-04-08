"""dashboard_tasks — public task table for live dashboard (Task 9)

Revision ID: 002_dashboard_tasks
Revises: 001_broski_token_system
Create Date: 2026-04-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '002_dashboard_tasks'
down_revision = '001_broski_token_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'dashboard_tasks' not in existing_tables:
        op.create_table(
            'dashboard_tasks',
            sa.Column('id',          sa.Integer(),                                      nullable=False),
            sa.Column('title',       sa.String(),                                       nullable=False),
            sa.Column('description', sa.Text(),                                         nullable=True),
            sa.Column('status',      sa.Enum('todo', 'in_progress', 'done', 'cancelled',
                                             name='dashboardtaskstatus'),               nullable=True),
            sa.Column('priority',    sa.String(),                                       nullable=True),
            sa.Column('source',      sa.Enum('manual', 'auto', 'system',
                                             name='dashboardtasksource'),               nullable=True),
            sa.Column('created_at',  sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column('updated_at',  sa.DateTime(timezone=True),                       nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_dashboard_tasks_id',    'dashboard_tasks', ['id'],    unique=False)
        op.create_index('ix_dashboard_tasks_title', 'dashboard_tasks', ['title'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_dashboard_tasks_title', table_name='dashboard_tasks')
    op.drop_index('ix_dashboard_tasks_id',    table_name='dashboard_tasks')
    op.drop_table('dashboard_tasks')
    op.execute("DROP TYPE IF EXISTS dashboardtaskstatus")
    op.execute("DROP TYPE IF EXISTS dashboardtasksource")
