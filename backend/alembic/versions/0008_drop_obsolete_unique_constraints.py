"""Drop obsolete unique constraints in favor of unique indexes (idempotent)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-26 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Drop redundant table-level UNIQUE constraints created by raw CREATE TABLE syntax
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key;")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;")
    op.execute("ALTER TABLE token_families DROP CONSTRAINT IF EXISTS token_families_family_id_key;")

    # 2. Ensure explicit unique indexes exist matching models.py
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_token_families_family_id ON token_families (family_id);")

def downgrade():
    pass
