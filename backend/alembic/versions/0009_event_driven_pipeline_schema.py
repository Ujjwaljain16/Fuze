"""Event driven pipeline status columns and bookmark events persistent store

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-26 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add pipeline stage status columns to bookmarks
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS scrape_status VARCHAR(20) DEFAULT 'PENDING';")
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(20) DEFAULT 'PENDING';")
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20) DEFAULT 'PENDING';")
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS scraped_at TIMESTAMP WITH TIME ZONE;")
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMP WITH TIME ZONE;")
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP WITH TIME ZONE;")
    op.execute("ALTER TABLE bookmarks ADD COLUMN IF NOT EXISTS pipeline_version INTEGER DEFAULT 1;")

    # 2. Create bookmark_events table for persistent audit & timeline
    op.execute("""
    CREATE TABLE IF NOT EXISTS bookmark_events (
        id BIGSERIAL PRIMARY KEY,
        event_id VARCHAR(64) NOT NULL,
        bookmark_id BIGINT REFERENCES bookmarks(id) ON DELETE CASCADE,
        user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
        pipeline_run_id VARCHAR(64) NOT NULL,
        sequence INTEGER NOT NULL DEFAULT 1,
        type VARCHAR(100) NOT NULL,
        schema_version INTEGER NOT NULL DEFAULT 1,
        data JSONB,
        error JSONB,
        metadata_json JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_bookmark_events_event_id ON bookmark_events (event_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookmark_events_bookmark_seq ON bookmark_events (bookmark_id, sequence);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookmark_events_user_created ON bookmark_events (user_id, created_at);")

def downgrade():
    op.execute("DROP TABLE IF EXISTS bookmark_events CASCADE;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS scrape_status;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS embedding_status;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS analysis_status;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS scraped_at;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS embedded_at;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS analyzed_at;")
    op.execute("ALTER TABLE bookmarks DROP COLUMN IF EXISTS pipeline_version;")
