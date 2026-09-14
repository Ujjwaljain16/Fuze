"""
Seed realistic data for a local load test (Phase 3 of the production-readiness
pass) directly against the app's models -- bypasses the /api/register and
/api/login endpoints entirely (both are rate-limited per-IP, and every Locust
user would otherwise share one local IP, exhausting the login limit after 5
attempts and skewing results towards 401s instead of measuring real app
throughput).

Mints a real access token per user with the app's own JWT config, so tokens
are valid without ever calling /api/login.

Usage:
    DATABASE_URL=... SECRET_KEY=... JWT_SECRET_KEY=... python scripts/seed_loadtest_data.py
"""
import os
import sys
import json
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backend'))

from run_production import create_app
from models import db, User, SavedContent, Project
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

NUM_USERS = 10
BOOKMARKS_PER_USER = 40

SAMPLE_TITLES = [
    "Understanding Async Python", "React Server Components Explained",
    "PostgreSQL Indexing Strategies", "The Case for Event-Driven Architecture",
    "Introduction to Vector Databases", "Scaling Redis at High Throughput",
    "A Deep Dive into Gunicorn Workers", "Building Resilient Web Scrapers",
    "JWT Refresh Token Rotation Patterns", "Designing for Horizontal Scale",
]
SAMPLE_TEXT = (
    "This article discusses production engineering practices, covering topics "
    "such as caching strategies, database connection pooling, background job "
    "processing, and observability. It walks through real-world tradeoffs "
    "encountered when scaling a web application to handle concurrent traffic, "
    "including lessons learned from incidents and performance regressions."
) * 3


def seed():
    app = create_app('production' if os.environ.get('FLASK_ENV') == 'production' else 'development')
    with app.app_context():
        db.create_all()

        users = []
        tokens = []
        for i in range(NUM_USERS):
            username = f"loadtest_user_{i}"
            email = f"loadtest_user_{i}@example.com"
            existing = User.query.filter_by(username=username).first()
            if existing:
                user = existing
            else:
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash("LoadTest!2026xyz"),
                )
                db.session.add(user)
                db.session.flush()

                for j in range(BOOKMARKS_PER_USER):
                    title = random.choice(SAMPLE_TITLES) + f" #{j}"
                    fake_embedding = [random.uniform(-1, 1) for _ in range(384)]
                    bm = SavedContent(
                        user_id=user.id,
                        url=f"https://example.com/article/{i}-{j}",
                        title=title,
                        source="manual",
                        extracted_text=SAMPLE_TEXT,
                        embedding=fake_embedding,
                        tags="engineering,backend",
                        category="technology",
                        quality_score=random.randint(5, 10),
                        analysis_status='SUCCESS',
                        embedding_status='SUCCESS',
                        scrape_status='SUCCESS',
                    )
                    db.session.add(bm)

                project = Project(
                    user_id=user.id,
                    title="Backend Scaling Project",
                    description="Improving throughput and reliability of the API layer",
                    technologies="Python,Flask,Postgres,Redis",
                )
                db.session.add(project)

                db.session.commit()

            users.append(user)
            token = create_access_token(identity=str(user.id), additional_claims={'family_id': 'loadtest'})
            tokens.append({"user_id": user.id, "username": user.username, "token": token})

        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loadtest_tokens.json')
        with open(out_path, 'w') as f:
            json.dump(tokens, f, indent=2)

        print(f"Seeded {len(users)} users x {BOOKMARKS_PER_USER} bookmarks each.")
        print(f"Tokens written to {out_path}")


if __name__ == '__main__':
    seed()
