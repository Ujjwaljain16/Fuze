"""
Add Postgres RPC functions for server-side semantic search.

These functions execute HNSW ANN search entirely inside PostgreSQL,
eliminating the Python/SQLAlchemy round-trip overhead.

Functions added:
  search_bookmarks_semantic_v1(user_id, query_embedding, match_count)
    → Returns top-N results ordered by cosine distance using HNSW index.

  search_bookmarks_hybrid_v1(user_id, query_embedding, text_query, match_count)
    → Returns results ranked by combined cosine similarity + text relevance.

Design notes:
  - SET enable_seqscan=off forces planner to use HNSW index (never sequential scan)
  - Versioned function names (_v1) allow future signature changes without breakage
  - CREATE OR REPLACE — idempotent, safe to re-apply
  - No user data is modified — pure SELECT functions

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-24
"""

from alembic import op

revision = '0006'
down_revision = '0005'


def upgrade():
    # Semantic search RPC: ANN via HNSW, returns candidate rows ordered by cosine distance
    op.execute("""
        CREATE OR REPLACE FUNCTION search_bookmarks_semantic_v1(
            p_user_id    INTEGER,
            p_embedding  vector(384),
            p_limit      INTEGER DEFAULT 20
        )
        RETURNS TABLE (
            id              INTEGER,
            title           TEXT,
            url             TEXT,
            notes           TEXT,
            extracted_text  TEXT,
            distance        FLOAT
        )
        LANGUAGE plpgsql
        STABLE
        AS $$
        BEGIN
            SET LOCAL enable_seqscan = off;

            -- Enforce dimension guard: reject mismatched embeddings early
            IF vector_dims(p_embedding) != 384 THEN
                RAISE EXCEPTION 'query embedding must be 384 dimensions, got %',
                    vector_dims(p_embedding);
            END IF;

            RETURN QUERY
            SELECT
                sc.id,
                sc.title::TEXT,
                sc.url::TEXT,
                sc.notes::TEXT,
                sc.extracted_text::TEXT,
                (sc.embedding <=> p_embedding)::FLOAT AS distance
            FROM saved_content sc
            WHERE sc.user_id = p_user_id
              AND sc.embedding IS NOT NULL
            ORDER BY sc.embedding <=> p_embedding
            LIMIT p_limit;
        END;
        $$;
    """)

    # Hybrid search RPC: combines vector similarity with ts_rank text search
    op.execute("""
        CREATE OR REPLACE FUNCTION search_bookmarks_hybrid_v1(
            p_user_id     INTEGER,
            p_embedding   vector(384),
            p_text_query  TEXT,
            p_limit       INTEGER DEFAULT 20,
            p_vector_weight FLOAT DEFAULT 0.7,
            p_text_weight   FLOAT DEFAULT 0.3
        )
        RETURNS TABLE (
            id              INTEGER,
            title           TEXT,
            url             TEXT,
            notes           TEXT,
            extracted_text  TEXT,
            hybrid_score    FLOAT
        )
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_tsquery tsquery;
        BEGIN
            SET LOCAL enable_seqscan = off;

            IF vector_dims(p_embedding) != 384 THEN
                RAISE EXCEPTION 'query embedding must be 384 dimensions, got %',
                    vector_dims(p_embedding);
            END IF;

            -- Build tsquery safely; fall back to plainto_tsquery if phrase fails
            BEGIN
                v_tsquery := phraseto_tsquery('english', p_text_query);
            EXCEPTION WHEN others THEN
                v_tsquery := plainto_tsquery('english', p_text_query);
            END;

            RETURN QUERY
            WITH vector_results AS (
                SELECT
                    sc.id,
                    sc.title::TEXT,
                    sc.url::TEXT,
                    sc.notes::TEXT,
                    sc.extracted_text::TEXT,
                    -- Convert distance to similarity: 1 - distance (cosine distance ∈ [0,2])
                    (1.0 - (sc.embedding <=> p_embedding) / 2.0)::FLOAT AS vec_score,
                    COALESCE(
                        ts_rank(
                            to_tsvector('english', COALESCE(sc.title, '') || ' ' ||
                                        COALESCE(sc.notes, '') || ' ' ||
                                        COALESCE(LEFT(sc.extracted_text, 2000), '')),
                            v_tsquery
                        ),
                        0.0
                    )::FLOAT AS text_score
                FROM saved_content sc
                WHERE sc.user_id = p_user_id
                  AND sc.embedding IS NOT NULL
                ORDER BY sc.embedding <=> p_embedding
                LIMIT p_limit * 3  -- over-fetch for re-ranking
            )
            SELECT
                vr.id,
                vr.title,
                vr.url,
                vr.notes,
                vr.extracted_text,
                (p_vector_weight * vr.vec_score + p_text_weight * vr.text_score)::FLOAT AS hybrid_score
            FROM vector_results vr
            ORDER BY hybrid_score DESC
            LIMIT p_limit;
        END;
        $$;
    """)


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS search_bookmarks_semantic_v1(INTEGER, vector, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS search_bookmarks_hybrid_v1(INTEGER, vector, TEXT, INTEGER, FLOAT, FLOAT)")
