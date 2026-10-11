"""
Intent × content recommendation engine.

  intent (user's own context + cached Gemini statement/needs)
    -> query vectors
    -> nearest passages/profiles over the user's content (pgvector)
    -> cross-encoder rerank of (intent, best passage)       [optional]
    -> MMR diversity
    -> results explained by the passage that matched

No keyword lists, rule-based boosts or query-independent multipliers.
"""

import hashlib
import json
import math
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


def _cache_key(intent: Intent, user_id: int, limit: int, rerank: bool) -> str:
    from utils.content_version import get_content_version
    from utils.embedding_utils import active_embedding_model_name
    raw = (f"{user_id}|{intent.hash}|{bool(intent.statement)}|{limit}|{rerank}|"
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

    results = []
    for c in picked:
        r = rows[c["content_id"]]
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
        results.append({
            "id": r["id"],
            "title": r.get("title") or r.get("url"),
            "url": r.get("url"),
            "score": pct,
            "confidence": pct,
            "reason": f"Matches what you're working on: “{snippet}”" if snippet else "",
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
        })

    payload = {"results": results, "intent": meta}
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
