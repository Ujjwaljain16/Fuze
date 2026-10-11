"""
Pipeline reconciler: the safety net that makes the bookmark pipeline eventually complete.

Any step can be lost: the enqueue after a save fails because Redis blipped, backpressure defers
an embedding, a worker dies mid-job, a site is down for an hour. Each of those leaves a status
in the database that says what is still missing. Every few minutes this finds those rows and
enqueues the missing step again. Jobs use fixed ids per bookmark and stage, so asking twice
never runs the work twice.

  scrape PENDING for a while          -> enqueue the fetch again
  scrape FAILED_FETCH (transient)     -> retry after 1h, 6h, 24h, then give up
  fetched but embedding not SUCCESS   -> enqueue the embedding (title/notes if the fetch failed)

The same loop also prunes old bookmark_events rows once a day (prune_bookmark_events). Every
pipeline event writes one, and the table is an audit trail, not a source of truth: the Redis
streams that feed live updates are already capped.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import delete, or_, select

from core.logging_config import get_logger

logger = get_logger(__name__)

INTERVAL_SECONDS = 300
STALE_AFTER = timedelta(minutes=15)
FETCH_RETRY_BACKOFF = [timedelta(hours=1), timedelta(hours=6), timedelta(hours=24)]
BATCH_LIMIT = 200
_LOCK_KEY = "fuze:pipeline_reconciler:lock"
_ATTEMPTS_KEY = "fuze:pipeline_reconciler:fetch_attempts:{}"
DEFAULT_EVENT_RETENTION_DAYS = 30
EVENT_RETENTION_BATCH = 5000
_RETENTION_KEY = "fuze:bookmark_events_retention:{}"


def _naive_utc(value: datetime) -> datetime:
    """scraped_at is timestamptz on Postgres (aware) but naive elsewhere; compare in naive UTC."""
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def _redis():
    from services.task_queue import get_redis_connection
    return get_redis_connection()


def _fetch_attempts(redis_conn, bookmark_id: int) -> int:
    try:
        return int(redis_conn.get(_ATTEMPTS_KEY.format(bookmark_id)) or 0)
    except Exception:
        return 0


def _count_fetch_attempt(redis_conn, bookmark_id: int) -> None:
    key = _ATTEMPTS_KEY.format(bookmark_id)
    redis_conn.incr(key)
    redis_conn.expire(key, int(timedelta(days=30).total_seconds()))


def reconcile(now: datetime = None) -> Dict[str, int]:
    """One pass. Safe to run from several processes: a Redis lock lets only one pass run at a time."""
    from models import SavedContent, db
    from services.pipeline_orchestrator import PipelineOrchestrator
    from services.task_queue import enqueue_bookmark_processing

    now = now or datetime.utcnow()
    counts = {"fetch_requeued": 0, "fetch_gave_up": 0, "embedding_requeued": 0, "deferred": 0}
    redis_conn = _redis()
    if redis_conn is None:
        logger.warning("pipeline_reconciler_no_redis")
        return counts
    if not redis_conn.set(_LOCK_KEY, "1", nx=True, ex=INTERVAL_SECONDS - 30):
        return counts

    stale = now - STALE_AFTER

    # 1. Fetches that never ran or failed for a reason that may have passed.
    candidates = (db.session.query(SavedContent.id, SavedContent.url, SavedContent.user_id,
                                   SavedContent.scrape_status, SavedContent.scraped_at)
                  .filter(or_(
                      (SavedContent.scrape_status == 'PENDING') & (SavedContent.saved_at < stale),
                      SavedContent.scrape_status == 'FAILED_FETCH',
                  ))
                  .order_by(SavedContent.saved_at)
                  .limit(BATCH_LIMIT).all())
    for bookmark_id, url, user_id, status, scraped_at in candidates:
        attempts = _fetch_attempts(redis_conn, bookmark_id)
        if attempts >= len(FETCH_RETRY_BACKOFF):
            counts["fetch_gave_up"] += 1
            continue
        if status == 'FAILED_FETCH' and scraped_at and _naive_utc(scraped_at) > now - FETCH_RETRY_BACKOFF[attempts]:
            continue
        if enqueue_bookmark_processing(bookmark_id, url, user_id) is not None:
            _count_fetch_attempt(redis_conn, bookmark_id)
            counts["fetch_requeued"] += 1
        else:
            counts["deferred"] += 1

    # 2. Fetched (or definitively failed) but never embedded: invisible to search until it is.
    missing_embeddings = (db.session.query(SavedContent.id, SavedContent.user_id)
                          .filter(SavedContent.scrape_status.in_(('SUCCESS', 'FAILED_FETCH', 'BLOCKED', 'DISALLOWED')),
                                  SavedContent.embedding_status != 'SUCCESS',
                                  or_(SavedContent.scraped_at.is_(None), SavedContent.scraped_at < stale))
                          .order_by(SavedContent.saved_at)
                          .limit(BATCH_LIMIT).all())
    orchestrator = PipelineOrchestrator()
    for bookmark_id, user_id in missing_embeddings:
        if orchestrator.request_embedding(bookmark_id, user_id):
            counts["embedding_requeued"] += 1
        else:
            counts["deferred"] += 1

    db.session.remove()
    if any(counts.values()):
        logger.info("pipeline_reconciled", extra=counts)
    return counts


def event_retention_days() -> int:
    """BOOKMARK_EVENTS_RETENTION_DAYS; 0 or less keeps events forever."""
    try:
        return int(os.environ.get('BOOKMARK_EVENTS_RETENTION_DAYS', DEFAULT_EVENT_RETENTION_DAYS))
    except ValueError:
        logger.warning("bookmark_events_retention_days_invalid")
        return DEFAULT_EVENT_RETENTION_DAYS


def prune_bookmark_events(now: datetime = None, batch_size: int = EVENT_RETENTION_BATCH) -> Optional[int]:
    """
    Delete bookmark_events older than the retention window, batch_size rows per statement so no
    single transaction holds locks on a large slice of the table. Runs at most once per UTC day
    across all processes (a Redis key per day). Returns rows deleted, or None when skipped.
    """
    from models import BookmarkEvent, db

    days = event_retention_days()
    if days <= 0:
        return None
    now = now or datetime.utcnow()
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    redis_conn = _redis()
    if redis_conn is None:
        return None
    day_key = _RETENTION_KEY.format(now.date().isoformat())
    if not redis_conn.set(day_key, "1", nx=True, ex=int(timedelta(days=2).total_seconds())):
        return None

    cutoff = now - timedelta(days=days)
    deleted = 0
    try:
        while True:
            oldest = select(BookmarkEvent.id).where(BookmarkEvent.created_at < cutoff).limit(batch_size)
            result = db.session.execute(
                delete(BookmarkEvent).where(BookmarkEvent.id.in_(oldest))
                .execution_options(synchronize_session=False))
            db.session.commit()
            deleted += result.rowcount or 0
            if (result.rowcount or 0) < batch_size:
                break
    except Exception:
        db.session.rollback()
        try:
            redis_conn.delete(day_key)  # let the next pass retry instead of waiting a day
        except Exception:
            pass
        raise
    finally:
        db.session.remove()
    logger.info("bookmark_events_pruned", extra={"deleted": deleted, "retention_days": days})
    return deleted


def run_forever(app, interval: int = INTERVAL_SECONDS, stop_event=None) -> None:
    """Loop for a daemon thread in the worker process."""
    import threading
    stop_event = stop_event or threading.Event()
    while not stop_event.wait(interval):
        try:
            with app.app_context():
                reconcile()
        except Exception:
            logger.exception("pipeline_reconciler_pass_failed")
        try:
            with app.app_context():
                prune_bookmark_events()
        except Exception:
            logger.exception("bookmark_events_prune_failed")
