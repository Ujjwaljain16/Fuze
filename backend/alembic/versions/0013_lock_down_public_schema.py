"""Lock down the public schema against Supabase's data API

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-12

Supabase serves every table in `public` over its REST/RPC API using the anon key
that ships in the frontend bundle, and grants the anon/authenticated roles full
privileges on new tables by default. Fuze only accesses data through its own
backend (which connects as the table owner and bypasses RLS), so:

- enable row level security on every table (no policies = no rows for API roles),
- revoke anon/authenticated privileges, now and for tables created later,
- drop the unused search RPC functions from 0006, which took an arbitrary
  user_id and were executable by any role through /rest/v1/rpc.

On plain Postgres (no anon/authenticated roles) only the RLS and function steps apply.
"""
import importlib.util
import os

from alembic import op

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

API_ROLES = ("anon", "authenticated")


def upgrade():
    op.execute("""
        DO $$
        DECLARE t text;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
            END LOOP;
        END $$;
    """)
    for role in API_ROLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role};
                    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {role};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {role};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM {role};
                END IF;
            END $$;
        """)
    op.execute("DROP FUNCTION IF EXISTS search_bookmarks_semantic_v1(INTEGER, vector, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS search_bookmarks_hybrid_v1(INTEGER, vector, TEXT, INTEGER, FLOAT, FLOAT)")


def downgrade():
    # Restores the 0006 functions and turns RLS off. API-role privileges are deliberately
    # not re-granted: exposing the tables over the anon key was never intended.
    path = os.path.join(os.path.dirname(__file__), "0006_search_rpc_functions.py")
    spec = importlib.util.spec_from_file_location("rev_0006", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.upgrade()
    op.execute("""
        DO $$
        DECLARE t text;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t);
            END LOOP;
        END $$;
    """)
