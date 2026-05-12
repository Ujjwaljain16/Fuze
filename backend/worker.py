#!/usr/bin/env python
"""
RQ Worker Script
Run this script to start background workers that process bookmark tasks

Usage:
    python backend/worker.py
    
    Or with specific queue:
    python backend/worker.py --queue default
    
    Or with multiple workers:
    python backend/worker.py --workers 4
"""

import os
import sys
import argparse
from rq import Worker, Queue
from rq.worker import WorkerStatus
from core.logging_config import get_logger

logger = get_logger(__name__)

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import after path setup
try:
    from services.task_queue import redis_conn, get_redis_connection
    logger.info("worker_import_success", module="task_queue")
except Exception as e:
    logger.error("worker_import_failed", module="task_queue", error=str(e))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Start RQ worker for background tasks')
    parser.add_argument(
        '--queue',
        type=str,
        default='default',
        help='Queue name to listen to (default: default)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of worker processes (default: 1)'
    )
    parser.add_argument(
        '--burst',
        action='store_true',
        help='Run in burst mode (exit when queue is empty)'
    )
    
    args = parser.parse_args()
    
    # Get Redis connection (try existing, or create new)
    rq_redis = redis_conn
    if not rq_redis:
        # Try to create connection if not already available
        try:
            rq_redis = get_redis_connection()
            rq_redis.ping()
        except Exception as e:
            logger.error("worker_redis_not_available", error=str(e))
            sys.exit(1)
    
    # Create queue
    queue = Queue(args.queue, connection=rq_redis)
    
    logger.info("worker_starting", queue=args.queue, burst_mode=args.burst, redis_status="connected")
    
    # Test that we can import the task function
    try:
        from blueprints.bookmarks import process_bookmark_content_task
        logger.info("worker_task_import_success")
    except Exception as e:
        logger.error("worker_task_import_failed", error=str(e))
        sys.exit(1)
    
    # Create and start worker
    worker = Worker(
        [queue],
        connection=rq_redis,
        name=f"fuze-worker-{args.queue}"
    )
    
    logger.info("worker_created", worker_name=worker.name)
    logger.info("worker_listening")
    
    import signal
    
    def handle_shutdown(signum, frame):
        logger.info("worker_shutdown_signal_received")
        worker.request_stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    try:
        if args.burst:
            # Burst mode: process all jobs and exit
            logger.info("worker_mode_burst")
            worker.work(burst=True)
        else:
            # Normal mode: keep running
            logger.info("worker_mode_continuous")
            worker.work()
    except Exception as e:
        logger.error("worker_runtime_error", error=str(e))
        sys.exit(1)

if __name__ == '__main__':
    main()

