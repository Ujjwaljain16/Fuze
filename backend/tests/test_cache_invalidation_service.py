import pytest
from unittest.mock import MagicMock
from services.cache_invalidation_service import CacheInvalidationService


@pytest.mark.unit
def test_cache_invalidation_targeted_keys():
    mock_redis = MagicMock()
    service = CacheInvalidationService(redis_cache=mock_redis)

    # 1. User cache invalidation deletes targeted keys
    res = service.invalidate_user_cache(user_id=42)
    assert res is True
    mock_redis.invalidate_user_bookmarks.assert_called_once_with(42)
    mock_redis.invalidate_recommendation_cache.assert_called_once_with(42)
    assert mock_redis.delete_cache.call_count >= 4

    # Verify NO delete_keys_pattern wildcard calls were made!
    assert not hasattr(mock_redis, 'delete_keys_pattern') or mock_redis.delete_keys_pattern.call_count == 0


@pytest.mark.unit
def test_invalidate_all_cache_confirmation_guard():
    mock_redis = MagicMock()
    service = CacheInvalidationService(redis_cache=mock_redis)

    # Calling without confirm=True is blocked
    res_blocked = service.invalidate_all_cache()
    assert res_blocked is False
    assert mock_redis.invalidate_all_recommendations.call_count == 0

    # Calling with confirm=True executes
    res_confirmed = service.invalidate_all_cache(confirm=True)
    assert res_confirmed is True
    assert mock_redis.invalidate_all_recommendations.call_count == 1


@pytest.mark.unit
def test_cache_invalidation_hooks():
    mock_redis = MagicMock()
    service = CacheInvalidationService(redis_cache=mock_redis)

    assert service.after_content_save(content_id=1, user_id=2) is True
    assert service.after_project_save(project_id=10, user_id=2) is True
    assert service.after_task_save(task_id=100, user_id=2) is True
