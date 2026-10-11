"""Gunicorn settings for the API (started by supervisord.conf)."""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '7860')}"

# 2 workers for the Space's 2 vCPUs. gevent multiplexes I/O-bound requests inside each worker;
# CPU-bound work (embedding a query, bcrypt) is pushed to gevent's thread pool so it doesn't
# freeze every other request on the worker (see utils/cooperative.py).
workers = 2
worker_class = "gevent"
worker_connections = 1000
keepalive = 5

# A worker that stops responding is recycled after 60 s (it was 2000 s: one stuck worker took
# half the capacity for half an hour). Long work belongs in RQ jobs, not requests.
timeout = 60
graceful_timeout = 30

accesslog = "-"
errorlog = "-"

# No preload: each worker opens its own DB/Redis connections after fork, so no socket is shared
# between processes (or created before gevent patched the socket module).
preload_app = False


def post_fork(server, worker):
    # psycopg2 is a C extension that blocks the whole process while it waits on Postgres;
    # gevent's monkey-patching can't reach it. psycogreen installs a wait callback so every
    # query yields to other greenlets instead.
    from psycogreen.gevent import patch_psycopg
    patch_psycopg()

    # One torch thread per worker: two workers on two vCPUs must not each spawn a thread per core.
    try:
        import torch
        torch.set_num_threads(1)
    except Exception:
        pass
