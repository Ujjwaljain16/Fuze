"""
Load test for Fuze's heavy, authenticated endpoints -- exercises the same
gunicorn+gevent single-worker concurrency model used in production
(supervisord.conf: --workers 1 --worker-class gevent).

Uses pre-minted JWTs from scripts/seed_loadtest_data.py (scripts/loadtest_tokens.json)
instead of hitting /api/login, since login is rate-limited per-IP (5 per 15
minutes) and every Locust user in a local test shares one source IP -- calling
/api/login here would just measure the rate limiter, not real app throughput.

Usage:
    python scripts/seed_loadtest_data.py   # once, against the target DB
    locust -f scripts/locustfile.py --host http://localhost:7860
"""
import json
import os
import random

from locust import HttpUser, task, between

TOKENS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loadtest_tokens.json')
with open(TOKENS_PATH) as f:
    _TOKENS = json.load(f)

SEARCH_TERMS = ["python", "database", "scaling", "architecture", "redis", "engineering"]


class FuzeAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        account = random.choice(_TOKENS)
        self.user_id = account["user_id"]
        self.headers = {"Authorization": f"Bearer {account['token']}"}

    @task(5)
    def list_bookmarks(self):
        page = random.randint(1, 3)
        self.client.get(
            f"/api/bookmarks?page={page}&per_page=10",
            headers=self.headers,
            name="/api/bookmarks [list]",
        )

    @task(3)
    def dashboard_summary(self):
        self.client.get(
            "/api/dashboard/summary",
            headers=self.headers,
            name="/api/dashboard/summary",
        )

    @task(3)
    def text_search(self):
        term = random.choice(SEARCH_TERMS)
        self.client.get(
            f"/api/search/text?q={term}&limit=10",
            headers=self.headers,
            name="/api/search/text",
        )

    @task(2)
    def semantic_search(self):
        term = random.choice(SEARCH_TERMS)
        self.client.post(
            "/api/search/semantic",
            json={"query": f"how to think about {term}", "limit": 10},
            headers=self.headers,
            name="/api/search/semantic",
        )

    # NOTE: /api/recommendations/unified, /unified-project/<id>, and
    # /project/<id> are excluded here -- discovered via this load test to be
    # permanently broken (100% failure) because blueprints/recommendations.py's
    # get_unified_engine() imports a top-level `unified_recommendation_engine`
    # module that does not exist anywhere in the codebase (it was superseded
    # by ml/unified_recommendation_orchestrator.py, used correctly by the only
    # endpoint the frontend actually calls, /unified-orchestrator). Confirmed
    # dead/unused code via grep across frontend/ and BookmarkExtension/ -- see
    # gaps.md. Left out of this run so they don't pollute throughput numbers
    # with fast-failing 500s that aren't representative of real load.

    @task(1)
    def unified_orchestrator_recommendations(self):
        # The heaviest REAL endpoint (the one the frontend actually calls):
        # embeds the request text and scores it against a user's content.
        self.client.post(
            "/api/recommendations/unified-orchestrator",
            json={
                "title": "Improving backend scalability",
                "description": "Looking for content on caching, connection pooling, and gevent concurrency",
                "technologies": "Python,Flask,Postgres,Redis",
                "user_interests": "backend engineering",
                "max_recommendations": 10,
            },
            headers=self.headers,
            name="/api/recommendations/unified-orchestrator",
        )

    @task(4)
    def health_check(self):
        self.client.get("/api/health", name="/api/health")
