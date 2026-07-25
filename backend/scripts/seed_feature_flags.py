#!/usr/bin/env python3
"""
scripts/seed_feature_flags.py
==============================
One-time seed script: reads current env-var values and writes them as
feature flag records to Redis. Run this once after deploying feature_flags.py
to ensure existing behaviour is preserved as the default state.

Safe to re-run — uses HSET which is idempotent (updates, does not reset pct
if the flag already exists in Redis, unless --force is passed).

Usage:
    cd backend
    python scripts/seed_feature_flags.py
    python scripts/seed_feature_flags.py --force      # overwrite existing flags
    python scripts/seed_feature_flags.py --dry-run    # print without writing
"""

import os
import sys
import argparse

# Ensure backend/ is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from core.feature_flags import _ENV_DEFAULTS, _get_redis, _REDIS_KEY_PREFIX
import time


def seed(force: bool = False, dry_run: bool = False) -> None:
    r = _get_redis()
    if r is None and not dry_run:
        print("[ERROR] Redis unavailable. Cannot seed feature flags.")
        sys.exit(1)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Seeding {len(_ENV_DEFAULTS)} feature flags...\n")

    results = {"seeded": [], "skipped": [], "failed": []}

    for flag_name, default_enabled in _ENV_DEFAULTS.items():
        redis_key = f"{_REDIS_KEY_PREFIX}{flag_name}"

        if dry_run:
            print(f"  [DRY RUN] Would seed: {flag_name!r:30s} enabled={default_enabled}  pct=100")
            results["seeded"].append(flag_name)
            continue

        try:
            existing = r.hgetall(redis_key)

            if existing and not force:
                print(f"  [SKIP]  {flag_name!r:30s} already exists in Redis (use --force to overwrite)")
                results["skipped"].append(flag_name)
                continue

            r.hset(redis_key, mapping={
                "enabled": "1" if default_enabled else "0",
                "pct": "100",
                "description": f"Seeded from env-var default (ENABLE_*). Updated by seed_feature_flags.py.",
                "updated_at": str(time.time()),
            })

            status = "[FORCE]" if (existing and force) else "[SEED] "
            print(f"  {status} {flag_name!r:30s} enabled={default_enabled}  pct=100")
            results["seeded"].append(flag_name)

        except Exception as exc:
            print(f"  [ERROR] {flag_name!r}: {exc}")
            results["failed"].append(flag_name)

    print(f"\nDone. Seeded: {len(results['seeded'])}  "
          f"Skipped: {len(results['skipped'])}  "
          f"Failed: {len(results['failed'])}")

    if results["failed"]:
        print(f"\nFailed flags: {results['failed']}")
        sys.exit(1)

    print("\nVerification — reading back from Redis:")
    if not dry_run and r:
        for flag_name in _ENV_DEFAULTS:
            redis_key = f"{_REDIS_KEY_PREFIX}{flag_name}"
            try:
                data = r.hgetall(redis_key)
                enabled = data.get(b"enabled", b"?").decode()
                pct = data.get(b"pct", b"?").decode()
                print(f"  {flag_name!r:30s} enabled={enabled}  pct={pct}")
            except Exception as exc:
                print(f"  {flag_name!r:30s} [READ ERROR] {exc}")


def main():
    parser = argparse.ArgumentParser(description="Seed Redis feature flags from env-var defaults")
    parser.add_argument("--force", action="store_true", help="Overwrite existing flags in Redis")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing to Redis")
    args = parser.parse_args()
    seed(force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
