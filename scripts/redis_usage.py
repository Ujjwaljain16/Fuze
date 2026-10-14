#!/usr/bin/env python3
"""How fast is Redis being used, and what does that come to per month?

    python scripts/redis_usage.py                 # 60-second sample of the server REDIS_URL points at
    python scripts/redis_usage.py --seconds 600   # a longer sample is steadier
    python scripts/redis_usage.py --limit 500000  # Upstash free plan (the default)

READ ONLY. It reads the server's own counters (INFO) twice and reports the difference, so it sees every
client: the web app, the workers, your laptop. It costs about 5 commands.

Upstash's free plan stops all commands for the rest of the month once 500,000 are used, so the number
to watch is the projection. A quiet system (no one using the app) should project under about 100,000 a
month; if it projects higher, something is polling. The by-command table says what.
"""

import argparse
import os
import sys
import time

DAYS_PER_MONTH = 30


def snapshot(client):
    info = client.info()
    stats = client.info("commandstats")
    return info["total_commands_processed"], {
        name.replace("cmdstat_", ""): value["calls"] for name, value in stats.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--limit", type=int, default=500_000, help="commands per month on your plan")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    url = os.environ.get("REDIS_URL")
    if not url:
        sys.exit("REDIS_URL is not set.")

    import redis
    client = redis.from_url(url, socket_timeout=30, socket_connect_timeout=30)
    start_total, start_calls = snapshot(client)
    print(f"Sampling for {args.seconds} s...")
    time.sleep(args.seconds)
    end_total, end_calls = snapshot(client)

    # The two snapshots cost a few commands themselves; they are subtracted so an idle server reads ~0.
    used = max(0, end_total - start_total - 4)
    per_day = used / args.seconds * 86_400
    per_month = per_day * DAYS_PER_MONTH
    print(f"\n{used} commands in {args.seconds} s -> {per_day:,.0f} a day -> {per_month:,.0f} a month "
          f"({per_month / args.limit:.0%} of {args.limit:,})")
    rows = sorted(((end_calls.get(name, 0) - start_calls.get(name, 0), name) for name in end_calls), reverse=True)
    print("\nBy command in this window (the sampler's own INFO calls excluded):")
    for count, name in rows[:10]:
        if name == "info":
            count = max(0, count - 4)
        if count:
            print(f"  {count:>8}  {name}")
    if per_month > args.limit * 0.5:
        print("\nOver half the monthly allowance at this rate. Look at the top command above: "
              "blpop/zrangebyscore/expire/get repeating means something is polling.")


if __name__ == "__main__":
    main()
