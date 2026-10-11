from unittest.mock import MagicMock, patch

from utils.content_version import bump_content_version, get_content_version


def test_bump_then_read():
    store = {}
    client = MagicMock()
    client.incr.side_effect = lambda k: store.__setitem__(k, store.get(k, 0) + 1)
    client.get.side_effect = lambda k: store.get(k)
    cache = MagicMock(redis_client=client)
    with patch("utils.redis_utils.redis_cache", cache):
        assert get_content_version(5) == 0
        bump_content_version(5)
        bump_content_version(5)
        assert get_content_version(5) == 2
        assert get_content_version(6) == 0


def test_unreadable_version_never_matches_a_stored_key():
    client = MagicMock()
    client.get.side_effect = RuntimeError("redis down")
    with patch("utils.redis_utils.redis_cache", MagicMock(redis_client=client)):
        assert get_content_version(5) == -1


def test_user_cache_invalidation_bumps_version():
    from services.cache_invalidation_service import cache_invalidator
    with patch("utils.content_version.bump_content_version") as bump:
        cache_invalidator.invalidate_user_cache(42)
    bump.assert_called_once_with(42)
