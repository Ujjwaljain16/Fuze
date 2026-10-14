"""
Intent × content recommendation engine.

  intent (user's own context + cached Gemini statement/needs)
    -> query vectors
    -> nearest passages/profiles over the user's content (pgvector)
    -> cross-encoder rerank of (intent, best passage)       [optional, changes the order]
    -> MMR diversity
    -> results explained by the passage that matched
    -> cross-encoder confidence check of the picked results [marks weak matches, never reorders]

No keyword lists, rule-based boosts or query-independent multipliers.
"""

import hashlib
import json
import math
import os
import time
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import text

from core.logging_config import get_logger
from ml.intent_engine.intent import Intent, load_context, resolve_intent

logger = get_logger(__name__)

CANDIDATES_PER_QUERY = 60
RERANK_TOP_N = 30
MMR_LAMBDA = 0.7
CACHE_TTL = 600
SNIPPET_CHARS = 240

# Raw cross-encoder score (ms-marco-MiniLM-L-6-v2) of (intent, best passage) under which a picked result is
# marked a weak match. Chosen by judging 15 requests (5 projects, 10 tasks, 150 results) on a real library of 238
# bookmarks; the scores below are for the passage the engine itself passes in. Unfiltered, 60% of the results
# were clearly useful. With a floor of -5, 89% of the irrelevant results and 45% of the loosely related ones
# are marked weak, the strong list is 81% clearly useful, and 23% of the useful results are marked weak too
# (mostly bookmarks with no readable page text, so the passage says little). Weak results are folded away, not
# removed, so that cost is one click. Cosine similarity could not do this: irrelevant results reached 77%
# while some useful ones sat at 66%, and its best floor kept 12% of the irrelevant at 21% loss of useful.
WEAK_MATCH_LOGIT = -5.0


def confidence_check_enabled() -> bool:
    """RECOMMENDATION_CONFIDENCE_ENABLED (default on): mark weak matches with the cross-encoder."""
    return os.environ.get("RECOMMENDATION_CONFIDENCE_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")


def mark_weak_matches(results: List[Dict[str, Any]], passages: List[str], query, score_fn=None) -> int:
    """Flag results whose best passage the cross-encoder does not tie to `query`; returns how many are weak.

    `query` is one text for every result, or a list with one text per result (results found for different
    interests are each judged against their own interest, not against a blend of all of them).

    The order is left alone (similarity plus diversity ranked well: nDCG 0.97 on the judged requests); this
    only says how sure the engine is. When the model is unavailable nothing is marked, which the page reads as
    "unknown", not "strong".
    """
    if not results or len(results) != len(passages):
        return 0
    queries = [query] * len(results) if isinstance(query, str) else list(query)
    if len(queries) != len(results):
        return 0
    if score_fn is None:
        from utils.reranker import rerank_passages as score_fn
    groups: Dict[str, List[int]] = {}
    for index, q in enumerate(queries):
        groups.setdefault(q, []).append(index)
    scores: List[float] = [0.0] * len(results)
    try:
        for q, indexes in groups.items():
            got = score_fn(q, [passages[i] for i in indexes])
            if got is None:
                return 0
            for i, value in zip(indexes, got):
                scores[i] = float(value)
    except Exception:
        logger.warning("recommendation_confidence_check_failed", exc_info=True)
        return 0
    weak = 0
    for result, score in zip(results, scores):
        score = float(score)
        result["weak_match"] = score < WEAK_MATCH_LOGIT
        result["metadata"]["confidence_score"] = round(score, 2)
        weak += result["weak_match"]
    return weak


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _parse_vec(value) -> Optional[np.ndarray]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return np.asarray(json.loads(value), dtype=np.float32)
        except (json.JSONDecodeError, TypeError):
            return None
    return np.asarray(value, dtype=np.float32)


def _snippet(passage: str, title: str) -> str:
    body = (passage or "").strip()
    if title and body.startswith(title):
        body = body[len(title):].lstrip("\n .:")
    body = " ".join(body.split())
    return body if len(body) <= SNIPPET_CHARS else body[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"


def _document_candidates(session, user_id: int, vectors, k: int) -> List[Dict[str, Any]]:
    """Fallback for content without passage chunks: one embedding per bookmark."""
    from utils.embedding_utils import active_embedding_model_name

    model = active_embedding_model_name()  # never compare vectors from different models
    best: Dict[int, Dict[str, Any]] = {}

    def keep(cid, passage, sim):
        if cid not in best or sim > best[cid]["similarity"]:
            best[cid] = {"content_id": cid, "passage": passage or "", "similarity": sim}

    if session.get_bind().dialect.name == "postgresql":
        from services.hybrid_search import _vec_literal, configure_filtered_ann
        configure_filtered_ann(session, k)
        for vec in vectors:
            rows = session.execute(text(
                "SELECT id, COALESCE(LEFT(extracted_text, 1200), title) AS passage, "
                "1 - (embedding <=> CAST(:emb AS vector)) AS similarity "
                "FROM saved_content WHERE user_id = :uid AND embedding IS NOT NULL "
                "AND embedding_metadata->>'model' = :model "
                "ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :k"
            ), {"emb": _vec_literal(vec), "uid": user_id, "k": k, "model": model})
            for cid, passage, sim in rows:
                keep(cid, passage, float(sim))
    else:
        # Non-Postgres (tests/dev): exact cosine in numpy over the user's embedded items.
        from models import SavedContent
        items = [i for i in session.query(SavedContent).filter(
            SavedContent.user_id == user_id, SavedContent.embedding.isnot(None))
            if (i.embedding_metadata or {}).get("model") == model]
        if items:
            mat = np.asarray([np.asarray(i.embedding, dtype=np.float32) for i in items])
            mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
            for vec in vectors:
                q = np.asarray(vec, dtype=np.float32)
                sims = mat @ (q / (np.linalg.norm(q) + 1e-9))
                for idx in np.argsort(-sims)[:k]:
                    item = items[idx]
                    keep(item.id, (item.extracted_text or item.title or "")[:1200], float(sims[idx]))
    return sorted(best.values(), key=lambda r: r["similarity"], reverse=True)


def _mmr(candidates: List[Dict[str, Any]], vectors: Dict[int, np.ndarray], k: int) -> List[Dict[str, Any]]:
    """Maximal marginal relevance: relevant, but not near-duplicates of what's already picked.

    Each candidate's score is lambda * relevance - (1 - lambda) * (max cosine to a picked item).
    The first pick, and any candidate without a vector, is scored by relevance alone; ties go to
    the earlier candidate. Vectorised: one matrix-vector product per pick keeps a running max.
    """
    pool = list(candidates)
    n = min(k, len(pool))
    if n <= 0:
        return []

    relevance = np.asarray([c["relevance"] for c in pool], dtype=np.float64)
    vecs = [vectors.get(c["content_id"]) for c in pool]
    has_vec = np.asarray([v is not None for v in vecs])
    dim = next((len(v) for v in vecs if v is not None), 0)
    mat = np.zeros((len(pool), dim), dtype=np.float64)
    for i, v in enumerate(vecs):
        if v is not None:
            mat[i] = v
    norms = np.linalg.norm(mat, axis=1)

    max_sim = np.full(len(pool), -np.inf)  # vs picked items that have a vector; -inf = none yet
    available = np.ones(len(pool), dtype=bool)
    order: List[int] = []
    while len(order) < n:
        if order:
            penalty = np.where(np.isfinite(max_sim), max_sim, 0.0)
            scores = np.where(has_vec, MMR_LAMBDA * relevance - (1 - MMR_LAMBDA) * penalty, relevance)
        else:
            scores = relevance.copy()
        scores[~available] = -np.inf
        best = int(np.argmax(scores))
        order.append(best)
        available[best] = False
        if has_vec[best]:
            max_sim = np.maximum(max_sim, (mat @ mat[best]) / (norms * norms[best] + 1e-9))
    return [pool[i] for i in order]


def _load_items(session, user_id: int, ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Title/url/profile/embedding for candidate bookmarks owned by the user."""
    if not ids:
        return {}
    from models import ContentAnalysis, SavedContent
    q = (session.query(SavedContent, ContentAnalysis)
         .outerjoin(ContentAnalysis, ContentAnalysis.content_id == SavedContent.id)
         .filter(SavedContent.user_id == user_id, SavedContent.id.in_(ids)))
    out = {}
    for item, analysis in q:
        out[item.id] = {
            "id": item.id, "title": item.title, "url": item.url, "quality_score": item.quality_score,
            "emb": item.embedding, "analysis_data": analysis.analysis_data if analysis else None,
        }
    return out


def _build_result(c: Dict[str, Any], r: Dict[str, Any], lead: str = "Matches what you're working on") -> Dict[str, Any]:
    """One recommendation as the API returns it: the bookmark, its profile, and the passage that matched."""
    profile = r.get("analysis_data") or {}
    if isinstance(profile, str):
        try:
            profile = json.loads(profile)
        except (json.JSONDecodeError, TypeError):
            profile = {}
    if not profile.get("profile_version"):
        profile = {}  # legacy/unverified analysis: show nothing rather than a guess
    pct = round(100 * c["relevance"], 1)
    snippet = _snippet(c["passage"], r.get("title") or "")
    return {
        "id": r["id"],
        "title": r.get("title") or r.get("url"),
        "url": r.get("url"),
        "score": pct,
        "confidence": pct,
        "reason": f"{lead}: \u201c{snippet}\u201d" if snippet else "",
        "basic_summary": profile.get("summary", ""),
        "content_type": profile.get("content_type", "other"),
        "difficulty": profile.get("audience_level", "mixed"),
        "technologies": profile.get("technologies", []),
        "key_concepts": profile.get("key_concepts", []),
        "quality_score": round((r.get("quality_score") or 0) / 10, 1),  # stored 0-100, UI shows 0-10
        "engine_used": "intent_engine",
        "metadata": {
            "matched_passage": snippet,
            "use_when": profile.get("use_when"),
            "vector_similarity": round(c["similarity"], 4),
            "rerank_score": round(c["rerank_score"], 4) if "rerank_score" in c else None,
        },
    }


def _cache_key(intent: Intent, user_id: int, limit: int, rerank: bool) -> str:
    from utils.content_version import get_content_version
    from utils.embedding_utils import active_embedding_model_name
    raw = (f"{user_id}|{intent.hash}|{bool(intent.statement)}|{limit}|{rerank}|{confidence_check_enabled()}|"
           f"{active_embedding_model_name()}|v{get_content_version(user_id)}")
    return "intent_recs:" + hashlib.sha256(raw.encode()).hexdigest()[:32]


def recommend(session, user_id: int, query: str = "", project_id: Optional[int] = None,
              task_id: Optional[int] = None, subtask_id: Optional[int] = None,
              limit: int = 10, rerank: Optional[bool] = None, use_cache: bool = True) -> Dict[str, Any]:
    """Recommend the user's own saved content for what they're doing right now."""
    from services.hybrid_search import rerank_enabled, retrieve, user_has_chunks
    from utils.embedding_utils import embed_query
    from utils.redis_utils import redis_cache

    started = time.perf_counter()
    if rerank is None:
        rerank = rerank_enabled()
    limit = max(1, min(int(limit or 10), 50))

    ctx = load_context(session, user_id, query, project_id, task_id, subtask_id)
    intent = resolve_intent(ctx)
    meta = {"intent_text": intent.text, "intent_statement": intent.statement, "needs": intent.needs,
            "intent_source": "llm" if intent.statement else "context"}
    if not intent.text:
        return {"results": [], "intent": meta, "cached": False}

    key = _cache_key(intent, user_id, limit, rerank)
    if use_cache:
        try:
            cached = redis_cache.get_cache(key)
            if cached:
                return {**cached, "cached": True}
        except Exception:
            pass

    vectors = [embed_query(t) for t in intent.query_texts()]
    if session.get_bind().dialect.name == "postgresql" and user_has_chunks(session, user_id):
        candidates = retrieve(session, user_id, vectors, CANDIDATES_PER_QUERY)
    else:
        candidates = _document_candidates(session, user_id, vectors, CANDIDATES_PER_QUERY)
    pool = candidates[:max(RERANK_TOP_N, limit * 3)]

    for c in pool:
        c["relevance"] = max(0.0, min(1.0, c["similarity"]))
    if rerank and pool:
        from utils.reranker import rerank_passages
        scores = rerank_passages(intent.rerank_query, [c["passage"] for c in pool[:RERANK_TOP_N]])
        if scores is not None:
            for c, s in zip(pool, scores):
                c["rerank_score"] = float(s)
                c["relevance"] = _sigmoid(float(s))
            pool = pool[:RERANK_TOP_N]
    pool.sort(key=lambda c: c["relevance"], reverse=True)

    rows = _load_items(session, user_id, [c["content_id"] for c in pool])

    doc_vecs = {cid: _parse_vec(r.get("emb")) for cid, r in rows.items()}
    picked = _mmr([c for c in pool if c["content_id"] in rows], doc_vecs, limit)

    results = [_build_result(c, rows[c["content_id"]]) for c in picked]

    weak = 0
    if confidence_check_enabled():
        weak = mark_weak_matches(results, [c["passage"] for c in picked], intent.rerank_query)
    payload = {"results": results, "intent": meta, "weak_matches": weak}
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    logger.info("intent_engine_recommendations", extra={
        "user_id": user_id, "candidates": len(candidates), "results": len(results),
        "rerank": bool(rerank), "intent_source": meta["intent_source"], "latency_ms": latency_ms,
    })
    if use_cache and results:
        try:
            redis_cache.set_cache(key, payload, CACHE_TTL)
        except Exception:
            pass
    return {**payload, "cached": False}


MAX_INTERESTS = 6
MAX_INTEREST_CHARS = 100
CANDIDATES_PER_INTEREST = 30


def clean_interests(raw) -> List[str]:
    """The interests to search for: strings, trimmed, no blanks or case-insensitive duplicates, capped."""
    if not isinstance(raw, (list, tuple)):
        return []
    seen, out = set(), []
    for item in raw:
        name = " ".join(str(item).split())[:MAX_INTEREST_CHARS] if isinstance(item, (str, int, float)) else ""
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
        if len(out) >= MAX_INTERESTS:
            break
    return out


def interleave_by_interest(per_interest: List[List[Dict[str, Any]]], limit: int) -> List[Dict[str, Any]]:
    """Round robin over the interests' candidate lists, best first within each, no bookmark twice.

    Each interest gets its turn in order, so every one is visible near the top and gets about limit / n of
    the list; an interest with few good bookmarks simply runs out and the others take the places. Each
    pick is a copy tagged with `interest_index`.
    """
    picked: List[Dict[str, Any]] = []
    seen = set()
    cursors = [0] * len(per_interest)
    progressed = True
    while len(picked) < limit and progressed:
        progressed = False
        for i, candidates in enumerate(per_interest):
            while cursors[i] < len(candidates) and candidates[cursors[i]]["content_id"] in seen:
                cursors[i] += 1
            if cursors[i] >= len(candidates):
                continue
            pick = dict(candidates[cursors[i]])
            pick["interest_index"] = i
            picked.append(pick)
            seen.add(pick["content_id"])
            cursors[i] += 1
            progressed = True
            if len(picked) >= limit:
                break
    return picked


def recommend_interests(session, user_id: int, interests, limit: int = 10, use_cache: bool = True) -> Dict[str, Any]:
    """Recommend the user's saved content across several interests, searching each one on its own.

    One blended query ("React, python, system design, backend") matches nothing well; each interest is
    searched separately and the lists are interleaved, and every result is judged against its own interest.
    """
    from services.hybrid_search import retrieve_each, user_has_chunks
    from utils.content_version import get_content_version
    from utils.embedding_utils import active_embedding_model_name, embed_query
    from utils.redis_utils import redis_cache

    started = time.perf_counter()
    limit = max(1, min(int(limit or 10), 50))
    names = clean_interests(interests)
    meta = {"intent_text": "Interests: " + ", ".join(names), "intent_statement": None, "needs": names,
            "intent_source": "interests", "interests": names}
    if not names:
        return {"results": [], "intent": meta, "cached": False}

    raw_key = (f"interests|{user_id}|{'|'.join(n.lower() for n in names)}|{limit}|{confidence_check_enabled()}|"
               f"{active_embedding_model_name()}|v{get_content_version(user_id)}")
    key = "intent_recs:" + hashlib.sha256(raw_key.encode()).hexdigest()[:32]
    if use_cache:
        try:
            cached = redis_cache.get_cache(key)
            if cached:
                return {**cached, "cached": True}
        except Exception:
            pass

    vectors = [embed_query(n) for n in names]
    if session.get_bind().dialect.name == "postgresql" and user_has_chunks(session, user_id):
        per_interest = retrieve_each(session, user_id, vectors, CANDIDATES_PER_INTEREST)
    else:
        per_interest = [_document_candidates(session, user_id, [v], CANDIDATES_PER_INTEREST) for v in vectors]
    for candidates in per_interest:
        for c in candidates:
            c["relevance"] = max(0.0, min(1.0, c["similarity"]))

    picked = interleave_by_interest(per_interest, limit)
    rows = _load_items(session, user_id, [c["content_id"] for c in picked])
    picked = [c for c in picked if c["content_id"] in rows]

    results = []
    for c in picked:
        result = _build_result(c, rows[c["content_id"]], lead=f"Matches your interest in {names[c['interest_index']]}")
        result["metadata"]["matched_interest"] = names[c["interest_index"]]
        results.append(result)

    weak = 0
    if confidence_check_enabled():
        weak = mark_weak_matches(results, [c["passage"] for c in picked], [names[c["interest_index"]] for c in picked])
    payload = {"results": results, "intent": meta, "weak_matches": weak}
    logger.info("intent_engine_interest_recommendations", extra={
        "user_id": user_id, "interests": len(names), "results": len(results),
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    })
    if use_cache and results:
        try:
            redis_cache.set_cache(key, payload, CACHE_TTL)
        except Exception:
            pass
    return {**payload, "cached": False}
