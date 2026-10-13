"""Make iterative HNSW scan the database default

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-13

Filtered vector search (WHERE user_id = ...) needs `hnsw.iterative_scan = relaxed_order` and a large enough
`hnsw.ef_search`, or HNSW stops after ef_search candidates and a user can get fewer results than exist.
The application used to send both settings before every search: a network round trip each time, about
215 ms between a Hugging Face Space and a Supabase project in another region.

Setting them as database defaults means every connection starts with them, through any pooler mode. Each
connection records what it actually received (run_production: `ann_defaults`) and the search code only
sends the settings itself when that is not enough, so a database without this migration still works.

ALTER DATABASE needs ownership; where it is not allowed (a managed role without it) this logs a notice and
carries on, and searches keep sending the settings themselves.
"""
from alembic import op

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None

EF_SEARCH = '60'  # the most passages one search asks for (CANDIDATES_PER_QUERY)


def upgrade():
    op.execute(f"""
        DO $$
        BEGIN
            EXECUTE format('ALTER DATABASE %I SET hnsw.iterative_scan = %L', current_database(), 'relaxed_order');
            EXECUTE format('ALTER DATABASE %I SET hnsw.ef_search = %L', current_database(), '{EF_SEARCH}');
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'could not set HNSW database defaults: %', SQLERRM;
        END
        $$
    """)


def downgrade():
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format('ALTER DATABASE %I RESET hnsw.iterative_scan', current_database());
            EXECUTE format('ALTER DATABASE %I RESET hnsw.ef_search', current_database());
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'could not reset HNSW database defaults: %', SQLERRM;
        END
        $$
    """)
