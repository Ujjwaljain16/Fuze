import json
from unittest.mock import MagicMock, patch

import numpy as np

from ml.intent_engine import intent as intent_mod
from ml.intent_engine.intent import IntentContext, compose_intent_text, parse_intent, resolve_intent


def _ctx(**kw):
    return IntentContext(user_id=1, **kw)


def test_intent_text_puts_the_current_step_first_and_uses_only_the_users_words():
    ctx = _ctx(project_title="Fuze", project_description="bookmark manager",
               project_technologies="Flask, pgvector", task_title="Add auth",
               task_description="login with JWT", subtask_title="Refresh tokens", query="rotation")
    text = compose_intent_text(ctx)
    lines = text.splitlines()
    assert lines[0].startswith("Current step: Refresh tokens")
    assert lines[1].startswith("Current task: Add auth")
    assert "Looking for: rotation" in text and "Project: Fuze" in text and "Using: Flask, pgvector" in text


def test_empty_context_gives_empty_intent():
    assert compose_intent_text(_ctx()) == ""


def test_ai_generated_task_json_description_is_read_as_prose():
    raw = json.dumps({"description": "Wire up OAuth", "key_technologies": ["Flask"]})
    assert intent_mod._task_description(raw) == "Wire up OAuth"
    assert intent_mod._task_description("plain words") == "plain words"


def test_parse_intent_validates_and_caps_needs():
    ok = parse_intent({"statement": "Building auth.", "needs": ["a", "b", "c", "d", "e", 7, ""]})
    assert ok == {"statement": "Building auth.", "needs": ["a", "b", "c", "d"]}
    assert parse_intent({"statement": "", "needs": ["a"]}) is None
    assert parse_intent("nope") is None


def test_resolve_uses_cached_statement_without_scheduling():
    cache = MagicMock()
    cache.get_cache.return_value = {"statement": "They are adding JWT auth.", "needs": ["refresh token rotation"]}
    with patch("utils.redis_utils.redis_cache", cache), \
         patch.object(intent_mod, "schedule_intent") as sched:
        it = resolve_intent(_ctx(query="jwt refresh"))
    assert it.statement == "They are adding JWT auth."
    assert it.query_texts() == ["Looking for: jwt refresh.", "They are adding JWT auth.", "refresh token rotation"]
    assert it.rerank_query == "They are adding JWT auth."
    sched.assert_not_called()


def test_resolve_without_cache_uses_the_users_words_and_schedules_once():
    cache = MagicMock()
    cache.get_cache.return_value = None
    cache.redis_client.set.side_effect = [True, False]
    queue = MagicMock()
    with patch("utils.redis_utils.redis_cache", cache), \
         patch("services.task_queue.get_queue", return_value=queue):
        first = resolve_intent(_ctx(query="jwt refresh"))
        second = resolve_intent(_ctx(query="jwt refresh"))
    assert first.statement is None and first.query_texts() == ["Looking for: jwt refresh."]
    assert first.rerank_query == "Looking for: jwt refresh."
    assert second.hash == first.hash
    queue.enqueue.assert_called_once()
    assert queue.enqueue.call_args.args[0] == intent_mod.JOB_PATH


def test_intent_job_caches_valid_statement_and_skips_invalid():
    cache = MagicMock()
    analyzer = MagicMock()
    with patch("utils.redis_utils.redis_cache", cache), \
         patch("utils.gemini_utils.GeminiAnalyzer", return_value=analyzer):
        analyzer.generate_json.return_value = {"statement": "Adding auth.", "needs": ["JWT"]}
        assert intent_mod.compute_intent_job("h1", "Looking for: auth.") is True
        analyzer.generate_json.return_value = None
        assert intent_mod.compute_intent_job("h2", "Looking for: auth.") is False
    assert cache.set_cache.call_count == 1
    assert cache.set_cache.call_args.args[0] == intent_mod.CACHE_PREFIX + "h1"


def test_load_context_ignores_objects_owned_by_someone_else(app):
    from models import db, Project, Task, User
    with app.app_context():
        a = User(username="ctx_a", email="ctx_a@example.com", password_hash="x")
        b = User(username="ctx_b", email="ctx_b@example.com", password_hash="x")
        db.session.add_all([a, b]); db.session.commit()
        p_b = Project(user_id=b.id, title="B secret", description="private")
        db.session.add(p_b); db.session.commit()
        t_b = Task(project_id=p_b.id, title="B task")
        db.session.add(t_b); db.session.commit()

        ctx = intent_mod.load_context(db.session, a.id, query="hi", project_id=p_b.id, task_id=t_b.id)
        assert ctx.project_title == "" and ctx.task_title == "" and ctx.project_id is None
        own = intent_mod.load_context(db.session, b.id, task_id=t_b.id)
        assert own.task_title == "B task" and own.project_title == "B secret"


def test_mmr_prefers_a_different_item_over_a_near_duplicate():
    from ml.intent_engine.engine import _mmr
    vecs = {1: np.array([1.0, 0.0]), 2: np.array([0.999, 0.04]), 3: np.array([0.0, 1.0])}
    cands = [{"content_id": 1, "relevance": 0.90}, {"content_id": 2, "relevance": 0.89},
             {"content_id": 3, "relevance": 0.80}]
    picked = [c["content_id"] for c in _mmr(cands, vecs, 2)]
    assert picked == [1, 3]


def test_snippet_drops_the_title_prefix_and_truncates():
    from ml.intent_engine.engine import _snippet
    s = _snippet("Flask JWT\n" + "word " * 200, "Flask JWT")
    assert not s.startswith("Flask JWT") and s.endswith("…") and len(s) <= 241


def test_recommend_end_to_end_on_document_fallback(app):
    """SQLite path: no chunks, document-level candidates, no reranker, results explained."""
    from ml.intent_engine.engine import recommend
    from models import db, ContentAnalysis, SavedContent, User
    with app.app_context():
        u = User(username="eng_u", email="eng_u@example.com", password_hash="x")
        db.session.add(u); db.session.commit()
        item = SavedContent(user_id=u.id, url="https://example.com/jwt", title="JWT in Flask",
                            extracted_text="How to issue and refresh JWTs in Flask.", quality_score=85)
        db.session.add(item); db.session.commit()
        db.session.add(ContentAnalysis(content_id=item.id, analysis_data={
            "profile_version": "profile-v1", "summary": "JWT auth in Flask", "use_when": "securing an API",
            "content_type": "tutorial", "audience_level": "intermediate", "technologies": ["Flask"],
            "key_concepts": ["JWT"]}))
        db.session.commit()

        fake = [{"content_id": item.id, "passage": "JWT in Flask\nHow to issue and refresh JWTs.", "similarity": 0.71}]
        with patch("ml.intent_engine.engine._document_candidates", return_value=fake), \
             patch("utils.embedding_utils.embed_query", return_value=np.ones(384, dtype=np.float32)), \
             patch("ml.intent_engine.intent.schedule_intent"):
            out = recommend(db.session, u.id, query="secure my api", rerank=False, use_cache=False)

    r = out["results"][0]
    assert r["id"] == item.id and r["score"] == 71.0 and r["engine_used"] == "intent_engine"
    assert r["basic_summary"] == "JWT auth in Flask" and r["content_type"] == "tutorial"
    assert r["quality_score"] == 8.5
    assert "How to issue and refresh JWTs" in r["reason"]
    assert out["intent"]["intent_source"] == "context"


def test_document_fallback_ranks_by_cosine_and_ignores_other_models(app):
    from ml.intent_engine.engine import _document_candidates
    from models import db, SavedContent, User
    from utils.embedding_utils import active_embedding_model_name
    with app.app_context():
        model = active_embedding_model_name()
        u = User(username="fb_u", email="fb_u@example.com", password_hash="x")
        db.session.add(u); db.session.commit()
        def vec(*head):
            v = np.zeros(384, dtype=np.float32); v[:len(head)] = head; return v
        near = SavedContent(user_id=u.id, url="https://e.com/near", title="near", extracted_text="near",
                            embedding=vec(1, 0.1), embedding_metadata={"model": model})
        far = SavedContent(user_id=u.id, url="https://e.com/far", title="far", extracted_text="far",
                           embedding=vec(0, 1), embedding_metadata={"model": model})
        stale = SavedContent(user_id=u.id, url="https://e.com/stale", title="stale", extracted_text="stale",
                             embedding=vec(1, 0), embedding_metadata={"model": "some-old-model"})
        db.session.add_all([near, far, stale]); db.session.commit()

        out = _document_candidates(db.session, u.id, [vec(1, 0)], k=10)
        assert [c["content_id"] for c in out] == [near.id, far.id]
        assert out[0]["similarity"] > 0.99 and abs(out[1]["similarity"]) < 0.2
