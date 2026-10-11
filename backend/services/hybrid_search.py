"""
Passage-level semantic retrieval over content_chunks, optionally reranked by a
cross-encoder. Meaning only: no keyword or rule-based matching.

Postgres-only (pgvector). Callers fall back to document-level search on other
dialects or when a user's content has no chunks yet.
"""

import os
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from sqlalchemy import text

from core.logging_config import get_logger
from utils.chunking import chunk_text
from utils.embedding_utils import active_embedding_model_name, embed_query, get_embeddings_batch

logger = get_logger(__name__)

CANDIDATES_PER_QUERY = 60
RERANK_TOP_N = 30


def rerank_enabled() -> bool:
    # Off by default: on SciFact the ms-marco cross-encoder changed nDCG@10 by -0.008 / +0.004
    # (short / long docs) while adding ~700 ms per query on CPU. See eval/results/.
    return os.environ.get("SEARCH_RERANK_ENABLED", "false").strip().lower() in ("1", "true", "yes")


def _vec_literal(vec) -> str:
    return "[" + ",".join(f"{float(x):.6f}" for x in np.asarray(vec, dtype=np.float32)) + "]"


def index_content_chunks(session, content_id: int) -> int:
    """(Re)build passage chunks + embeddings for one bookmark. Returns the number of chunks written."""
    row = session.execute(
        text("SELECT user_id, title, extracted_text, notes FROM saved_content WHERE id = :id"),
        {"id": content_id},
    ).first()
    if not row:
        return 0
    user_id, title, extracted, notes = row
    body = "\n\n".join(p for p in (extracted, notes) if p)
    passages = chunk_text(title or "", body)
    session.execute(text("DELETE FROM content_chunks WHERE content_id = :id AND kind = 'passage'"), {"id": content_id})
    if not passages:
        return 0

    vectors = get_embeddings_batch(passages)
    model = active_embedding_model_name()
    session.execute(
        text(
            "INSERT INTO content_chunks (content_id, user_id, chunk_index, text, embedding, embedding_model) "
            "VALUES (:content_id, :user_id, :idx, :text, CAST(:emb AS vector), :model)"
        ),
        [
            {"content_id": content_id, "user_id": user_id, "idx": i, "text": p, "emb": _vec_literal(v),
             "model": model}
            for i, (p, v) in enumerate(zip(passages, vectors))
            if np.any(v)
        ],
    )
    return len(passages)


# Nearest passages for one query vector. Called once per query vector; results are merged in Python.
_ANN_SQL = """
SELECT c.content_id, c.text, 1 - (c.embedding <=> CAST(:emb AS vector)) AS similarity
FROM content_chunks c
WHERE c.user_id = :uid AND c.embedding_model = :model
ORDER BY c.embedding <=> CAST(:emb AS vector)
LIMIT :k
"""

_DOCS_SQL = """
SELECT id, title, url, notes, saved_at FROM saved_content WHERE user_id = :uid AND id = ANY(:ids)
"""


def user_has_chunks(session, user_id: int) -> bool:
    return session.execute(
        text("SELECT 1 FROM content_chunks WHERE user_id = :uid AND embedding_model = :model LIMIT 1"),
        {"uid": user_id, "model": active_embedding_model_name()}
    ).first() is not None


def retrieve(session, user_id: int, query_vectors: Sequence, k: int = CANDIDATES_PER_QUERY) -> List[Dict[str, Any]]:
    """Union of nearest passages across query vectors; one entry per bookmark with its best passage."""
    # Keep scanning HNSW when the per-user filter removes most neighbours (pgvector >= 0.8).
    session.execute(text("SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true)"))
    session.execute(text("SELECT set_config('hnsw.ef_search', :ef, true)"), {"ef": str(max(k, 40))})

    model = active_embedding_model_name()
    best: Dict[int, Dict[str, Any]] = {}
    for vec in query_vectors:
        for content_id, passage, sim in session.execute(
            text(_ANN_SQL), {"emb": _vec_literal(vec), "uid": user_id, "k": k, "model": model}
        ):
            sim = float(sim)
            if content_id not in best or sim > best[content_id]["similarity"]:
                best[content_id] = {"content_id": content_id, "passage": passage, "similarity": sim}
    return sorted(best.values(), key=lambda r: r["similarity"], reverse=True)


def semantic_search(session, user_id: int, query: str, limit: int = 10,
                    rerank: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Rank a user's bookmarks for a query by passage meaning; best passage returned as the snippet."""
    if rerank is None:
        rerank = rerank_enabled()
    started = time.perf_counter()

    candidates = retrieve(session, user_id, [embed_query(query)])
    pool = candidates[:max(limit, RERANK_TOP_N)] if rerank else candidates[:limit]

    if rerank and pool:
        from utils.reranker import rerank_passages
        scores = rerank_passages(query, [c["passage"] for c in pool[:RERANK_TOP_N]])
        if scores is not None:
            for c, s in zip(pool, scores):
                c["rerank_score"] = float(s)
            head = sorted(pool[:RERANK_TOP_N], key=lambda c: c["rerank_score"], reverse=True)
            pool = head + pool[RERANK_TOP_N:]
    pool = pool[:limit]

    if pool:
        docs = {d["id"]: dict(d) for d in session.execute(
            text(_DOCS_SQL), {"uid": user_id, "ids": [c["content_id"] for c in pool]}
        ).mappings()}
        for c in pool:
            c.update(docs.get(c["content_id"], {}))

    logger.info("passage_search_completed", extra={
        "user_id": user_id, "rerank": bool(rerank), "results": len(pool),
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    })
    return pool
