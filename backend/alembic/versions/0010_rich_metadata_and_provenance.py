"""Rich metadata and acquisition provenance columns + bookmark_metadata JSONB table

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-26 19:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add acquisition metadata & provenance columns to saved_content
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS author VARCHAR(255);")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS reading_time INTEGER DEFAULT 0;")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS language VARCHAR(10);")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS content_hash CHAR(64);")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS strategy_used VARCHAR(20);")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS scrapling_version VARCHAR(20);")
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS extractor_version VARCHAR(20);")

    # Index for fast content_hash lookup and deduplication
    op.execute("CREATE INDEX IF NOT EXISTS idx_saved_content_content_hash ON saved_content (content_hash);")

    # 2. Create bookmark_metadata table for rich JSON payloads (JSON-LD, OpenGraph, Breadcrumbs, etc.)
    op.execute("""
    CREATE TABLE IF NOT EXISTS bookmark_metadata (
        bookmark_id BIGINT PRIMARY KEY REFERENCES saved_content(id) ON DELETE CASCADE,
        jsonb_payload JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # GIN index for fast JSONB field querying
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookmark_metadata_jsonb ON bookmark_metadata USING gin (jsonb_payload);")

def downgrade():
    op.execute("DROP TABLE IF EXISTS bookmark_metadata CASCADE;")
    op.execute("DROP INDEX IF EXISTS idx_saved_content_content_hash;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS author;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS reading_time;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS published_at;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS language;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS content_hash;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS strategy_used;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS scrapling_version;")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS extractor_version;")
