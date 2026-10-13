"""Set the role's HNSW defaults for real: load pgvector before naming its settings

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-13

0017 did nothing on Supabase. In a session where pgvector has not been used yet, `hnsw.iterative_scan` is
only a placeholder name, and Supabase refuses `ALTER ROLE ... SET` for a placeholder ("permission denied to
set parameter"). 0017 caught that error and carried on, so it applied cleanly and changed nothing.

Once a vector function has run in the session, the setting is the extension's own (user-settable) one and
the same statement is accepted. So this touches the vector type first, then sets the defaults. Applied to a
database that already has them it is a no-op, and the application still verifies what each connection
received and sends the settings itself when it is not enough.
"""
from alembic import op

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None

EF_SEARCH = '60'  # the most passages one search asks for (CANDIDATES_PER_QUERY)


def upgrade():
    op.execute(f"""
        DO $$
        BEGIN
            PERFORM '[1,2,3]'::vector;   -- load pgvector so its settings are real, not placeholders
            EXECUTE format('ALTER ROLE %I SET hnsw.iterative_scan = %L', current_user, 'relaxed_order');
            EXECUTE format('ALTER ROLE %I SET hnsw.ef_search = %L', current_user, '{EF_SEARCH}');
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'could not set HNSW role defaults: %', SQLERRM;
        END
        $$
    """)


def downgrade():
    # 0017 downgrades by resetting the same two settings; leave them for it.
    pass
