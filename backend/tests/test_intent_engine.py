import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

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


def _mmr_reference(candidates, vectors, k, lam=0.7):
    """The original pure-Python MMR, kept to check the vectorised version picks the same items."""
    pool = list(candidates)
    picked = []
    while pool and len(picked) < k:
        def mmr_score(c):
            v = vectors.get(c["content_id"])
            if v is None or not picked:
                return c["relevance"]
            sims = [float(np.dot(v, vectors[p["content_id"]]) /
                          (np.linalg.norm(v) * np.linalg.norm(vectors[p["content_id"]]) + 1e-9))
                    for p in picked if vectors.get(p["content_id"]) is not None]
            return lam * c["relevance"] - (1 - lam) * (max(sims) if sims else 0.0)
        best = max(pool, key=mmr_score)
        picked.append(best)
        pool.remove(best)
    return picked


@pytest.mark.parametrize("seed", range(20))
def test_vectorised_mmr_matches_the_reference_on_random_data(seed):
    from ml.intent_engine.engine import _mmr, MMR_LAMBDA
    rng = np.random.default_rng(seed)
    n = int(rng.integers(1, 120))
    k = int(rng.integers(0, n + 5))
    base = rng.normal(size=(8, 384)).astype(np.float32)
    vecs = {}
    for cid in range(n):
        if rng.random() < 0.1:
            continue  # some candidates have no stored embedding
        # Clustered vectors so near-duplicates (and real MMR trade-offs) occur.
        vecs[cid] = (base[cid % 8] + 0.3 * rng.normal(size=384)).astype(np.float32)
    cands = [{"content_id": cid, "relevance": float(r)} for cid, r in enumerate(rng.random(n))]
    cands.sort(key=lambda c: c["relevance"], reverse=True)

    expected = [c["content_id"] for c in _mmr_reference(cands, vecs, k, MMR_LAMBDA)]
    assert [c["content_id"] for c in _mmr(cands, vecs, k)] == expected


def test_mmr_handles_empty_input_and_no_vectors():
    from ml.intent_engine.engine import _mmr
    assert _mmr([], {}, 5) == []
    cands = [{"content_id": 1, "relevance": 0.2}, {"content_id": 2, "relevance": 0.9}]
    assert [c["content_id"] for c in _mmr(cands, {1: None}, 5)] == [2, 1]


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


def test_document_candidates_enable_iterative_hnsw_scan_on_postgres():
    from ml.intent_engine.engine import _document_candidates
    session = MagicMock()
    session.info = {}
    session.get_bind.return_value.dialect.name = "postgresql"
    session.execute.return_value = []
    _document_candidates(session, 7, [np.ones(384, dtype=np.float32)], k=60)
    sql = [str(c.args[0]) for c in session.execute.call_args_list]
    assert "hnsw.iterative_scan" in sql[0] and "hnsw.ef_search" in sql[0]  # both settings in one statement
    assert session.execute.call_args_list[0].args[1] == {"ef": "60"}
    assert "<=>" in sql[1]


# ---------------------------------------------------------------- confidence check (weak matches)

def _result(i):
    return {"id": i, "metadata": {}}


def test_a_result_scoring_below_the_floor_is_marked_weak_and_nothing_is_reordered():
    from ml.intent_engine.engine import WEAK_MATCH_LOGIT, mark_weak_matches
    results = [_result(1), _result(2), _result(3)]
    weak = mark_weak_matches(results, ["a", "b", "c"], "q",
                             score_fn=lambda q, p: [3.0, WEAK_MATCH_LOGIT - 0.1, WEAK_MATCH_LOGIT])
    assert weak == 1
    assert [r["weak_match"] for r in results] == [False, True, False]     # at the floor is not weak
    assert [r["id"] for r in results] == [1, 2, 3]
    assert results[0]["metadata"]["confidence_score"] == 3.0


def test_when_the_model_is_unavailable_nothing_is_marked():
    from ml.intent_engine.engine import mark_weak_matches
    results = [_result(1), _result(2)]
    assert mark_weak_matches(results, ["a", "b"], "q", score_fn=lambda q, p: None) == 0
    assert all("weak_match" not in r for r in results)        # unknown, not "strong"

    def boom(q, p):
        raise RuntimeError("model crashed")
    assert mark_weak_matches(results, ["a", "b"], "q", score_fn=boom) == 0
    assert all("weak_match" not in r for r in results)


def test_mismatched_inputs_are_ignored_not_guessed():
    from ml.intent_engine.engine import mark_weak_matches
    results = [_result(1), _result(2)]
    assert mark_weak_matches(results, ["only one passage"], "q", score_fn=lambda q, p: [0.0]) == 0
    assert mark_weak_matches([], [], "q", score_fn=lambda q, p: []) == 0


def test_the_check_can_be_switched_off(monkeypatch):
    from ml.intent_engine.engine import confidence_check_enabled
    monkeypatch.delenv("RECOMMENDATION_CONFIDENCE_ENABLED", raising=False)
    assert confidence_check_enabled() is True
    for off in ("false", "0", "no", "OFF"):
        monkeypatch.setenv("RECOMMENDATION_CONFIDENCE_ENABLED", off)
        assert confidence_check_enabled() is False


# ---------------------------------------------------------------- several interests, searched one at a time

def _cand(cid, sim=0.5):
    return {"content_id": cid, "passage": f"p{cid}", "similarity": sim}


def test_interests_are_cleaned_deduplicated_and_capped():
    from ml.intent_engine.engine import MAX_INTERESTS, MAX_INTEREST_CHARS, clean_interests
    assert clean_interests(["React", " react ", "", None, "system  design", 7]) == ["React", "system design", "7"]
    assert clean_interests("React, python") == []            # only a list is accepted
    assert clean_interests(None) == []
    assert len(clean_interests([f"topic {i}" for i in range(20)])) == MAX_INTERESTS
    assert len(clean_interests(["x" * 500])[0]) == MAX_INTEREST_CHARS


def test_interleaving_gives_each_interest_its_turn_and_never_repeats_a_bookmark():
    from ml.intent_engine.engine import interleave_by_interest
    react = [_cand(1), _cand(2), _cand(3)]
    design = [_cand(10), _cand(2), _cand(11)]           # 2 answers both: it is picked once, for the first
    picked = interleave_by_interest([react, design], limit=10)
    assert [(p["content_id"], p["interest_index"]) for p in picked] == [(1, 0), (10, 1), (2, 0), (11, 1), (3, 0)]


def test_an_interest_with_few_matches_runs_out_and_the_others_fill_the_list():
    from ml.intent_engine.engine import interleave_by_interest
    picked = interleave_by_interest([[_cand(1)], [_cand(10), _cand(11), _cand(12)], []], limit=4)
    assert [p["content_id"] for p in picked] == [1, 10, 11, 12]


def test_interleaving_stops_at_the_limit_and_copies_its_input():
    from ml.intent_engine.engine import interleave_by_interest
    lists = [[_cand(1), _cand(2)], [_cand(10), _cand(11)]]
    picked = interleave_by_interest(lists, limit=3)
    assert [p["content_id"] for p in picked] == [1, 10, 2]
    assert "interest_index" not in lists[0][0]           # the candidates passed in are left untouched
    assert interleave_by_interest([], limit=5) == []


def test_each_result_is_judged_against_its_own_interest():
    from ml.intent_engine.engine import mark_weak_matches
    results = [_result(1), _result(2), _result(3)]
    seen = []

    def score(query, passages):
        seen.append((query, list(passages)))
        return [0.0] * len(passages)

    mark_weak_matches(results, ["a", "b", "c"], ["react", "go", "react"], score_fn=score)
    assert sorted(seen) == [("go", ["b"]), ("react", ["a", "c"])]
    assert [r["metadata"]["confidence_score"] for r in results] == [0.0, 0.0, 0.0]
    assert mark_weak_matches(results, ["a", "b", "c"], ["only", "two"], score_fn=score) == 0   # wrong length: ignored


def test_recommend_interests_searches_each_one_and_labels_the_matches(app):
    from ml.intent_engine.engine import recommend_interests
    from models import db, SavedContent, User
    with app.app_context():
        u = User(username="int_u", email="int_u@example.com", password_hash="x")
        db.session.add(u); db.session.commit()
        react = SavedContent(user_id=u.id, url="https://e.com/react", title="React hooks", extracted_text="hooks")
        design = SavedContent(user_id=u.id, url="https://e.com/sd", title="System design primer", extracted_text="design")
        db.session.add_all([react, design]); db.session.commit()

        def fake_candidates(session, user_id, vectors, k):
            react_passage = "React hooks\nHow hooks work in components."
            design_passage = "System design primer\nScaling a service step by step."
            by_dim = {0: [{"content_id": react.id, "passage": react_passage, "similarity": 0.8}],
                      1: [{"content_id": design.id, "passage": design_passage, "similarity": 0.7}]}
            return by_dim[int(np.argmax(vectors[0]))]

        def embed(text):
            v = np.zeros(384, dtype=np.float32)
            v[0 if text == "React" else 1] = 1.0
            return v

        with patch("ml.intent_engine.engine._document_candidates", side_effect=fake_candidates), \
             patch("utils.embedding_utils.embed_query", side_effect=embed), \
             patch("ml.intent_engine.engine.mark_weak_matches", return_value=0) as weak:
            out = recommend_interests(db.session, u.id, ["React", "system design"], use_cache=False)

    assert [r["title"] for r in out["results"]] == ["React hooks", "System design primer"]
    assert [r["metadata"]["matched_interest"] for r in out["results"]] == ["React", "system design"]
    assert out["results"][0]["reason"].startswith("Matches your interest in React")
    assert out["intent"]["intent_source"] == "interests" and out["intent"]["interests"] == ["React", "system design"]
    assert weak.call_args.args[2] == ["React", "system design"]       # judged against their own interests


def test_recommend_interests_with_nothing_to_search_returns_nothing():
    from ml.intent_engine.engine import recommend_interests
    out = recommend_interests(MagicMock(), 1, ["", "  ", None], use_cache=False)
    assert out["results"] == [] and out["intent"]["interests"] == []


def test_retrieve_each_keeps_the_queries_apart_with_one_statement_each():
    from services.hybrid_search import retrieve_each
    session = MagicMock()
    session.info = {}
    session.get_bind.return_value.dialect.name = "postgresql"
    rows = [(7, "passage", 0.9, "Title", "https://e.com", None, None)]
    session.execute.side_effect = lambda *a, **k: rows if "<=>" in str(a[0]) and "emb" in (a[1] if len(a) > 1 else {}) else []
    lists = retrieve_each(session, 1, [np.ones(384, dtype=np.float32), np.ones(384, dtype=np.float32)], k=30)
    assert len(lists) == 2                                   # one list per query, not one merged list
    assert [c["content_id"] for c in lists[0]] == [7] == [c["content_id"] for c in lists[1]]
    queries = [c for c in session.execute.call_args_list if "<=>" in str(c.args[0])]
    assert len(queries) == 2                                 # one SQL statement per query vector
