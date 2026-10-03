import pytest

from scrapers.fetchers import dynamic_fetcher, stealth_fetcher
from scrapers.fetchers.browser_policy import browser_fetchers_disabled


@pytest.mark.parametrize("value,expected", [("true", True), ("1", True), ("YES", True), ("false", False), ("", False)])
def test_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("DISABLE_BROWSER_FETCHERS", value)
    assert browser_fetchers_disabled() is expected


@pytest.mark.parametrize("module,attr,avail", [
    (stealth_fetcher, "StealthyFetcher", "SCRAPLING_STEALTH_AVAILABLE"),
    (dynamic_fetcher, "DynamicFetcherClass", "SCRAPLING_DYNAMIC_AVAILABLE"),
])
def test_browser_never_launched_when_disabled(monkeypatch, module, attr, avail):
    launched = []

    class Boom:
        def fetch(self, *a, **k):
            launched.append(1)
            raise AssertionError("browser fetcher must not run when disabled")

    monkeypatch.setattr(module, attr, Boom)
    monkeypatch.setattr(module, avail, True)
    monkeypatch.setenv("DISABLE_BROWSER_FETCHERS", "true")

    class Result:
        http_status = 200
        final_url = "https://example.com"
        headers = {}
        raw_content = b"ok"

        class fetch_metadata:
            redirected = False
            redirect_chain = []
            fetch_latency_ms = 1

    import scrapers.fetchers.http_fetcher as http_fetcher
    monkeypatch.setattr(http_fetcher.HTTPFetcher, "fetch", lambda self, url: Result)
    monkeypatch.setattr(stealth_fetcher, "StealthFetcher", stealth_fetcher.StealthFetcher)

    fetcher_cls = module.StealthFetcher if module is stealth_fetcher else module.DynamicFetcher
    out = fetcher_cls().fetch("https://example.com")

    assert launched == []
    assert out.raw_content == b"ok"
