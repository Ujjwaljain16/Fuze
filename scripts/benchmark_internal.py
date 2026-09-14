"""
Internal (non-HTTP) performance benchmarks for Fuze's hottest data-access
paths: the pgvector ANN query used by the recommendation pipeline, and the
Redis cache used on nearly every request.

Unlike scripts/locustfile.py (which measures the app over HTTP), this
exercises the actual SQL and cache calls directly -- useful for isolating
"is the query/index the bottleneck" from "is the web/auth layer the
bottleneck" when interpreting Locust results.

Produces a JSON results file (not just console prints) so numbers are
comparable across runs -- e.g. before/after an index change or a Postgres
tier upgrade.

Usage:
    DATABASE_URL=... REDIS_URL=... python scripts/benchmark_internal.py [--user-id N] [--iterations 50]
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
import redis

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'benchmark_results.json')


def percentile(sorted_values, pct):
    if not sorted_values:
        return None
    idx = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return sorted_values[idx]


def summarize(latencies_ms, label):
    latencies_ms = sorted(latencies_ms)
    result = {
        "label": label,
        "n": len(latencies_ms),
        "p50_ms": round(percentile(latencies_ms, 0.50), 2) if latencies_ms else None,
        "p95_ms": round(percentile(latencies_ms, 0.95), 2) if latencies_ms else None,
        "p99_ms": round(percentile(latencies_ms, 0.99), 2) if latencies_ms else None,
        "max_ms": round(latencies_ms[-1], 2) if latencies_ms else None,
        "min_ms": round(latencies_ms[0], 2) if latencies_ms else None,
    }
    print(f"--- {label} ---")
    if not latencies_ms:
        print("  No samples (see errors above)\n")
    else:
        print(f"  n={result['n']}  min={result['min_ms']}ms  p50={result['p50_ms']}ms  "
              f"p95={result['p95_ms']}ms  p99={result['p99_ms']}ms  max={result['max_ms']}ms\n")
    return result


def benchmark_ann_vector_search(app, db, user_id, iterations):
    """
    Benchmarks the ACTUAL production ANN query from
    backend/ml/recommendation/retrieval.py's fetch_ann_candidates() --
    cosine-distance ordering via the HNSW index on saved_content.embedding,
    scoped to a real user, exactly as the recommendation pipeline runs it.
    Falls back to a global (unscoped) query if the given user has no
    embedded content, so this still produces a number rather than nothing.
    """
    with app.app_context():
        import random
        query_vector = [random.uniform(-1, 1) for _ in range(384)]
        query_vector_str = '[' + ','.join(str(v) for v in query_vector) + ']'

        scoped_sql = text("""
            SELECT sc.id, sc.title, sc.url
            FROM saved_content sc
            WHERE sc.user_id = :user_id AND sc.embedding IS NOT NULL
            ORDER BY sc.embedding <=> CAST(:query_vector AS vector)
            LIMIT 20
        """)
        global_sql = text("""
            SELECT sc.id, sc.title, sc.url
            FROM saved_content sc
            WHERE sc.embedding IS NOT NULL
            ORDER BY sc.embedding <=> CAST(:query_vector AS vector)
            LIMIT 20
        """)

        try:
            rows = db.session.execute(scoped_sql, {"user_id": user_id, "query_vector": query_vector_str}).fetchall()
            sql, label = (scoped_sql, "ANN vector search (user-scoped, saved_content, HNSW cosine)") if rows else \
                         (global_sql, "ANN vector search (global fallback -- given user has no embedded content)")
            params = {"user_id": user_id, "query_vector": query_vector_str} if sql is scoped_sql else {"query_vector": query_vector_str}

            # Warm up
            db.session.execute(sql, params).fetchall()

            latencies = []
            for _ in range(iterations):
                start = time.perf_counter()
                db.session.execute(sql, params).fetchall()
                latencies.append((time.perf_counter() - start) * 1000)

            return summarize(latencies, label)
        except Exception as e:
            print(f"ANN vector search benchmark failed: {e}\n")
            return summarize([], "ANN vector search (failed)")


def benchmark_bookmark_list_query(app, db, user_id, iterations):
    """Benchmarks the actual paginated bookmark-list query pattern used by
    GET /api/bookmarks (backend/services/bookmark_service.py), the single
    most frequently hit endpoint in the Locust results."""
    with app.app_context():
        sql = text("""
            SELECT id, title, url, category, saved_at
            FROM saved_content
            WHERE user_id = :user_id
            ORDER BY saved_at DESC
            LIMIT 10 OFFSET 0
        """)
        try:
            db.session.execute(sql, {"user_id": user_id}).fetchall()
            latencies = []
            for _ in range(iterations):
                start = time.perf_counter()
                db.session.execute(sql, {"user_id": user_id}).fetchall()
                latencies.append((time.perf_counter() - start) * 1000)
            return summarize(latencies, "Bookmark list query (paginated, indexed on user_id+saved_at)")
        except Exception as e:
            print(f"Bookmark list query benchmark failed: {e}\n")
            return summarize([], "Bookmark list query (failed)")


def benchmark_embedding_generation(iterations):
    """Benchmarks utils.embedding_utils.get_embedding() end-to-end, forcing a
    genuine cache MISS on every call (real model/fallback inference, not a
    Redis lookup -- that case is already covered by the Redis benchmark
    below). Text includes a UUID per call: without this, re-running the
    script reuses the same "sample text (variant N)" strings from a PRIOR
    run still sitting in Redis, silently turning this into a cache-hit
    benchmark that under-reports real latency by 100x+ (caught during manual
    verification: fallback-hash-model cache hits measured ~1ms, while the
    real SentenceTransformer model on genuinely fresh text measured
    p50=~94ms -- the true, and much more consequential, number)."""
    from utils.embedding_utils import get_embedding, is_embedding_available
    import uuid

    sample_texts = [
        "Understanding async Python and event loops for high-throughput services",
        "PostgreSQL indexing strategies for large-scale production databases",
        "Scaling Redis connection pools under concurrent load",
        "Designing resilient background job processing with RQ and gevent",
        "A practical guide to gunicorn worker models and gevent concurrency",
    ]
    label = "Embedding generation" if is_embedding_available() else "Embedding generation (fallback hash model -- real model unavailable)"

    try:
        get_embedding(sample_texts[0])  # warm up model load (this one call may hit cache from a prior run -- harmless, excluded from measured samples)
        latencies = []
        for i in range(iterations):
            text_input = f"{sample_texts[i % len(sample_texts)]} [{uuid.uuid4()}]"
            start = time.perf_counter()
            get_embedding(text_input)
            latencies.append((time.perf_counter() - start) * 1000)
        return summarize(latencies, label)
    except Exception as e:
        print(f"Embedding generation benchmark failed: {e}\n")
        return summarize([], "Embedding generation (failed)")


def benchmark_redis_cache(redis_client, iterations):
    """Benchmarks realistic cache payload sizes: a serialized bookmark-list
    page (~2KB JSON), matching what GET /api/bookmarks actually caches."""
    key = "benchmark_test_key"
    payload = json.dumps([
        {"id": i, "title": f"Sample bookmark title number {i}", "url": f"https://example.com/{i}",
         "category": "technology", "saved_at": "2026-09-15T00:00:00Z"}
        for i in range(10)
    ]).encode('utf-8')  # ~1-2KB, matches a real 10-item bookmarks page

    try:
        write_latencies, read_latencies = [], []
        for i in range(iterations):
            start = time.perf_counter()
            redis_client.set(f"{key}_{i}", payload, ex=300)
            write_latencies.append((time.perf_counter() - start) * 1000)
        for i in range(iterations):
            start = time.perf_counter()
            redis_client.get(f"{key}_{i}")
            read_latencies.append((time.perf_counter() - start) * 1000)

        redis_client.delete(*[f"{key}_{i}" for i in range(iterations)])

        return {
            "write": summarize(write_latencies, "Redis SET (~1.5KB payload, realistic bookmarks-page size)"),
            "read": summarize(read_latencies, "Redis GET (~1.5KB payload, realistic bookmarks-page size)"),
        }
    except Exception as e:
        print(f"Redis benchmark failed: {e}\n")
        return {"write": summarize([], "Redis SET (failed)"), "read": summarize([], "Redis GET (failed)")}


def main():
    parser = argparse.ArgumentParser(description="Internal Fuze performance benchmarks")
    parser.add_argument("--user-id", type=int, default=1, help="User id to scope the ANN/bookmark-list benchmarks to (default: 1)")
    parser.add_argument("--iterations", type=int, default=50, help="Samples per benchmark (default: 50)")
    args = parser.parse_args()

    print("Initializing app...")
    from run_production import create_app
    from models import db
    app = create_app()

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis.from_url(redis_url)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": args.user_id,
        "iterations": args.iterations,
        "benchmarks": {},
    }

    results["benchmarks"]["ann_vector_search"] = benchmark_ann_vector_search(app, db, args.user_id, args.iterations)
    results["benchmarks"]["bookmark_list_query"] = benchmark_bookmark_list_query(app, db, args.user_id, args.iterations)
    with app.app_context():
        results["benchmarks"]["embedding_generation"] = benchmark_embedding_generation(args.iterations)
    results["benchmarks"]["redis_cache"] = benchmark_redis_cache(redis_client, args.iterations)

    with open(RESULTS_PATH, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
