"""initial schema

Revision ID: 0b8c1f7f3f0b
Revises: 
Create Date: 2026-03-15 00:00:00.000000
"""

# pylint: disable=no-member,missing-function-docstring,line-too-long

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0b8c1f7f3f0b"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    userrole = postgresql.ENUM("ADMIN", "DEVELOPER", "VIEWER", name="userrole", create_type=False)
    projectstatus = postgresql.ENUM("ACTIVE", "ARCHIVED", "DRAFT", name="projectstatus", create_type=False)
    taskstatus = postgresql.ENUM("TODO", "IN_PROGRESS", "REVIEW", "DONE", name="taskstatus", create_type=False)

    userrole.create(bind, checkfirst=True)
    projectstatus.create(bind, checkfirst=True)
    taskstatus.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("role", userrole, server_default=sa.text("'DEVELOPER'::userrole"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", projectstatus, server_default=sa.text("'DRAFT'::projectstatus"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_projects_id", "projects", ["id"], unique=False)
    op.create_index("ix_projects_name", "projects", ["name"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("status", taskstatus, server_default=sa.text("'TODO'::taskstatus"), nullable=False),
        sa.Column("priority", sa.String(), server_default=sa.text("'medium'"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"], unique=False)
    op.create_index("ix_tasks_title", "tasks", ["title"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_title", table_name="tasks")
    op.drop_index("ix_tasks_id", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    postgresql.ENUM(name="taskstatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="projectstatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="userrole").drop(bind, checkfirst=True)
