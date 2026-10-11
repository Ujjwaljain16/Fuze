"""Passage-level and profile chunks with embeddings for semantic retrieval

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-11

One embedding per bookmark only covers its first ~5,000 characters, so most of a
long article is invisible to search. Each passage is embedded individually; a
'profile' row holds the embedding of the LLM content profile (what the item is for).
"""
from alembic import op

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_chunks (
            id           BIGSERIAL PRIMARY KEY,
            content_id   INTEGER NOT NULL REFERENCES saved_content(id) ON DELETE CASCADE,
            user_id      INTEGER NOT NULL,
            kind         VARCHAR(16) NOT NULL DEFAULT 'passage',
            chunk_index  INTEGER NOT NULL,
            text         TEXT NOT NULL,
            embedding    vector(384),
            -- vectors from different models live in different spaces and must never be compared
            embedding_model VARCHAR(120) NOT NULL,
            created_at   TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT uq_content_chunks_content_kind_idx UNIQUE (content_id, kind, chunk_index)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_content_chunks_user_model ON content_chunks (user_id, embedding_model)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_content_chunks_embedding_hnsw ON content_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS content_chunks")
