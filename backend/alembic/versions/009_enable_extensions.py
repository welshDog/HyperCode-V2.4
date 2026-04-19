"""009_enable_extensions

Revision ID: 009
Revises: 008
Create Date: 2026-04-19

Enable `pgcrypto` and `uuid-ossp` so downstream features can use
`gen_random_uuid()` and `uuid_generate_v4()` without ad-hoc psql steps.

Idempotent — `IF NOT EXISTS` guards make this safe to re-run.
"""
from alembic import op

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade():
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
    op.execute('DROP EXTENSION IF EXISTS pgcrypto')
