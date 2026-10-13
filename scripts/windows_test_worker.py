"""
LOCAL-TESTING-ONLY worker runner for Windows dev machines.

worker.py's FuzeWorker (backend/worker.py) uses RQ's default forking Worker,
which relies on os.fork() -- not available on Windows at all. In actual
production this runs on Linux (Docker), where os.fork() works fine, so
worker.py itself is correct and is NOT changed here.

This script uses RQ's SimpleWorker (in-process, no fork) purely so bookmark
background processing can be exercised end-to-end on a Windows dev machine.
Never used in production and not referenced by anything else in the app.

Like the production default worker it also runs the pipeline reconciler (which enqueues
embeddings deferred under backpressure and recovers lost jobs) and the RQ scheduler (which
puts retries such as "fetch failed with HTTP 500, try again in 60 s" back on the queue).
RQ starts its scheduler in a child process, which on Windows re-imports this script and
starts a second worker, so here the scheduler runs in a thread instead.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../backend")

SCHEDULER_INTERVAL_SECONDS = 15   # each pass costs Redis commands; the shortest retry wait is 10 s


def run_scheduler(queue_names, connection, stop: threading.Event) -> None:
    """Move due scheduled jobs (retries, enqueue_in) back onto their queues."""
    from rq.scheduler import RQScheduler
    scheduler = RQScheduler(queue_names, connection=connection)
    while not stop.wait(SCHEDULER_INTERVAL_SECONDS):
        try:
            scheduler.acquire_locks()
            if scheduler.acquired_locks:
                scheduler.enqueue_scheduled_jobs()
                scheduler.heartbeat()
        except Exception as e:  # keep the thread alive across Redis hiccups
            print(f"scheduler pass failed: {e}", file=sys.stderr)
            time.sleep(SCHEDULER_INTERVAL_SECONDS)


def main() -> None:
    from rq import SimpleWorker
    from run_production import create_app
    from services.pipeline_reconciler import run_forever
    from services.task_queue import get_queue_connection

    app = create_app()

    # Load the embedding model once up front, as worker.py does, instead of inside the first job.
    try:
        from utils.embedding_utils import get_embedding_model
        with app.app_context():
            get_embedding_model()
    except Exception as e:
        print(f"embedding model preload failed: {e}", file=sys.stderr)

    threading.Thread(target=run_forever, args=(app,), name="pipeline-reconciler", daemon=True).start()

    queue_names = ["high", "default"]
    with app.app_context():
        conn = get_queue_connection()
        stop = threading.Event()
        threading.Thread(target=run_scheduler, args=(queue_names, conn, stop),
                         name="rq-scheduler", daemon=True).start()
        try:
            SimpleWorker(queue_names, connection=conn).work(burst=False)
        finally:
            stop.set()


if __name__ == "__main__":
    main()
