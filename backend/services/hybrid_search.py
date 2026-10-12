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
# The inner query keeps the shape HNSW needs (ORDER BY distance LIMIT k on the filtered table); the
# join then adds each bookmark's title, url, notes and date, so showing results needs no second query.
_ANN_SQL = """
SELECT x.content_id, x.text, x.similarity, s.title, s.url, s.notes, s.saved_at
FROM (
    SELECT c.content_id, c.text, 1 - (c.embedding <=> CAST(:emb AS vector)) AS similarity
    FROM content_chunks c
    WHERE c.user_id = :uid AND c.embedding_model = :model
    ORDER BY c.embedding <=> CAST(:emb AS vector)
    LIMIT :k
) x
JOIN saved_content s ON s.id = x.content_id AND s.user_id = :uid
ORDER BY x.similarity DESC
"""

_DOCS_SQL = """
SELECT id, title, url, notes, saved_at FROM saved_content WHERE user_id = :uid AND id = ANY(:ids)
"""


def configure_filtered_ann(session, k: int) -> None:
    """Make the next HNSW queries in this transaction return k rows despite a per-user filter.

    HNSW returns at most ef_search candidates before the WHERE clause runs, so a filter on
    user_id can leave a user with fewer than k results (or none). With iterative scan
    (pgvector >= 0.8) the index keeps scanning until k rows pass the filter. Settings are
    transaction-local (set_config(..., true)). Postgres only.

    Every statement is a network round trip (about 250 ms between a Hugging Face Space and a Supabase
    project in another region), so this is one statement, and it is skipped when the current
    transaction already has the settings with an ef_search at least this large (a request that runs
    several ANN queries used to repeat both set_config calls before each of them).
    """
    ef = max(k, 40)
    real = _real_session(session)
    transaction = real.get_transaction()
    configured = real.info.get("ann_config")
    if transaction is not None and configured is not None and configured[0] is transaction and configured[1] >= ef:
        return
    session.execute(
        text("SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true), set_config('hnsw.ef_search', :ef, true)"),
        {"ef": str(ef)})
    real.info["ann_config"] = (real.get_transaction(), ef)


def _real_session(session):
    """The Session behind a Flask-SQLAlchemy scoped_session (which proxies only some Session methods)."""
    from sqlalchemy.orm import scoped_session
    return session() if isinstance(session, scoped_session) else session


def user_has_chunks(session, user_id: int) -> bool:
    return session.execute(
        text("SELECT 1 FROM content_chunks WHERE user_id = :uid AND embedding_model = :model LIMIT 1"),
        {"uid": user_id, "model": active_embedding_model_name()}
    ).first() is not None


# Nearest saved-text passages only. The 'profile' row is Gemini's own description of an item: right for
# matching intent, wrong as evidence for an answer that must come from what the user actually saved.
_PASSAGES_SQL = """
SELECT c.content_id, c.chunk_index, c.text, 1 - (c.embedding <=> CAST(:emb AS vector)) AS similarity
FROM content_chunks c
WHERE c.user_id = :uid AND c.embedding_model = :model AND c.kind = 'passage'
ORDER BY c.embedding <=> CAST(:emb AS vector)
LIMIT :k
"""


def nearest_passages(session, user_id: int, query_vector, k: int = CANDIDATES_PER_QUERY) -> List[Dict[str, Any]]:
    """Every nearest passage (several per bookmark allowed), best first. For answering, not ranking."""
    configure_filtered_ann(session, k)
    rows = session.execute(text(_PASSAGES_SQL), {
        "emb": _vec_literal(query_vector), "uid": user_id, "k": k, "model": active_embedding_model_name(),
    })
    return [{"content_id": cid, "chunk_index": idx, "passage": passage, "similarity": float(sim)}
            for cid, idx, passage, sim in rows]


def retrieve(session, user_id: int, query_vectors: Sequence, k: int = CANDIDATES_PER_QUERY) -> List[Dict[str, Any]]:
    """Union of nearest passages across query vectors; one entry per bookmark with its best passage."""
    configure_filtered_ann(session, k)

    model = active_embedding_model_name()
    best: Dict[int, Dict[str, Any]] = {}
    for vec in query_vectors:
        for content_id, passage, sim, title, url, notes, saved_at in session.execute(
            text(_ANN_SQL), {"emb": _vec_literal(vec), "uid": user_id, "k": k, "model": model}
        ):
            sim = float(sim)
            if content_id not in best or sim > best[content_id]["similarity"]:
                best[content_id] = {"content_id": content_id, "passage": passage, "similarity": sim,
                                    "id": content_id, "title": title, "url": url, "notes": notes,
                                    "saved_at": saved_at}
    return sorted(best.values(), key=lambda r: r["similarity"], reverse=True)


def semantic_search(session, user_id: int, query: str, limit: int = 10,
                    rerank: Optional[bool] = None, query_vector=None) -> List[Dict[str, Any]]:
    """Rank a user's bookmarks for a query by passage meaning; best passage returned as the snippet."""
    if rerank is None:
        rerank = rerank_enabled()
    started = time.perf_counter()

    candidates = retrieve(session, user_id, [query_vector if query_vector is not None else embed_query(query)])
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

    missing = [c["content_id"] for c in pool if "title" not in c]
    if missing:  # retrieve() normally returns the details already; this is for any other source of candidates
        docs = {d["id"]: dict(d) for d in session.execute(
            text(_DOCS_SQL), {"uid": user_id, "ids": missing}
        ).mappings()}
        for c in pool:
            if "title" not in c:
                c.update(docs.get(c["content_id"], {}))

    logger.info("passage_search_completed", extra={
        "user_id": user_id, "rerank": bool(rerank), "results": len(pool),
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    })
    return pool
