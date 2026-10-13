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
  embedded, analysis PENDING/FAILED   -> enqueue the analysis, backing off 1h, 6h, 24h between
                                         tries, only while the user has Gemini allowance left

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
ANALYSIS_TASK = "services.bookmark_processing_service.analyze_bookmark_task"
ANALYSIS_RETRY_BACKOFF = [timedelta(hours=1), timedelta(hours=6), timedelta(hours=24)]  # wait after try n
MAX_ANALYSIS_ATTEMPTS = len(ANALYSIS_RETRY_BACKOFF) + 1
ANALYSIS_BATCH_LIMIT = 20  # Gemini calls are slow and metered; the rest wait for the next pass
ANALYSIS_PER_USER_LIMIT = 5  # one user's backlog doesn't take the whole pass
_ANALYSIS_ATTEMPTS_KEY = "fuze:pipeline_reconciler:analysis_attempts:{}"
_ANALYSIS_LAST_TRY_KEY = "fuze:pipeline_reconciler:analysis_last_try:{}"


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


def _fetch_attempts_many(redis_conn, bookmark_ids) -> Dict[int, int]:
    """Attempt counts for many bookmarks in ONE Redis command (each command counts against a metered plan)."""
    ids = list(bookmark_ids)
    if not ids:
        return {}
    try:
        values = redis_conn.mget([_ATTEMPTS_KEY.format(i) for i in ids])
    except Exception:
        return {i: 0 for i in ids}
    return {i: int(v or 0) for i, v in zip(ids, values)}


def move_due_retries(redis_conn, queue_names=("default", "high")) -> int:
    """Put retries whose wait is over back on their queues; returns how many.

    RQ normally does this in a scheduler that wakes every second. That is two Redis commands a second, all
    day, per worker, and used up Upstash's free 500,000 a month in a day or two. The reconciler already
    wakes every few minutes under a lock, so it does the same job there. The waits are 60 s or more (and 10 s
    for one cache warm-up), so a retry can be late by up to one interval; nothing here needs it sooner.
    """
    from rq import Queue
    from rq.job import Job
    from rq.utils import current_timestamp

    moved = 0
    for name in queue_names:
        queue = Queue(name, connection=redis_conn)
        registry = queue.scheduled_job_registry
        job_ids = registry.get_jobs_to_schedule(current_timestamp())
        if not job_ids:
            continue
        with redis_conn.pipeline() as pipeline:
            for job in Job.fetch_many(job_ids, connection=redis_conn):
                if job is not None:
                    queue._enqueue_job(job, pipeline=pipeline, at_front=job.should_enqueue_at_front())
            for job_id in job_ids:
                registry.remove(job_id, pipeline=pipeline)
            pipeline.execute()
        moved += len(job_ids)
    return moved


def _count_fetch_attempt(redis_conn, bookmark_id: int) -> None:
    key = _ATTEMPTS_KEY.format(bookmark_id)
    redis_conn.incr(key)
    redis_conn.expire(key, int(timedelta(days=30).total_seconds()))


def reconcile(now: datetime = None) -> Dict[str, int]:
    """One pass. Safe to run from several processes: a Redis lock lets only one pass run at a time."""
    from models import SavedContent, db
    from services.pipeline_orchestrator import PipelineOrchestrator
    from services.task_queue import bookmark_job_id, enqueue_bookmark_processing, is_job_active

    now = now or datetime.utcnow()
    counts = {"fetch_requeued": 0, "fetch_gave_up": 0, "embedding_requeued": 0,
              "analysis_requeued": 0, "analysis_gave_up": 0, "deferred": 0, "retries_moved": 0}
    redis_conn = _redis()
    if redis_conn is None:
        logger.warning("pipeline_reconciler_no_redis")
        return counts
    if not redis_conn.set(_LOCK_KEY, "1", nx=True, ex=INTERVAL_SECONDS - 30):
        return counts

    try:
        counts["retries_moved"] = move_due_retries(redis_conn)
    except Exception:
        logger.exception("move_due_retries_failed")

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
    attempts_by_id = _fetch_attempts_many(redis_conn, [c[0] for c in candidates])
    for bookmark_id, url, user_id, status, scraped_at in candidates:
        attempts = attempts_by_id.get(bookmark_id, 0)
        if (attempts < len(FETCH_RETRY_BACKOFF) and status == 'FAILED_FETCH' and scraped_at
                and _naive_utc(scraped_at) > now - FETCH_RETRY_BACKOFF[attempts]):
            continue  # still inside its wait: decided from data already in hand, no Redis command
        if is_job_active(bookmark_job_id(bookmark_id), redis_conn):
            # Still waiting its turn (or running, or waiting for its own retry): not lost. Without
            # this a long queue was counted as failed tries and bookmarks at the back of a big
            # import were marked FAILED after about half an hour without ever being fetched.
            continue
        if attempts >= len(FETCH_RETRY_BACKOFF):
            # Terminal: drop it out of this oldest-first window so it can't crowd out new work.
            db.session.query(SavedContent).filter(SavedContent.id == bookmark_id).update(
                {SavedContent.scrape_status: 'FAILED'}, synchronize_session=False)
            db.session.commit()
            counts["fetch_gave_up"] += 1
            continue
        if enqueue_bookmark_processing(bookmark_id, url, user_id) is not None:
            _count_fetch_attempt(redis_conn, bookmark_id)
            counts["fetch_requeued"] += 1
        else:
            counts["deferred"] += 1

    # 2. Fetched (or definitively failed) but never embedded: invisible to search until it is.
    missing_embeddings = (db.session.query(SavedContent.id, SavedContent.user_id)
                          .filter(SavedContent.scrape_status.in_(('SUCCESS', 'FAILED_FETCH', 'BLOCKED', 'DISALLOWED', 'FAILED')),
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

    # 3. Embedded with text but never analysed.
    _retry_analyses(redis_conn, now, stale, counts)

    db.session.remove()
    if any(counts.values()):
        logger.info("pipeline_reconciled", extra=counts)
    return counts


def analysis_job_id(bookmark_id: int) -> str:
    return f"analyze_bookmark_{bookmark_id}"


def _analysis_state_many(redis_conn, bookmark_ids) -> Dict[int, tuple]:
    """(attempts, last try) for many bookmarks in ONE Redis command."""
    ids = list(bookmark_ids)
    if not ids:
        return {}
    keys = [key.format(i) for i in ids for key in (_ANALYSIS_ATTEMPTS_KEY, _ANALYSIS_LAST_TRY_KEY)]
    try:
        values = redis_conn.mget(keys)
    except Exception:
        return {}
    return {i: (values[2 * n], values[2 * n + 1]) for n, i in enumerate(ids)}


def _analysis_due(redis_conn, bookmark_id: int, now: datetime, stored: Optional[tuple] = None) -> Optional[bool]:
    """True when the next analysis try is due, False while backing off, None once out of tries.

    `stored` is the (attempts, last try) pair read earlier for many bookmarks at once; without it the
    two values are read here, one command each."""
    try:
        if stored is not None:
            attempts, last_try = int(stored[0] or 0), stored[1]
        else:
            attempts = int(redis_conn.get(_ANALYSIS_ATTEMPTS_KEY.format(bookmark_id)) or 0)
            last_try = redis_conn.get(_ANALYSIS_LAST_TRY_KEY.format(bookmark_id))
    except Exception:
        return False
    if attempts >= MAX_ANALYSIS_ATTEMPTS:
        return None
    if attempts == 0 or not last_try:
        return True
    if isinstance(last_try, bytes):
        last_try = last_try.decode()
    return datetime.fromisoformat(last_try) <= _naive_utc(now) - ANALYSIS_RETRY_BACKOFF[attempts - 1]


def _count_analysis_attempt(redis_conn, bookmark_id: int, now: datetime) -> None:
    ttl = int(timedelta(days=30).total_seconds())
    attempts_key = _ANALYSIS_ATTEMPTS_KEY.format(bookmark_id)
    redis_conn.incr(attempts_key)
    redis_conn.expire(attempts_key, ttl)
    redis_conn.set(_ANALYSIS_LAST_TRY_KEY.format(bookmark_id), _naive_utc(now).isoformat(), ex=ttl)


def _retry_analyses(redis_conn, now: datetime, stale: datetime, counts: Dict[str, int]) -> None:
    """
    Re-enqueue analysis for bookmarks that are embedded and have text but no analysis: it failed,
    hit a rate limit, or was deferred because the user's daily share of the system Gemini key ran
    out. Newest first, so tries that gave up sink below fresh work instead of filling the window.
    """
    from models import SavedContent, db
    from services.multi_user_api_manager import has_gemini_allowance
    from services.pipeline_orchestrator import MAX_QUEUE_BACKLOG
    from services.task_queue import enqueue_unique, get_queue, is_job_active

    candidates = (db.session.query(SavedContent.id, SavedContent.user_id)
                  .filter(SavedContent.embedding_status == 'SUCCESS',
                          SavedContent.extracted_text.isnot(None),
                          SavedContent.extracted_text != '',
                          SavedContent.analysis_status.in_(('PENDING', 'FAILED')),
                          or_(SavedContent.embedded_at.is_(None), SavedContent.embedded_at < stale))
                  .order_by(SavedContent.saved_at.desc())
                  .limit(BATCH_LIMIT).all())
    if not candidates:
        return
    queue = get_queue()
    try:
        backed_up = queue is None or len(queue) >= MAX_QUEUE_BACKLOG
    except Exception:
        backed_up = False
    if backed_up:
        counts["deferred"] += len(candidates)
        return

    # Every candidate used to cost four Redis commands each pass (about 450 a pass with a backlog and the
    # Gemini key out of quota, over 100,000 a day). Now: one command for all their counters, and a command
    # about a job or a user only for a candidate that is actually due.
    state = _analysis_state_many(redis_conn, [c[0] for c in candidates])
    allowance: Dict[int, bool] = {}
    per_user: Dict[int, int] = {}
    for bookmark_id, user_id in candidates:
        if counts["analysis_requeued"] >= ANALYSIS_BATCH_LIMIT:
            break
        due = _analysis_due(redis_conn, bookmark_id, now, stored=state.get(bookmark_id, (None, None)))
        if due is None:
            counts["analysis_gave_up"] += 1
            continue
        if not due or per_user.get(user_id, 0) >= ANALYSIS_PER_USER_LIMIT:
            continue
        if user_id not in allowance:
            allowance[user_id] = has_gemini_allowance(user_id)
        if not allowance[user_id]:
            counts["deferred"] += 1  # not a try: the allowance comes back tomorrow
            continue
        if is_job_active(analysis_job_id(bookmark_id), redis_conn):
            continue  # already queued or running: waiting is not a failed try
        job = enqueue_unique(queue, ANALYSIS_TASK, analysis_job_id(bookmark_id),
                             kwargs={'bookmark_id': bookmark_id, 'user_id': user_id}, job_timeout=300)
        if job is None:
            counts["deferred"] += 1
            continue
        _count_analysis_attempt(redis_conn, bookmark_id, now)
        per_user[user_id] = per_user.get(user_id, 0) + 1
        counts["analysis_requeued"] += 1


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
