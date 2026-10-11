"""Server-side fetches of user URLs must never reach internal addresses."""
import socket
from unittest.mock import MagicMock, patch

import pytest

from scrapers import safe_http
from scrapers.safe_http import UnsafeURLError, is_public_ip, safe_get


def _addrinfo(*ips):
    return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 0)) for ip in ips]


@pytest.mark.parametrize('ip,public', [
    ('93.184.216.34', True), ('127.0.0.1', False), ('10.1.2.3', False), ('169.254.169.254', False),
    ('100.64.0.1', False), ('::1', False), ('::ffff:127.0.0.1', False), ('fd00::1', False), ('224.0.0.1', False),
    ('2606:4700::1111', True),
])
def test_address_policy(ip, public):
    assert is_public_ip(ip) is public


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'gopher://x/', 'http://user:pw@example.com/', 'http:///nohost'])
def test_rejects_disallowed_urls(url):
    with pytest.raises(UnsafeURLError):
        safe_get(url)


def test_host_with_any_internal_address_is_rejected():
    with patch('scrapers.safe_http.socket.getaddrinfo', return_value=_addrinfo('93.184.216.34', '10.0.0.5')), \
         patch.object(safe_http, '_fetch_once') as fetch:
        with pytest.raises(UnsafeURLError):
            safe_get('http://split-horizon.example/')
    fetch.assert_not_called()


def test_connects_to_the_address_that_was_checked():
    """DNS rebinding: a second lookup returning 127.0.0.1 must not be used for the connection."""
    answers = iter([_addrinfo('93.184.216.34'), _addrinfo('127.0.0.1')])
    with patch('scrapers.safe_http.socket.getaddrinfo', side_effect=lambda *a, **k: next(answers)), \
         patch.object(safe_http, '_fetch_once', return_value=(200, {}, b'ok', False)) as fetch:
        safe_get('http://rebind.example/')
    assert fetch.call_args.args[1] == '93.184.216.34'


def test_redirect_to_internal_address_is_blocked():
    def resolve(host, *a, **k):
        return _addrinfo('93.184.216.34' if host == 'public.example' else '127.0.0.1')
    with patch('scrapers.safe_http.socket.getaddrinfo', side_effect=resolve), \
         patch.object(safe_http, '_fetch_once', return_value=(302, {'Location': 'http://internal.example/admin'}, b'', False)):
        with pytest.raises(UnsafeURLError):
            safe_get('http://public.example/')


def test_body_is_capped():
    resp = MagicMock(status_code=200, headers={})
    resp.iter_content.return_value = iter([b'x' * 600, b'y' * 600, b'z' * 600])
    resp.__enter__ = lambda s: s
    resp.__exit__ = lambda *a: None
    with patch('scrapers.safe_http.socket.getaddrinfo', return_value=_addrinfo('93.184.216.34')), \
         patch('scrapers.safe_http.requests.Session.get', return_value=resp):
        result = safe_get('http://big.example/', max_bytes=1000)
    assert len(result.content) == 1000 and result.truncated


def test_robots_txt_is_not_fetched_for_unsafe_hosts():
    from scrapers.acquisition_engine import ContentAcquisitionEngine
    engine = ContentAcquisitionEngine()
    with patch.object(engine.robots_manager, 'can_fetch') as can_fetch, \
         patch('scrapers.rate_limiter.DomainRateLimiter.acquire', return_value=(True, 0.0)):
        doc = engine.acquire_and_normalize('http://169.254.169.254/latest/meta-data/')
    can_fetch.assert_not_called()
    assert doc.markdown_content == ''
