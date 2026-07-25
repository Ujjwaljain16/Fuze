#!/usr/bin/env python3
"""
scripts/backfill_embeddings.py
==============================
One-shot backfill: enqueues embedding generation jobs for all saved_content
rows where embedding IS NULL.

Run this after deploying embed_worker.py and before enabling ITEM 2
(two-stage retrieval). The RQ worker must be running to process the jobs.

Usage:
    cd backend
    python scripts/backfill_embeddings.py
    python scripts/backfill_embeddings.py --batch-size 100 --queue default
    python scripts/backfill_embeddings.py --verify          # only check null count, no enqueue
    python scripts/backfill_embeddings.py --dry-run         # count + print, no enqueue
"""

import os
import sys
import argparse
import time

# Ensure backend/ is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()


def get_null_embedding_count(session) -> int:
    from sqlalchemy import text
    result = session.execute(
        text("SELECT COUNT(*) FROM saved_content WHERE embedding IS NULL")
    )
    return result.scalar() or 0


def get_null_embedding_ids(session, batch_size: int, offset: int) -> list:
    from sqlalchemy import text
    result = session.execute(
        text(
            "SELECT id FROM saved_content WHERE embedding IS NULL "
            "ORDER BY id LIMIT :limit OFFSET :offset"
        ),
        {"limit": batch_size, "offset": offset},
    )
    return [row[0] for row in result.fetchall()]


def run_verify():
    """Print the current null embedding count. Gate 0 check."""
    from models import db
    from run_production import create_app

    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(
                text("SELECT COUNT(*) FROM saved_content WHERE embedding IS NULL")
            )
            null_count = result.scalar() or 0
            result_total = conn.execute(text("SELECT COUNT(*) FROM saved_content"))
            total = result_total.scalar() or 0

    null_rate = null_count / total if total > 0 else 0.0
    gate_passed = null_rate < 0.01  # Gate 0: < 1%

    try:
        from core.metrics import embedding_null_rate
        embedding_null_rate.set(null_rate)
    except Exception:
        pass

    print(f"\n[Backfill Verify] Null embeddings: {null_count} / {total} "
          f"({null_rate:.2%}) — Gate 0: {'PASS ✓' if gate_passed else 'FAIL ✗'}")

    if not gate_passed:
        print(f"  [FAIL] {null_count} rows still have NULL embeddings. "
              f"Run backfill or wait for workers to complete.")
        sys.exit(1)
    else:
        print("  [PASS] Embedding null rate < 1%. Gate 0 cleared.")


def run_backfill(batch_size: int = 50, queue_name: str = 'default', dry_run: bool = False):
    from run_production import create_app
    from models import db
    from services.task_queue import enqueue_embedding_job, is_rq_available

    app = create_app()

    with app.app_context():
        if not dry_run:
            if not is_rq_available():
                print("[ERROR] RQ / Redis is not available. Start the worker before running backfill.")
                sys.exit(1)

        with db.engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(
                text("SELECT COUNT(*) FROM saved_content WHERE embedding IS NULL")
            )
            total_null = result.scalar() or 0

        if total_null == 0:
            print("\n[Backfill] No NULL embeddings found. Gate 0 already cleared.")
            return

        print(f"\n[Backfill] Found {total_null} bookmarks with NULL embeddings.")
        print(f"           Batch size: {batch_size}  Queue: {queue_name}  Dry-run: {dry_run}")
        print(f"           Estimated jobs: {total_null}")

        enqueued = 0
        failed = 0
        offset = 0

        with db.engine.connect() as conn:
            while True:
                from sqlalchemy import text
                result = conn.execute(
                    text(
                        "SELECT id FROM saved_content WHERE embedding IS NULL "
                        "ORDER BY id LIMIT :limit OFFSET :offset"
                    ),
                    {"limit": batch_size, "offset": offset},
                )
                ids = [row[0] for row in result.fetchall()]

                if not ids:
                    break

                for bookmark_id in ids:
                    if dry_run:
                        print(f"  [DRY RUN] Would enqueue embed_bookmark_job({bookmark_id})")
                        enqueued += 1
                    else:
                        job = enqueue_embedding_job(bookmark_id, queue_name=queue_name)
                        if job:
                            enqueued += 1
                        else:
                            failed += 1
                            print(f"  [WARN] Failed to enqueue bookmark_id={bookmark_id}")

                offset += batch_size

                if not dry_run:
                    # Brief pause between batches to avoid Redis saturation
                    time.sleep(0.05)

                print(f"  Progress: {min(offset, total_null)}/{total_null} processed...", end='\r')

        print(f"\n\n[Backfill] Complete. Enqueued: {enqueued}  Failed: {failed}")

        if failed > 0:
            print(f"[WARN] {failed} jobs failed to enqueue. Re-run backfill to retry.")

        if not dry_run:
            print("\nMonitor worker progress:")
            print("  python scripts/backfill_embeddings.py --verify")


def main():
    parser = argparse.ArgumentParser(description="Backfill missing embeddings via RQ")
    parser.add_argument("--batch-size", type=int, default=50,
                        help="Number of bookmark IDs per batch (default: 50)")
    parser.add_argument("--queue", type=str, default="default",
                        help="RQ queue name (default: default)")
    parser.add_argument("--verify", action="store_true",
                        help="Check null embedding count only (Gate 0 verification)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print jobs without enqueuing")
    args = parser.parse_args()

    if args.verify:
        run_verify()
    else:
        run_backfill(batch_size=args.batch_size, queue_name=args.queue, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
