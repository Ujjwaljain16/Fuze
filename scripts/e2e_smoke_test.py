"""
End-to-end smoke test against a REAL running instance of the app (real
Postgres+pgvector, real Redis, real RQ workers actually processing jobs) --
not unit tests, not mocks. Exercises actual user journeys through the real
HTTP API to prove the app works before deploying anywhere.

Usage:
    python scripts/e2e_smoke_test.py --base-url http://localhost:5000
"""
import argparse
import sys
import time
import uuid

import requests

PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  [PASS] {name}")
    else:
        FAIL.append((name, detail))
        print(f"  [FAIL] {name} -- {detail}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    run_id = uuid.uuid4().hex[:8]
    username = f"e2e_{run_id}"
    email = f"e2e_{run_id}@example.com"
    password = "E2eTest!2026xyz"

    print(f"\n=== 1. Health checks ===")
    r = requests.get(f"{base}/api/health", timeout=10)
    check("GET /api/health returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")
    body = r.json() if r.status_code == 200 else {}
    check("health: database connected", body.get("database") == "connected", str(body))
    check("health: redis connected", body.get("redis", {}).get("connected") is True, str(body))

    r = requests.get(f"{base}/health/liveness", timeout=10)
    check("GET /health/liveness returns 200", r.status_code == 200)

    r = requests.get(f"{base}/health/readiness", timeout=10)
    check("GET /health/readiness returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")

    print(f"\n=== 2. Registration + login (real endpoints, not seeded) ===")
    r = requests.post(f"{base}/api/auth/register", json={
        "username": username, "email": email, "password": password
    }, timeout=15)
    check("register returns 201", r.status_code == 201, f"got {r.status_code}: {r.text[:500]}")

    r = requests.post(f"{base}/api/auth/login", json={
        "username": username, "password": password
    }, timeout=15)
    check("login returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:500]}")
    token = r.json().get("access_token") if r.status_code == 200 else None
    check("login returns access_token", bool(token))

    if not token:
        print("\nCannot continue without a valid token. Aborting.")
        print_summary()
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    print(f"\n=== 3. CORS allowlist behavior ===")
    r = requests.get(f"{base}/api/health", headers={"Origin": "https://itsfuze.vercel.app"}, timeout=10)
    check("legit origin gets echoed back", r.headers.get("Access-Control-Allow-Origin") == "https://itsfuze.vercel.app",
          f"header was {r.headers.get('Access-Control-Allow-Origin')!r}")
    r = requests.get(f"{base}/api/health", headers={"Origin": "https://evil-attacker.example"}, timeout=10)
    check("arbitrary origin is NOT echoed back", r.headers.get("Access-Control-Allow-Origin") is None,
          f"header was {r.headers.get('Access-Control-Allow-Origin')!r}")

    print(f"\n=== 4. Save a bookmark and wait for REAL background processing ===")
    bookmark_url = f"https://example.com/e2e-test-article-{run_id}"
    r = requests.post(f"{base}/api/bookmarks/quick-save", json={
        "url": bookmark_url, "title": "E2E Test Article"
    }, headers=headers, timeout=15)
    check("quick-save returns 2xx", 200 <= r.status_code < 300, f"got {r.status_code}: {r.text[:500]}")
    bookmark_id = None
    if r.status_code < 300:
        body = r.json()
        bookmark_id = (body.get("bookmark") or {}).get("id")
    check("quick-save returns a bookmark id", bookmark_id is not None, str(r.text[:300]))

    if bookmark_id:
        print(f"  Waiting for RQ worker to process bookmark {bookmark_id}...")
        processed = False
        final_status = None
        for _ in range(30):  # up to ~60s
            r = requests.get(f"{base}/api/bookmarks", headers=headers, params={"per_page": 50}, timeout=10)
            if r.status_code == 200:
                items = r.json().get("bookmarks", [])
                match = next((b for b in items if b.get("id") == bookmark_id), None)
                if match:
                    final_status = match
                    # has_content True once scraping/analysis completed
                    if match.get("has_content"):
                        processed = True
                        break
            time.sleep(2)
        check("background pipeline actually processed the bookmark (has_content)", processed,
              f"final observed state: {final_status}")

    print(f"\n=== 5. Search ===")
    r = requests.get(f"{base}/api/search/text", params={"q": "test", "limit": 5}, headers=headers, timeout=10)
    check("text search returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")

    r = requests.post(f"{base}/api/search/semantic", json={"query": "an article about testing", "limit": 5},
                       headers=headers, timeout=20)
    check("semantic search returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")

    print(f"\n=== 6. Dashboard ===")
    r = requests.get(f"{base}/api/dashboard/summary", headers=headers, timeout=15)
    check("dashboard summary returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")

    print(f"\n=== 7. Recommendations (the real, live endpoint) ===")
    r = requests.post(f"{base}/api/recommendations/unified-orchestrator", json={
        "title": "Testing backend reliability",
        "description": "Looking for content about automated testing",
        "technologies": "Python,Flask",
        "max_recommendations": 5,
    }, headers=headers, timeout=30)
    check("unified-orchestrator returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:500]}")

    print(f"\n=== 8. SSE ticket mint (auth-gated, real endpoint) ===")
    r = requests.post(f"{base}/api/realtime/stream-ticket", headers=headers, timeout=10)
    check("stream-ticket returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:300]}")
    ticket = r.json().get("ticket") if r.status_code == 200 else None
    check("stream-ticket returns a ticket", bool(ticket))

    if ticket:
        r = requests.get(f"{base}/api/realtime/stream", params={"ticket": ticket}, stream=True, timeout=5)
        check("SSE stream with valid ticket connects (200)", r.status_code == 200, f"got {r.status_code}")
        r.close()

    r = requests.get(f"{base}/api/realtime/stream", params={"ticket": "not-a-real-ticket"}, timeout=10)
    check("SSE stream with bogus ticket is rejected (401)", r.status_code == 401, f"got {r.status_code}")

    print(f"\n=== 9. Auth edge cases ===")
    r = requests.get(f"{base}/api/bookmarks", timeout=10)
    check("unauthenticated request to protected endpoint is rejected", r.status_code == 401, f"got {r.status_code}")

    r = requests.post(f"{base}/api/auth/login", json={"username": username, "password": "wrong-password"}, timeout=10)
    check("wrong password is rejected", r.status_code == 401, f"got {r.status_code}")

    print_summary()
    sys.exit(1 if FAIL else 0)


def print_summary():
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("\nFailures:")
        for name, detail in FAIL:
            print(f"  - {name}: {detail}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
