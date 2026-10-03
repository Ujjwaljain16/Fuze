import os


def browser_fetchers_disabled() -> bool:
    """True when headless-browser fetch tiers (Camoufox/Playwright via Scrapling) must not run.

    Set DISABLE_BROWSER_FETCHERS=true on hosts whose policies forbid browser
    automation tooling; scraping then uses plain HTTP fetching only.
    """
    return os.environ.get("DISABLE_BROWSER_FETCHERS", "").strip().lower() in ("1", "true", "yes")
