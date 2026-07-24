#!/usr/bin/env python3
"""
RQ Worker Script for Fuze
Starts background workers that process queue jobs with unique worker naming,
multiprocessing support for --workers, queue validation, and graceful signal handling.

Usage:
    python backend/worker.py
    python backend/worker.py --queue default --workers 4
"""

import os
import sys
import socket
import signal
import argparse
import multiprocessing
from rq import Worker, Queue
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


def run_single_worker(args, worker_index: int = 1):
    """Run a single RQ worker instance within a process context."""
    from services.task_queue import get_queue_connection
    rq_redis = get_queue_connection()

    if not rq_redis:
        logger.error("worker_redis_connection_failed")
        sys.exit(1)

    worker_name = f"fuze-worker-{args.queue}-{socket.gethostname()}-{os.getpid()}-{worker_index}"

    worker = Worker(
        [args.queue],
        connection=rq_redis,
        name=worker_name
    )

    def handle_shutdown(signum, frame):
        logger.info("worker_graceful_shutdown_requested", worker_name=worker_name)
        worker.request_stop()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Initialize Flask application context
    try:
        from run_production import create_app
        app = create_app()
        logger.info("worker_flask_context_ready", worker_name=worker_name)
    except Exception as e:
        logger.error("worker_flask_context_failed", error=str(e))
        sys.exit(1)

    try:
        with app.app_context():
            logger.info("worker_listening", worker_name=worker_name, queue=args.queue, burst=args.burst)
            worker.work(burst=args.burst)
    except Exception as e:
        logger.error("worker_execution_error", worker_name=worker_name, error=str(e))
        sys.exit(1)


def main():
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
        from services.background_analysis_service import analyze_bookmark_async
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
