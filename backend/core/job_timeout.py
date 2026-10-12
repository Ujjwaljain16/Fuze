"""
RQ enforces job_timeout by raising JobTimeoutException inside the running code. It subclasses
Exception, so a broad `except Exception` swallows it: the job keeps running until the worker
SIGKILLs it at timeout+60s, and no FAILED status is ever written. Code on the job path catches
this first and re-raises it.
"""

try:
    from rq.timeouts import JobTimeoutException
except ImportError:  # rq not installed (e.g. tooling); nothing can raise it then
    class JobTimeoutException(Exception):  # type: ignore[no-redef]
        pass

__all__ = ['JobTimeoutException']
