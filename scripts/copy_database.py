"""Copy every application table from one Fuze Postgres database to another (a region move, a restore).

    set SOURCE_DATABASE_URL=postgresql://...old project...   (read only: this script never writes to it)
    set TARGET_DATABASE_URL=postgresql://...new project...
    python scripts/copy_database.py --dry-run       # counts rows, changes nothing
    python scripts/copy_database.py                 # copies, then verifies

The target must already have the schema, built by the project's own migrations
(`DATABASE_URL=<target> python -m alembic -c alembic.ini upgrade head`), at the same Alembic revision
as the source, and its tables must be empty (use --truncate-target to empty them first).

How it copies: one REPEATABLE READ, read-only transaction on the source (a consistent snapshot even if
the app is still writing), then PostgreSQL's own COPY between the two databases, table by table in
foreign-key order, inside ONE transaction on the target: either everything arrives or nothing does.
COPY moves vectors, JSON and timestamps exactly as stored. Generated columns (such as the search
vector, which the target rebuilds itself) are skipped, ID counters are reset past the highest copied
id, and the row counts and an id checksum of every table are compared at the end. Exit code 0 only
when every table matches.

URLs come from the environment (or --source / --target) so passwords stay out of the shell history
when you use the variables. Nothing is printed except table names and counts.
"""

import argparse
import os
import sys
import tempfile
from collections import defaultdict, deque

import psycopg2

SKIP_TABLES = {"alembic_version"}


def connect(url, readonly=False):
    conn = psycopg2.connect(url, connect_timeout=15)
    if readonly:
        conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
    return conn


def one(cur, sql, params=None):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def app_tables(cur):
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    return [t for (t,) in cur.fetchall() if t not in SKIP_TABLES]


def foreign_key_order(cur, tables):
    """Tables with the ones they reference first. Self references are fine (one COPY checks at its end)."""
    cur.execute("""
        SELECT c.conrelid::regclass::text, c.confrelid::regclass::text
        FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.contype = 'f' AND n.nspname = 'public'""")
    wanted = set(tables)
    depends = defaultdict(set)
    for child, parent in cur.fetchall():
        child, parent = child.replace("public.", "").strip('"'), parent.replace("public.", "").strip('"')
        if child in wanted and parent in wanted and child != parent:
            depends[child].add(parent)
    ready = deque(sorted(t for t in tables if not depends[t]))
    order, remaining = [], {t: set(depends[t]) for t in tables}
    while ready:
        table = ready.popleft()
        order.append(table)
        for other in sorted(remaining):
            if table in remaining[other]:
                remaining[other].discard(table)
                if not remaining[other] and other not in order and other not in ready:
                    ready.append(other)
    if len(order) != len(tables):
        raise SystemExit("Foreign keys form a cycle between tables; copy them by hand: "
                         + ", ".join(sorted(set(tables) - set(order))))
    return order


def copyable_columns(cur, table):
    """Columns that can be written: everything except generated columns (the target computes those)."""
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND is_generated = 'NEVER'
        ORDER BY ordinal_position""", (table,))
    return [c for (c,) in cur.fetchall()]


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def fingerprint(cur, table):
    """(row count, sum of integer ids) for a table: cheap, and catches a missing or duplicated row."""
    count = one(cur, f"SELECT count(*) FROM {quoted(table)}")
    has_id = one(cur, """SELECT count(*) FROM information_schema.columns
                         WHERE table_schema='public' AND table_name=%s AND column_name='id'
                           AND data_type IN ('integer','bigint','smallint')""", (table,))
    id_sum = one(cur, f"SELECT COALESCE(sum(id), 0) FROM {quoted(table)}") if has_id else None
    return count, id_sum


def reset_sequences(cur):
    cur.execute("""
        SELECT table_name, column_name, pg_get_serial_sequence(quote_ident(table_name), column_name)
        FROM information_schema.columns WHERE table_schema = 'public'""")
    for table, column, sequence in cur.fetchall():
        if sequence and table not in SKIP_TABLES:
            cur.execute(f"SELECT setval(%s, COALESCE((SELECT max({quoted(column)}) FROM {quoted(table)}), 1), "
                        f"(SELECT max({quoted(column)}) IS NOT NULL FROM {quoted(table)}))", (sequence,))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=os.environ.get("SOURCE_DATABASE_URL"))
    parser.add_argument("--target", default=os.environ.get("TARGET_DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true", help="count rows and check the target, change nothing")
    parser.add_argument("--truncate-target", action="store_true", help="empty the target's tables first")
    args = parser.parse_args()
    if not args.source or not args.target:
        sys.exit("Set SOURCE_DATABASE_URL and TARGET_DATABASE_URL (or pass --source/--target).")
    if args.source == args.target:
        sys.exit("Source and target are the same database.")

    source, target = connect(args.source, readonly=True), connect(args.target)
    src, dst = source.cursor(), target.cursor()

    src_rev = one(src, "SELECT version_num FROM alembic_version") if one(src, "SELECT to_regclass('public.alembic_version')") else None
    dst_rev = one(dst, "SELECT version_num FROM alembic_version") if one(dst, "SELECT to_regclass('public.alembic_version')") else None
    if src_rev != dst_rev:
        sys.exit(f"Schema revisions differ: source {src_rev}, target {dst_rev}. Run `alembic upgrade head` on the target "
                 "(and on the source, if it is behind) first.")

    tables = foreign_key_order(src, app_tables(src))
    missing = [t for t in tables if not one(dst, "SELECT to_regclass(%s)", (f"public.{quoted(t)}",))]
    if missing:
        sys.exit("The target has no table(s): " + ", ".join(missing) + ". Build its schema with alembic first.")

    filled = {t: one(dst, f"SELECT count(*) FROM {quoted(t)}") for t in tables}
    filled = {t: n for t, n in filled.items() if n}
    if filled and not args.truncate_target and not args.dry_run:
        sys.exit("The target is not empty (" + ", ".join(f"{t}: {n}" for t, n in filled.items())
                 + "). Use --truncate-target to empty it first, or point at a fresh project.")

    print(f"Schema revision {src_rev}. {len(tables)} tables, copied in this order:")
    plan = {t: fingerprint(src, t) for t in tables}
    for t in tables:
        print(f"  {t:<28} {plan[t][0]:>8} rows")
    if args.dry_run:
        print("Dry run: nothing was copied.")
        return

    if filled:
        dst.execute("TRUNCATE " + ", ".join(quoted(t) for t in tables) + " RESTART IDENTITY CASCADE")
    for t in tables:
        columns = ", ".join(quoted(c) for c in copyable_columns(src, t))
        with tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024) as buffer:
            src.copy_expert(f"COPY (SELECT {columns} FROM {quoted(t)}) TO STDOUT", buffer)
            buffer.seek(0)
            dst.copy_expert(f"COPY {quoted(t)} ({columns}) FROM STDIN", buffer)
        print(f"  copied {t}")
    reset_sequences(dst)
    target.commit()  # all or nothing
    source.rollback()

    # statistics for the planner, then verify against the snapshot the copy was taken from
    target.autocommit = True
    for t in tables:
        dst.execute(f"ANALYZE {quoted(t)}")
    bad = []
    print("\nVerification (rows / id checksum):")
    for t in tables:
        got = fingerprint(dst, t)
        ok = got == plan[t]
        print(f"  {'ok ' if ok else 'BAD'} {t:<28} {got[0]:>8} rows")
        if not ok:
            bad.append((t, plan[t], got))
    if bad:
        for t, expected, got in bad:
            print(f"MISMATCH {t}: source {expected}, target {got}", file=sys.stderr)
        sys.exit(1)
    print("\nEvery table matches. Point the application at the target, then check /health/readiness.")


if __name__ == "__main__":
    main()
