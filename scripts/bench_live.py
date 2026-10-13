"""Latency benchmark for a LIVE Fuze deployment, run by its owner with their own account.

    python scripts/bench_live.py                       # the Hugging Face Space
    python scripts/bench_live.py --base https://my.host --samples 20 --ask 2

What it does (about 600 requests in 6 to 8 minutes, paced under the app's own rate limits):
  1. network floor: GET /health/liveness (touches no database), so everything else can be read as
     "what the application adds on top of the network"
  2. sequential latency, p50/p95 per endpoint: semantic search, keyword search, bookmark list,
     dashboard summary
  3. Ask your bookmarks (a few calls: each uses the LLM provider and costs a fraction of a cent)
  4. a short, gentle concurrency ramp on a read endpoint (1, 2, 4, 8 clients), stopped at the first
     sign of errors or rate limiting

Your password is asked for at the prompt (never as an argument), used once for POST /api/auth/login
and then dropped; the access token stays in memory. Neither is printed or written anywhere. Results
go to docs/perf/live-bench-<UTC time>.json. Limits to know: login is 5 per 15 minutes per IP,
semantic search 30 per minute, Ask 10 per minute and 100 per day; this script stays well under them.
"""

import argparse
import datetime
import getpass
import json
import os
import re
import statistics
import sys
import threading
import time

import requests

DEFAULT_BASE = "https://ujjwaljain16-fuze-backend.hf.space"
USER_AGENT = "FuzeBench/1.0 (owner-run latency check)"
QUERIES = ["docker containers", "react hooks", "system design interview", "how does jwt authentication work",
           "learn rust async", "sql joins", "kubernetes", "machine learning datasets", "python decorators",
           "git rebase vs merge", "caching strategies", "rest api design", "css grid layout", "linux commands",
           "data structures and algorithms"]
QUESTIONS = ["What should I read first to learn Docker?", "Which of my bookmarks cover system design?",
             "What do my saved pages say about authentication?"]


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round((p / 100) * (len(values) - 1))))]


def summarize(ms):
    return {"n": len(ms), "min": round(min(ms)), "p50": round(statistics.median(ms)),
            "p95": round(percentile(ms, 95)), "max": round(max(ms)),
            "mean": round(statistics.fmean(ms))}


class Bench:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.session.headers["X-Server-Timing"] = "1"  # ask the server where each request's time went
        self.rate_limited = 0
        self.errors = 0
        self.last_server = {}

    @staticmethod
    def parse_server_timing(header):
        """'total;dur=2154.0, embed;dur=640.2, db;dur=1083.5, dbn;desc="5 statements"' -> numbers."""
        found = {name: float(value) for name, value in re.findall(r"(\w+);dur=([\d.]+)", header or "")}
        statements = re.search(r'dbn;desc="(\d+) statements"', header or "")
        if statements:
            found["statements"] = float(statements.group(1))
        return found

    def call(self, method, path, **kwargs):
        """One timed request; returns (milliseconds, status). Honors Retry-After and gives up after 3 429s."""
        start = time.time()
        try:
            response = self.session.request(method, self.base + path, timeout=60, **kwargs)
        except requests.RequestException:
            self.errors += 1
            return None, 0
        elapsed = (time.time() - start) * 1000
        if response.status_code == 429:
            self.rate_limited += 1
            if self.rate_limited >= 3:
                sys.exit("Stopped: the server rate-limited this run 3 times. Wait a few minutes and retry.")
            time.sleep(min(float(response.headers.get("Retry-After", "30") or 30), 90))
            return None, 429
        if response.status_code >= 500:
            self.errors += 1
        self.last_server = self.parse_server_timing(response.headers.get("Server-Timing"))
        return elapsed, response.status_code

    def measure(self, label, method, path, samples, pace, make_kwargs=None):
        times, server = [], []
        for i in range(samples):
            kwargs = make_kwargs(i) if make_kwargs else {}
            ms, status = self.call(method, path(i) if callable(path) else path, **kwargs)
            if ms is not None and status == 200:
                times.append(ms)
                if self.last_server:
                    server.append(self.last_server)
            time.sleep(pace)
        if not times:
            return None
        stats = summarize(times)
        if server:  # median of each part the server reported, across the samples
            stats["server"] = {key: round(statistics.median(s[key] for s in server if key in s), 1)
                               for key in ("total", "embed", "db", "statements") if any(key in s for s in server)}
        return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--samples", type=int, default=30, help="requests per endpoint in the sequential phase")
    parser.add_argument("--ask", type=int, default=3, help="Ask calls (0 skips; each costs a fraction of a cent)")
    parser.add_argument("--ramp", default="1,2,4,8", help="client counts for the concurrency ramp")
    parser.add_argument("--no-ramp", action="store_true",
                        help="skip the concurrency ramp (the app's default limit is 50 requests/minute per client)")
    parser.add_argument("--step-seconds", type=int, default=10)
    args = parser.parse_args()

    email = os.environ.get("FUZE_BENCH_EMAIL") or input("Fuze account email: ").strip()
    password = getpass.getpass("Password (not shown, not saved): ")
    bench = Bench(args.base)

    # --- sign in once; keep only the access token, in memory
    for attempt in range(1, 6):   # a network hiccup (a failed DNS lookup, say) should not end the run
        try:
            response = bench.session.post(bench.base + "/api/auth/login",
                                          json={"email": email, "password": password}, timeout=60)
            break
        except requests.ConnectionError as error:
            if attempt == 5:
                sys.exit(f"Could not reach {bench.base} after 5 tries: {type(error).__name__}. Check your connection and retry.")
            print(f"Connection failed (try {attempt} of 5), retrying...")
            time.sleep(3)
    del password
    if response.status_code != 200:
        sys.exit(f"Sign-in failed (HTTP {response.status_code}). Nothing else was sent.")
    token = response.json().get("access_token")
    if not token:
        sys.exit("The server returned no access token.")
    bench.session.headers["Authorization"] = f"Bearer {token}"
    del token, response
    print(f"Signed in to {bench.base}. Benchmarking...\n")

    results = {"base": bench.base, "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "samples_per_endpoint": args.samples, "endpoints": {}}

    def record(label, stats):
        results["endpoints"][label] = stats
        if stats:
            print(f"  {label:<42} p50 {stats['p50']:>5} ms   p95 {stats['p95']:>5} ms   (n={stats['n']}, max {stats['max']} ms)")
            server = stats.get("server")
            if server and "db" in server:  # where the server says the time went (medians)
                parts = [f"total {server.get('total', 0):.0f}"]
                if "embed" in server:
                    parts.append(f"embedding {server['embed']:.0f}")
                parts.append(f"database {server['db']:.0f} ({server.get('statements', 0):.0f} statements)")
                other = server.get("total", 0) - server.get("embed", 0) - server["db"]
                parts.append(f"other {other:.0f}")
                print(f"  {'':<42}   server-side ms: " + ", ".join(parts))
        else:
            print(f"  {label:<42} no successful samples")

    print("1. Network floor and sequential latency")
    for _ in range(3):  # warm-up: TLS, connection pool, caches
        bench.call("GET", "/health/liveness")
    record("network floor: GET /health/liveness", bench.measure("floor", "GET", "/health/liveness", args.samples, 0.4))
    record("GET /api/bookmarks?per_page=20", bench.measure(
        "list", "GET", lambda i: f"/api/bookmarks?page=1&per_page=20&search={QUERIES[i % len(QUERIES)].split()[0] if i % 3 == 0 else ''}",
        args.samples, 0.5))
    record("GET /api/dashboard/summary", bench.measure("dash", "GET", "/api/dashboard/summary", args.samples, 0.5))
    record("GET /api/search/text (keyword)", bench.measure(
        "text", "GET", lambda i: "/api/search/text?q=" + requests.utils.quote(QUERIES[i % len(QUERIES)]) + "&limit=10",
        args.samples, 0.5))
    # semantic search is limited to 30/minute: one request every 2.3 s stays under it
    record("POST /api/search/semantic", bench.measure(
        "semantic", "POST", "/api/search/semantic", args.samples, 2.3,
        make_kwargs=lambda i: {"json": {"query": QUERIES[i % len(QUERIES)], "limit": 10}}))

    if args.ask > 0:
        print("\n2. Ask your bookmarks (uses the LLM provider)")
        record("POST /api/ask", bench.measure(
            "ask", "POST", "/api/ask", args.ask, 8.0,
            make_kwargs=lambda i: {"json": {"question": QUESTIONS[i % len(QUESTIONS)]}}))

    if args.ramp and not args.no_ramp:
        print("\n3. Concurrency ramp on GET /api/bookmarks (gentle: stops at the first errors)")
        results["ramp"] = []
        for clients in [int(x) for x in args.ramp.split(",") if x.strip()]:
            times, errors, lock = [], [0], threading.Lock()
            stop = time.time() + args.step_seconds

            def worker():
                while time.time() < stop:
                    ms, status = bench.call("GET", "/api/bookmarks?page=1&per_page=20")
                    with lock:
                        if ms is not None and status == 200:
                            times.append(ms)
                        else:
                            errors[0] += 1

            threads = [threading.Thread(target=worker) for _ in range(clients)]
            began = time.time()
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            span = time.time() - began
            step = {"clients": clients, "requests": len(times), "errors": errors[0],
                    "req_per_sec": round(len(times) / span, 1), **(summarize(times) if times else {})}
            results["ramp"].append(step)
            print(f"  {clients:>2} clients: {step['req_per_sec']:>5} req/s   p50 {step.get('p50', '-'):>5} ms   "
                  f"p95 {step.get('p95', '-'):>5} ms   errors {errors[0]}")
            if errors[0] > 0 and errors[0] / max(1, errors[0] + len(times)) > 0.02:
                print("  stopping the ramp: errors above 2%")
                break
            time.sleep(3)

    results["rate_limited"] = bench.rate_limited
    results["errors"] = bench.errors
    results["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    floor = (results["endpoints"].get("network floor: GET /health/liveness") or {}).get("p50")
    if floor:
        print(f"\nNetwork floor (no database) p50 = {floor} ms. Read each p50 above minus {floor} ms for what the app itself adds.")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "perf")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = os.path.join(out_dir, f"live-bench-{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {os.path.relpath(json_path)}")


if __name__ == "__main__":
    main()
