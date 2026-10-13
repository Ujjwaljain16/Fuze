# Things removed only because of Hugging Face — re-enable when moving hosts

Hugging Face paused the `fuze-backend` Space twice (Oct 2026) for browser-automation tooling
(`camoufox` in `requirements.txt`). Everything below was removed to satisfy HF's content policy,
not because it was broken. **If the backend moves to a host that allows it (the `deploy/` VM,
Fly.io, etc.), re-enable these for better content extraction.** Never add them back to the HF image.

## What was removed (see git history before the "strip browser automation" commit)

| Removed | Why it mattered |
|---|---|
| `scrapling[all]`, `camoufox[geoip]`, `playwright`, `mcp` pin in `requirements.txt` | JS-rendered page support; `mcp==1.24.0` was pinned to stop pip's resolver from backtracking |
| `backend/scrapers/fetchers/stealth_fetcher.py`, `dynamic_fetcher.py`, `browser_policy.py` | Tier 2/3 fetch strategies (STEALTH / DYNAMIC) |
| `backend/scrapers/scrapling_enhanced_scraper.py` | Main scrape entry used by bookmarks (Scrapling tiers + GitHub/LinkedIn handling) |
| Playwright paths in `enhanced_web_scraper.py`, `utils_web_scraper.py` | Site-specific rendering (LeetCode, GitHub, Medium, etc.) |
| `easy_linkedin_scraper.py` header/mobile-UA strategy rotation | Higher LinkedIn success rate |
| STEALTH / DYNAMIC escalation in `decision_engine.py` and `fetch_policy.py` (+ per-domain policies) | Auto-escalating to a browser when HTTP gets thin/blocked content |
| `camoufox fetch` + browser system libs (`libnss3`, `libgtk-3-0`, ...) in `Dockerfile` | Browser binary baked into the image |
| `DISABLE_BROWSER_FETCHERS` kill switch | Was added then removed along with the fetchers |
| Honest `FuzeBot/1.0` user agent in `http_fetcher.py` | Replaced a Chrome UA string; many sites block unknown bots, so revisit |

## What replaced them on HF

[`docs/CONTENT_ACQUISITION.md`](CONTENT_ACQUISITION.md) covers the browser-free tiers that
recover most of these pages for now: more official adapters (YouTube, Reddit, Medium, X), a
remote reader service (Jina Reader) for thin, JS-only and bot-blocked pages, and Wayback
Machine snapshots for gone pages. Browser tiers come back only on a host that allows them. Put
them between `HTTP` and `READER` in the strategy plan, so the third-party reader only gets
what our own browser could not render.

## How to restore

1. `git log --oneline -- backend/scrapers/scrapling_enhanced_scraper.py` and check out the files from the
   commit before the removal (`git checkout <sha>^ -- <paths>`), or revert that commit.
2. Re-add the dependencies to `requirements.txt` (keep `mcp==1.24.0` and `playwright==1.56.0` pinned).
3. Restore the `camoufox fetch` step + browser libs in the `Dockerfile` (verify with a real `docker build`).
4. Restore the STEALTH/DYNAMIC logic and tests in `decision_engine.py`, `fetch_policy.py`, `acquisition_engine.py`,
   `tests/test_content_acquisition_engine.py`.
5. Re-run the full backend suite and a live scrape of a JS-heavy page.

## Better than restoring: separate the browser worker

Keep the web app on whatever host, and run browser rendering as a separate RQ worker on infrastructure
that allows it (the same image with a different entrypoint, sharing `REDIS_URL` / `DATABASE_URL`). Also
consider Chrome-extension page capture and site APIs / `trafilatura` first.

## When the API host itself changes

The frontend's Content-Security-Policy (`frontend/vercel.json`) only lets the app call
`https://*.hf.space` (plus Supabase and Sentry). On a new API host, add its origin to `connect-src`
there, or every API call from the browser will be blocked. The backend's CORS allowlist
(`backend/utils/cors_utils.py`) needs no change: it lists the app's origins, not the API's.
