"""Every cache that a write can make stale is the key that invalidation actually clears."""
from unittest.mock import patch

from core import cache_keys


def test_user_invalidation_clears_the_keys_readers_use(patch_redis_for_tests):
    from services.cache_invalidation_service import CacheInvalidationService
    fake = patch_redis_for_tests
    for key in (cache_keys.profile(5), cache_keys.dashboard_summary(5), cache_keys.dashboard_stats(5),
                cache_keys.bookmarks_page(5, 1, 20, '', ''), cache_keys.bookmarks_list(5),
                cache_keys.projects_page(5, 1, 10, True), cache_keys.profile(6)):
        fake.store[key] = {'cached': True}
    with patch('utils.content_version.bump_content_version'):
        assert CacheInvalidationService(fake).invalidate_user_cache(5)
    assert fake.store == {cache_keys.profile(6): {'cached': True}}  # only user 5's caches went


def test_delete_all_clears_the_import_dedupe_cache_immediately(client, auth_headers, test_user):
    with patch('services.cache_invalidation_service.cache_invalidator.invalidate_user_cache') as invalidate:
        response = client.delete('/api/bookmarks/all', headers=auth_headers)
    assert response.status_code == 200
    invalidate.assert_called_once_with(test_user['id'])


def test_invalidation_from_rq_jobs_runs_inline():
    """RQ work horses exit with os._exit(): background-thread invalidations never ran."""
    from services import cache_invalidation_service as cis
    ran = []
    with patch.object(cis, '_in_rq_job', return_value=True), \
         patch.object(cis._invalidation_executor, 'submit') as submit:
        cis._dispatch_async('t', lambda: ran.append(True))
    submit.assert_not_called()
    assert ran == [True]
