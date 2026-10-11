#!/usr/bin/env python3
"""
One-shot backfill: run AI content analysis for every saved_content row that has
extracted text but no content_analysis row.

Needed because analysis silently never ran for any bookmark until the
`pipeline_run_id` TypeError in bookmark_processing_service was fixed.

Runs synchronously (no RQ) and paces calls so it stays under the Gemini
per-user limit (15/min). Safe to stop and re-run: it only selects rows that are
still unanalyzed.

Usage (from backend/):
    python scripts/backfill_content_analysis.py --verify
    python scripts/backfill_content_analysis.py --dry-run --limit 20
    python scripts/backfill_content_analysis.py --limit 200 --delay 5
"""

import argparse
import os
import sys
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

MISSING_SQL = """
    SELECT sc.id, sc.user_id
    FROM saved_content sc
    WHERE sc.extracted_text IS NOT NULL
      AND sc.extracted_text <> ''
      AND NOT EXISTS (SELECT 1 FROM content_analysis ca WHERE ca.content_id = sc.id)
    ORDER BY sc.id
    LIMIT :limit
"""


def counts(conn):
    with_text = conn.execute(text(
        "SELECT COUNT(*) FROM saved_content WHERE extracted_text IS NOT NULL AND extracted_text <> ''"
    )).scalar() or 0
    analyzed = conn.execute(text(
        "SELECT COUNT(DISTINCT content_id) FROM content_analysis"
    )).scalar() or 0
    missing = conn.execute(text(
        "SELECT COUNT(*) FROM saved_content sc WHERE sc.extracted_text IS NOT NULL AND sc.extracted_text <> '' "
        "AND NOT EXISTS (SELECT 1 FROM content_analysis ca WHERE ca.content_id = sc.id)"
    )).scalar() or 0
    return with_text, analyzed, missing


def main():
    parser = argparse.ArgumentParser(description="Backfill missing AI content analysis")
    parser.add_argument("--limit", type=int, default=100, help="Max rows to process this run (default 100)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Seconds between analyses; 5s keeps one user under 15/min (default 5)")
    parser.add_argument("--max-consecutive-failures", type=int, default=5,
                        help="Stop early after this many failures in a row (quota/key problems)")
    parser.add_argument("--verify", action="store_true", help="Only print counts")
    parser.add_argument("--dry-run", action="store_true", help="List rows that would be analyzed")
    args = parser.parse_args()

    from run_production import create_app
    from models import db

    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            with_text, analyzed, missing = counts(conn)
        print(f"[backfill] with extracted text: {with_text}  analyzed: {analyzed}  missing: {missing}")
        if args.verify or missing == 0:
            return

        with db.engine.connect() as conn:
            rows = conn.execute(text(MISSING_SQL), {"limit": args.limit}).fetchall()

        if args.dry_run:
            for content_id, user_id in rows:
                print(f"  would analyze content_id={content_id} user_id={user_id}")
            print(f"[backfill] dry run: {len(rows)} rows")
            return

        from services.background_analysis_service import analyze_content

        done = failed = streak = 0
        for i, (content_id, user_id) in enumerate(rows, 1):
            analyze_content(content_id, user_id)
            with db.engine.connect() as conn:
                ok = conn.execute(
                    text("SELECT 1 FROM content_analysis WHERE content_id = :cid"), {"cid": content_id}
                ).first() is not None
            if ok:
                done += 1
                streak = 0
            else:
                failed += 1
                streak += 1
            print(f"  [{i}/{len(rows)}] content_id={content_id} {'ok' if ok else 'FAILED'}")
            if streak >= args.max_consecutive_failures:
                print(f"[backfill] stopping: {streak} failures in a row (check GEMINI_API_KEY / quota)")
                break
            if i < len(rows):
                time.sleep(args.delay)

        print(f"[backfill] analyzed: {done}  failed: {failed}  (re-run to continue)")


if __name__ == "__main__":
    main()
