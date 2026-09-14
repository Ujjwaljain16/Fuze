"""
LOCAL-TESTING-ONLY worker runner for Windows dev machines.

worker.py's FuzeWorker (backend/worker.py) uses RQ's default forking Worker,
which relies on os.fork() -- not available on Windows at all. In actual
production this runs on Linux (Docker), where os.fork() works fine, so
worker.py itself is correct and is NOT changed here.

This script uses RQ's SimpleWorker (in-process, no fork) purely so bookmark
background processing can be exercised end-to-end on a Windows dev machine.
Never used in production and not referenced by anything else in the app.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../backend")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/../backend")

from run_production import create_app
from services.task_queue import get_queue_connection
from rq import SimpleWorker

app = create_app()
with app.app_context():
    conn = get_queue_connection()
    w = SimpleWorker(["default", "high"], connection=conn)
    w.work(burst=False)
