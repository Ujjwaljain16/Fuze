"""
CPU-bound work inside gevent web workers.

gevent only switches greenlets at I/O. A model.encode() or bcrypt hash runs for tens to hundreds
of milliseconds of pure CPU, and every other request on that worker waits for it. Under a
monkey-patched worker, run_cpu_bound() moves the call to gevent's native thread pool (torch and
bcrypt release the GIL while they compute), so the hub keeps serving other requests. Elsewhere
(RQ workers, scripts, tests) it simply calls the function.
"""


def run_cpu_bound(fn, *args, **kwargs):
    try:
        from gevent import get_hub, monkey
    except ImportError:
        return fn(*args, **kwargs)
    if not monkey.is_module_patched('socket'):
        return fn(*args, **kwargs)
    return get_hub().threadpool.apply(fn, args, kwargs)
