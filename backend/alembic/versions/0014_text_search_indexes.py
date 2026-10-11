"""Indexed text search over saved content

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-12

Text search ran `ILIKE '%q%'` over title, notes and extracted_text. A leading wildcard
cannot use a b-tree index, so every query read every bookmark's full text (a sequential
scan of the table, ~100-180 ms on 6k rows of ~4 KB each, growing linearly).

- search_vector: a generated tsvector over title (weight A), notes (B) and the first
  100k characters of extracted_text (C), with a GIN index. Queries use
  websearch_to_tsquery (never raises on user syntax) and rank with ts_rank_cd. This
  handles what people type into a search box: words, in any order, with stemming.
  The body is capped so one huge page cannot exceed the 1 MB tsvector limit and make
  the bookmark's INSERT fail.
- A pg_trgm GIN index on title, for substring and partial-word matches on titles
  ("kube" -> "Kubernetes", "C++"), which word search cannot do. Substring matching
  inside full article text is dropped: it is what forced the full scan, and trigram
  indexes over full text would be several times the size of the text itself.

Adding a STORED generated column rewrites saved_content once (ACCESS EXCLUSIVE lock for
the duration). The GIN indexes are built CONCURRENTLY.
"""
from alembic import op

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None

SEARCH_VECTOR = """
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(notes, '')), 'B') ||
    setweight(to_tsvector('english', left(coalesce(extracted_text, ''), 100000)), 'C')
"""


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS search_vector tsvector "
        f"GENERATED ALWAYS AS ({SEARCH_VECTOR}) STORED"
    )
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_saved_content_search_vector "
            "ON saved_content USING gin (search_vector)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_saved_content_title_trgm "
            "ON saved_content USING gin (title gin_trgm_ops)"
        )


def downgrade():
    # pg_trgm is left installed: it may have existed before 0014 (Supabase preinstalls it)
    # and other objects may depend on it.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_saved_content_title_trgm")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_saved_content_search_vector")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS search_vector")
