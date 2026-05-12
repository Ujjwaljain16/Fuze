"""
Run once after Phase 3 deploy to embed all existing bookmarks.
Usage: python -m scripts.backfill_embeddings

Processes in batches of 50 to avoid OOM.
Safe to run multiple times — skips already-embedded content.
Estimated time: ~1 second per 50 items on CPU.
"""
import sys
import os
from dotenv import load_dotenv

# Add backend dir to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load root .env file
root_dir = os.path.dirname(backend_dir)
dotenv_path = os.path.join(root_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
elif os.path.exists(os.path.join(backend_dir, '.env')):
    load_dotenv(os.path.join(backend_dir, '.env'))

from rq import Queue

from services.task_queue import get_redis_connection
from jobs.embedding_job import backfill_missing_embeddings

def run():
    redis_conn = get_redis_connection()
    if not redis_conn:
        print("Error: Could not connect to Redis.")
        sys.exit(1)
        
    queue = Queue('low', connection=redis_conn)
    # Enqueue in batches — each batch is a separate job
    # This distributes load over time rather than spiking CPU
    queue.enqueue(
        backfill_missing_embeddings,
        args=(None, 50),  # all users, 50 at a time
        job_timeout=600,
    )
    print("Backfill job enqueued. Monitor via RQ dashboard.")

if __name__ == "__main__":
    run()
