"""Make iterative HNSW scan a default of the application's database role

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-13

0015 set the vector-search settings as DATABASE defaults. On Supabase that is not allowed (the database
belongs to Supabase's own admin role), so 0015 logged a notice and changed nothing there: production kept
paying a round trip per search for settings the database could have supplied at connect time.

A role may set its own defaults on any Postgres, Supabase included. This sets the same two settings for
the role that runs the migration, which is the role the application connects as (and it is the same role
on a plain Postgres, where 0015 already worked). The application still checks what each connection really
received and sends the settings itself when it is not enough.
"""
from alembic import op

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None

EF_SEARCH = '60'  # the most passages one search asks for (CANDIDATES_PER_QUERY)


def upgrade():
    op.execute(f"""
        DO $$
        BEGIN
            EXECUTE format('ALTER ROLE %I SET hnsw.iterative_scan = %L', current_user, 'relaxed_order');
            EXECUTE format('ALTER ROLE %I SET hnsw.ef_search = %L', current_user, '{EF_SEARCH}');
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'could not set HNSW role defaults: %', SQLERRM;
        END
        $$
    """)


def downgrade():
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format('ALTER ROLE %I RESET hnsw.iterative_scan', current_user);
            EXECUTE format('ALTER ROLE %I RESET hnsw.ef_search', current_user);
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'could not reset HNSW role defaults: %', SQLERRM;
        END
        $$
    """)
