#!/usr/bin/env python3
"""
Invalidate cached recommendation/search results.

Results are cached under keys that include a per-user content version, so bumping
the version makes every cached result for that user unreachable at once.

Usage (from backend/):
    python scripts/utils/clear_recommendation_cache.py 42      # one user
    python scripts/utils/clear_recommendation_cache.py --all   # every user
"""

import argparse
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()


def main():
    ap = argparse.ArgumentParser(description="Invalidate cached recommendations")
    ap.add_argument("user_id", nargs="?", type=int)
    ap.add_argument("--all", action="store_true", help="invalidate for every user")
    args = ap.parse_args()
    if not args.user_id and not args.all:
        ap.error("give a user_id or --all")

    from utils.content_version import bump_content_version

    if args.user_id:
        bump_content_version(args.user_id)
        print(f"Invalidated cached results for user {args.user_id}")
        return

    from sqlalchemy import text
    from run_production import create_app
    from models import db
    with create_app().app_context():
        user_ids = [r[0] for r in db.session.execute(text("SELECT id FROM users"))]
    for uid in user_ids:
        bump_content_version(uid)
    print(f"Invalidated cached results for {len(user_ids)} users")


if __name__ == "__main__":
    main()
