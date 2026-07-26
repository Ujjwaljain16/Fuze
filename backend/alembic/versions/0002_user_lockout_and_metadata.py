"""Add user metadata, provider, and lockout columns (idempotent)

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-01 00:00:00.000000

"""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    # Ensure all user columns exist on users table idempotently
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS user_metadata JSON;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_name VARCHAR(50);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS provider_user_id VARCHAR(200);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMP;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS account_locked_until TIMESTAMP;")

    # Case-insensitive unique indexes
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique_lower ON users (lower(email));")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique_lower ON users (lower(username));")

def downgrade():
    pass
