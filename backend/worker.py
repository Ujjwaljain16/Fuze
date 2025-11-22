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
from rq import Worker, Queue, Connection
from rq.worker import WorkerStatus

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import after path setup
from services.task_queue import redis_conn, get_redis_connection

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
    
    print(f"Starting RQ worker for queue: {args.queue}")
    print(f"Redis connection: {'Connected' if rq_redis.ping() else 'Failed'}")
    print(f"Burst mode: {args.burst}")
    print("-" * 50)
    
    # Create and start worker
    worker = Worker(
        [queue],
        connection=rq_redis,
        name=f"fuze-worker-{args.queue}"
    )
    
    try:
        if args.burst:
            # Burst mode: process all jobs and exit
            worker.work(burst=True)
        else:
            # Normal mode: keep running
            worker.work()
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
    except Exception as e:
        print(f"Worker error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

