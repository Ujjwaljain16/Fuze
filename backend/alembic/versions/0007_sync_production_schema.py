"""Sync production schema indexes and columns (idempotent)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-26 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add embedding_metadata JSON columns safely (idempotent)
    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS embedding_metadata JSON;")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS embedding_metadata JSON;")
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS embedding_metadata JSON;")
    op.execute("ALTER TABLE subtasks ADD COLUMN IF NOT EXISTS embedding_metadata JSON;")

    # 2. Add missing indexes safely (idempotent)
    op.execute("CREATE INDEX IF NOT EXISTS idx_saved_content_user_unanalyzed ON saved_content (user_id, id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_user_id ON feedback (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_project_id ON feedback (project_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_content_id ON feedback (content_id);")

def downgrade():
    pass
