from dataclasses import asdict
from unittest.mock import MagicMock, patch

import ml.intent_analysis_engine as iae


def _intent(goal="build", h="abc"):
    return iae.UserIntent(
        primary_goal=goal, learning_stage="intermediate", project_type="api", urgency_level="medium",
        specific_technologies=["flask"], complexity_preference="moderate", time_constraint="deep_dive",
        focus_areas=[], context_hash=h,
    )


def test_cache_hit_returns_llm_intent_without_enqueue():
    cache = MagicMock()
    cache.get_cache.return_value = asdict(_intent("optimize"))
    with patch("utils.redis_utils.redis_cache", cache), \
         patch("services.task_queue.get_queue") as get_queue:
        intent = iae.get_intent_nonblocking("speed up my flask api", None)
    assert intent.primary_goal == "optimize"
    get_queue.assert_not_called()


def test_cache_miss_returns_fallback_and_enqueues_once():
    cache = MagicMock()
    cache.get_cache.return_value = None
    cache.redis_client.set.side_effect = [True, False]  # second call: job already pending
    queue = MagicMock()
    with patch("utils.redis_utils.redis_cache", cache), \
         patch("services.task_queue.get_queue", return_value=queue), \
         patch.object(iae, "analyze_user_intent") as llm:
        first = iae.get_intent_nonblocking("build a flask api", 7)
        second = iae.get_intent_nonblocking("build a flask api", 7)

    llm.assert_not_called()
    assert first.context_hash == "fallback" and second.context_hash == "fallback"
    assert first.primary_goal == "build"
    queue.enqueue.assert_called_once()
    assert queue.enqueue.call_args.args[:3] == (iae.PRECOMPUTE_JOB_PATH, "build a flask api", 7)


def test_redis_down_still_returns_fallback():
    cache = MagicMock()
    cache.get_cache.side_effect = RuntimeError("redis down")
    with patch("utils.redis_utils.redis_cache", cache):
        intent = iae.get_intent_nonblocking("learn python", None)
    assert intent.context_hash == "fallback"


def test_precompute_job_caches_successful_intent_and_clears_pending():
    cache = MagicMock()
    with patch("utils.redis_utils.redis_cache", cache), \
         patch.object(iae, "analyze_user_intent", return_value=_intent("build", "h1")):
        assert iae.precompute_intent_job("build a flask api", 7) == "build"
    key = cache.set_cache.call_args.args[0]
    assert key.startswith(iae.INTENT_CACHE_PREFIX)
    cache.redis_client.delete.assert_called_once()


def test_precompute_job_does_not_cache_failed_analysis():
    cache = MagicMock()
    with patch("utils.redis_utils.redis_cache", cache), \
         patch.object(iae, "analyze_user_intent", return_value=_intent("learn", "")):
        iae.precompute_intent_job("x", None)
    cache.set_cache.assert_not_called()
