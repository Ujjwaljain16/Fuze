#!/usr/bin/env python3
"""
RQ Worker Script for Fuze
Starts background workers that process queue jobs with unique worker naming,
multiprocessing support for --workers, queue validation and the RQ scheduler (retries).

Usage:
    python backend/worker.py
    python backend/worker.py --queue default --workers 4
"""

import os
import sys
import socket
import argparse
import multiprocessing
from rq import Worker
from core.logging_config import get_logger

logger = get_logger(__name__)

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

ALLOWED_QUEUES = {'default', 'high', 'low', 'background_analysis', 'recommendations'}


class FuzeWorker(Worker):
    """Custom RQ Worker that ensures SQLAlchemy session cleanup after every job."""

    def perform_job(self, job, queue):
        from core.logging_config import bind_request_context, clear_request_context
        bind_request_context(correlation_id=job.id, job=job.func_name)  # tag every log line of the job
        try:
            return super().perform_job(job, queue)
        finally:
            clear_request_context()
            try:
                from models import db
                db.session.remove()
            except Exception:
                pass


def run_single_worker(args, worker_index: int = 1):
    """Run a single RQ worker instance within a process context."""
    # Per process (each --workers child), before run_production is imported, so job failures are
    # reported tagged component=worker. RQ's work horses are forked from here and inherit it.
    from core.sentry_setup import init_sentry
    init_sentry(component='worker')

    from services.task_queue import get_queue_connection
    rq_redis = get_queue_connection()

    if not rq_redis:
        logger.error("worker_redis_connection_failed")
        sys.exit(1)

    worker_name = f"fuze-worker-{args.queue}-{socket.gethostname()}-{os.getpid()}-{worker_index}"

    worker = FuzeWorker(
        [args.queue],
        connection=rq_redis,
        name=worker_name
    )

    # Graceful shutdown: RQ installs its own SIGTERM/SIGINT handlers in work() (finish the
    # current job, then exit), so none are registered here.

    # Initialize Flask application context
    try:
        from run_production import create_app
        app = create_app()
        logger.info("worker_flask_context_ready", worker_name=worker_name)
    except Exception as e:
        logger.error("worker_flask_context_failed", error=str(e))
        sys.exit(1)

    # RQ forks a work horse per job, and the fork inherits the parent's connection pool. The
    # parent keeps using it (the reconciler thread), so a horse could talk over the same socket.
    # The child drops its inherited connections without closing them (close=False leaves the
    # parent's sockets intact) and opens its own.
    def _drop_inherited_pool():
        try:
            with app.app_context():
                from models import db
                db.engine.dispose(close=False)
        except Exception:
            pass

    os.register_at_fork(after_in_child=_drop_inherited_pool)

    # Load the embedding model once in this parent process. RQ forks a work horse per job, and
    # each fork shares the loaded model copy-on-write instead of loading ~130 MB again.
    # One torch thread per worker: the host has 2 vCPUs shared with the web workers.
    try:
        import torch
        torch.set_num_threads(1)
        from utils.embedding_utils import get_embedding_model
        get_embedding_model()
        logger.info("worker_embedding_model_preloaded", worker_name=worker_name)
    except Exception as e:
        # Jobs that need embeddings will fail and be retried; fetch-only work can still run.
        logger.error("worker_embedding_model_preload_failed", error=str(e))

    # The default-queue worker also runs the pipeline reconciler: a periodic pass that
    # re-enqueues bookmarks whose fetch or embedding was lost or deferred.
    if args.queue == 'default' and not args.burst:
        import threading
        from services.pipeline_reconciler import run_forever
        threading.Thread(target=run_forever, args=(app,), name='pipeline-reconciler', daemon=True).start()

    try:
        with app.app_context():
            logger.info("worker_listening", worker_name=worker_name, queue=args.queue, burst=args.burst)
            # with_scheduler: jobs enqueued with Retry(interval=...) or enqueue_in() sit in the
            # ScheduledJobRegistry until a scheduler moves them back to the queue. Without it,
            # every retry waited forever.
            worker.work(burst=args.burst, with_scheduler=True)
    except Exception as e:
        logger.error("worker_execution_error", worker_name=worker_name, error=str(e))
        sys.exit(1)


def main():
    # Before anything reads the configuration: worker processes (and the ones spawned below)
    # get the small worker connection pool from utils/unified_config.py, not the web one.
    os.environ.setdefault('FUZE_PROCESS_ROLE', 'worker')

    parser = argparse.ArgumentParser(description='Start RQ worker for background tasks')
    parser.add_argument('--queue', type=str, default='default', help='Queue name to listen to')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes')
    parser.add_argument('--burst', action='store_true', help='Run in burst mode (exit when empty)')

    args = parser.parse_args()

    if args.queue not in ALLOWED_QUEUES:
        logger.error("invalid_queue_name", queue=args.queue, allowed=list(ALLOWED_QUEUES))
        sys.exit(1)

    # Verify job handlers before starting workers
    try:
        from services.bookmark_processing_service import process_bookmark_content_task  # noqa: F401 -- import check only
        logger.info("worker_task_handlers_verified")
    except Exception as e:
        logger.warning("worker_task_handler_verification_warning", error=str(e))

    if args.workers > 1:
        logger.info("spawning_multiprocess_workers", count=args.workers, queue=args.queue)
        processes = []
        for i in range(args.workers):
            p = multiprocessing.Process(target=run_single_worker, args=(args, i + 1))
            p.start()
            processes.append(p)

        for p in processes:
            p.join()
    else:
        run_single_worker(args, 1)


if __name__ == '__main__':
    main()
