"""
LOCAL-TESTING-ONLY worker runner for Windows dev machines.

worker.py's FuzeWorker (backend/worker.py) uses RQ's default forking Worker,
which relies on os.fork() -- not available on Windows at all. In actual
production this runs on Linux (Docker), where os.fork() works fine, so
worker.py itself is correct and is NOT changed here.

This script uses RQ's SimpleWorker (in-process, no fork) purely so bookmark
background processing can be exercised end-to-end on a Windows dev machine.
Never used in production and not referenced by anything else in the app.

Like the production default worker it also runs the pipeline reconciler: it enqueues
embeddings deferred under backpressure, recovers lost jobs, and puts retries such as "fetch
failed with HTTP 500, try again in 60 s" back on the queue. There is no RQ scheduler: it woke
every second and cost two Redis commands each time (see backend/worker.py).
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../backend")

WORKER_TTL_SECONDS = 1800   # an idle worker renews its Redis registration once per TTL


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
        SimpleWorker(queue_names, connection=conn, worker_ttl=WORKER_TTL_SECONDS).work(burst=False)


if __name__ == "__main__":
    main()
