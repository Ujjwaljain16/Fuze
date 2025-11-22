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
import logging
from rq import Worker, Queue, Connection
from rq.worker import WorkerStatus

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    logger.info("Successfully imported task_queue module")
except Exception as e:
    logger.error(f"Failed to import task_queue: {e}", exc_info=True)
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
            print(f"ERROR: Redis connection not available: {e}")
            print("Please ensure Redis is running and configured.")
            sys.exit(1)
    
    # Create queue
    queue = Queue(args.queue, connection=rq_redis)
    
    logger.info(f"Starting RQ worker for queue: {args.queue}")
    logger.info(f"Redis connection: {'Connected' if rq_redis.ping() else 'Failed'}")
    logger.info(f"Burst mode: {args.burst}")
    logger.info("-" * 50)
    
    # Test that we can import the task function
    try:
        from blueprints.bookmarks import process_bookmark_content_task
        logger.info("Successfully imported process_bookmark_content_task")
    except Exception as e:
        logger.error(f"Failed to import process_bookmark_content_task: {e}", exc_info=True)
        logger.error("Worker cannot process jobs without the task function!")
        sys.exit(1)
    
    # Create and start worker
    worker = Worker(
        [queue],
        connection=rq_redis,
        name=f"fuze-worker-{args.queue}"
    )
    
    logger.info(f"Worker created: {worker.name}")
    logger.info("Worker is now listening for jobs...")
    
    try:
        if args.burst:
            # Burst mode: process all jobs and exit
            logger.info("Running in burst mode - will exit when queue is empty")
            worker.work(burst=True)
        else:
            # Normal mode: keep running
            logger.info("Running in continuous mode - will keep processing jobs")
            worker.work()
    except KeyboardInterrupt:
        logger.info("\nWorker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

