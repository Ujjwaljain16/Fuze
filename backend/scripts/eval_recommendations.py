#!/usr/bin/env python3
"""
Offline evaluation of the recommendation engine (ml/intent_engine) on a BEIR dataset,
run end-to-end through engine.recommend() against a real Postgres + pgvector database.

How a public IR dataset becomes a recommendation benchmark:
  - corpus documents -> one synthetic user's bookmarks (title + text; passages chunked and
    embedded exactly as the production pipeline does)
  - each test query   -> a project owned by that user: title = first 8 words of the query,
    description = the full query (empty when the query is 8 words or fewer)
  - qrels             -> relevance (graded where the dataset grades)
  recommend(project_id=...) is then scored against the qrels.

Configurations compared (all on the same loaded data):
  - MMR lambda 1.0 (no diversity), 0.7 (production), 0.5
  - intent augmentation off (the user's own words: what production serves until the Gemini
    statement is cached) vs a template statement standing in for Gemini (see TEMPLATE below;
    it measures the extra-query-vector mechanism, not Gemini's quality)
  - the same intent expressed as a task under a generic project, and as a raw query
  - cross-encoder reranker on vs off, on a seeded sample of queries (CPU cost)
  - multi-user: the corpus split into disjoint per-user slices; checks that no result ever
    belongs to another user and that HNSW with the per-user filter keeps recall vs exact search

Metrics: nDCG@10, MRR@10, Recall@20, intra-list diversity (mean pairwise cosine distance of
the top 10), catalog coverage, latency p50/p95 of recommend() (query embeddings precomputed;
encoder time is reported separately).

Usage (from backend/, against a throwaway local database migrated to head; --load deletes and
recreates the benchmark users; .env is deliberately not read):
    APP_ENV=development python scripts/eval_recommendations.py \\
        --db-url postgresql://postgres:test@localhost:55432/fz_receval --data-dir ~/.cache/fuze-beir/scifact --load
    APP_ENV=development python scripts/eval_recommendations.py --db-url ... --data-dir ...   # re-run, no reload
BEIR datasets: https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/<name>.zip
"""

import argparse
import contextlib
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence
from unittest import mock

import numpy as np

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

TITLE_WORDS = 8
TASK_PROJECT_TITLE = "Literature review"
URL_PREFIX = "beir://"
# Stand-in for the Gemini intent statement. Deterministic and grounded only in the user's words.
TEMPLATE = "They are researching {title}. They need studies and evidence about: {text}"


# --------------------------------------------------------------------------- dataset

@dataclass
class EvalSet:
    name: str
    docs: List[Dict]                        # [{"_id", "title", "text"}]
    queries: Dict[str, str]                 # qid -> text
    qrels: Dict[str, Dict[str, int]]        # qid -> {doc_id: grade>0}
    info: Dict = field(default_factory=dict)


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _read_qrels(path):
    qrels: Dict[str, Dict[str, int]] = {}
    with open(path, encoding="utf-8") as f:
        next(f)
        for line in f:
            qid, did, score = line.rstrip("\n").split("\t")
            if int(score) > 0:
                qrels.setdefault(qid, {})[did] = int(score)
    return qrels


def load_beir(data_dir: str, split: str = "test", max_docs: int = 5000, max_queries: int = 0,
              seed: int = 13) -> EvalSet:
    """A BEIR dataset, capped at max_docs: every document relevant to an evaluated query is kept,
    the rest is a seeded random sample of the other documents (distractors)."""
    corpus = _read_jsonl(os.path.join(data_dir, "corpus.jsonl"))
    queries = {q["_id"]: q["text"] for q in _read_jsonl(os.path.join(data_dir, "queries.jsonl"))}
    qrels = _read_qrels(os.path.join(data_dir, "qrels", f"{split}.tsv"))
    by_id = {d["_id"]: d for d in corpus}
    qids = sorted(q for q in qrels if q in queries and any(d in by_id for d in qrels[q]))
    rnd = random.Random(seed)
    if max_queries and len(qids) > max_queries:
        qids = sorted(rnd.sample(qids, max_queries))

    relevant = sorted({d for q in qids for d in qrels[q] if d in by_id})
    others = sorted(d for d in by_id if d not in set(relevant))
    n_other = len(others) if not max_docs else max(0, min(len(others), max_docs - len(relevant)))
    keep = set(relevant) | set(rnd.sample(others, n_other))
    docs = [by_id[d] for d in sorted(keep)]
    grades = sorted({g for q in qids for g in qrels[q].values()})
    return EvalSet(
        name=os.path.basename(os.path.normpath(data_dir)),
        docs=docs,
        queries={q: queries[q] for q in qids},
        qrels={q: {d: g for d, g in qrels[q].items() if d in keep} for q in qids},
        info={"split": split, "corpus_size": len(corpus), "documents": len(docs),
              "queries": len(qids), "relevance_grades": grades,
              "mean_relevant_per_query": round(float(np.mean([len(qrels[q]) for q in qids])), 2),
              "sampled": len(docs) < len(corpus), "seed": seed},
    )


def project_context(query_text: str):
    """(title, description) for the project standing in for a query."""
    words = query_text.split()
    title = " ".join(words[:TITLE_WORDS])[:100]
    description = query_text if len(words) > TITLE_WORDS else ""
    return title, description


def partition(evalset: EvalSet, n_users: int, seed: int = 13):
    """Disjoint per-user slices. Each query goes to one user (seeded round robin), who owns the
    documents relevant to it; a document relevant to queries of several users goes to the first.
    Distractors are dealt round robin. Qrels are restricted to what the query's user owns;
    queries left with no owned relevant document are dropped (and counted)."""
    rnd = random.Random(seed)
    qids = sorted(evalset.queries)
    rnd.shuffle(qids)
    owner_of_query = {q: i % n_users for i, q in enumerate(qids)}
    owner_of_doc: Dict[str, int] = {}
    for q in qids:
        for d in sorted(evalset.qrels[q]):
            owner_of_doc.setdefault(d, owner_of_query[q])
    rest = [d["_id"] for d in evalset.docs if d["_id"] not in owner_of_doc]
    rnd.shuffle(rest)
    for i, d in enumerate(rest):
        owner_of_doc[d] = i % n_users

    slices = []
    for u in range(n_users):
        owned = {d for d, o in owner_of_doc.items() if o == u}
        uq = {q: evalset.queries[q] for q in sorted(evalset.queries) if owner_of_query[q] == u}
        uqrels = {q: {d: g for d, g in evalset.qrels[q].items() if d in owned} for q in uq}
        uq = {q: t for q, t in uq.items() if uqrels[q]}
        slices.append({"docs": sorted(owned), "queries": uq, "qrels": {q: uqrels[q] for q in uq}})
    dropped = len(evalset.queries) - sum(len(s["queries"]) for s in slices)
    return slices, dropped


# --------------------------------------------------------------------------- embeddings

def real_embedder():
    """(model name, passage encoder, query encoder) using the production embedding model."""
    from utils import embedding_utils as eu
    eu.get_embedding_model()
    name = eu.active_embedding_model_name()
    query_prefix = eu._prefixes(name)[0]
    model = eu.get_embedding_model()

    def passages(texts):
        return np.asarray(eu.get_embeddings_batch(list(texts)), dtype=np.float32)

    def queries(texts):
        clean = [query_prefix + t.strip()[:eu.MAX_EMBED_TEXT_LENGTH] for t in texts]
        return np.asarray(model.encode(clean, batch_size=32), dtype=np.float32)

    return name, passages, queries


MISSES: List[str] = []


@contextlib.contextmanager
def engine_embeddings(model_name: str, query_vectors: Dict[str, np.ndarray],
                      encode_queries: Callable[[Sequence[str]], np.ndarray]):
    """Serve query vectors from a precomputed table (encoding misses on the fly), so latency
    measures retrieval, not the encoder, and the run never touches Redis."""
    def embed_query(text):
        if text not in query_vectors:
            MISSES.append(text)   # encoded inside a timed call: should stay empty
            query_vectors[text] = encode_queries([text])[0]
        return query_vectors[text]

    with mock.patch("utils.embedding_utils.embed_query", embed_query), \
         mock.patch("utils.embedding_utils.active_embedding_model_name", lambda: model_name), \
         mock.patch("services.hybrid_search.embed_query", embed_query), \
         mock.patch("services.hybrid_search.active_embedding_model_name", lambda: model_name):
        yield


# --------------------------------------------------------------------------- loading

def _postgres(session) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def embed_corpus(evalset: EvalSet, encode_passages, log=print):
    """Document vectors (title | first 5000 chars, as the pipeline embeds) and passage vectors."""
    from utils.chunking import chunk_text
    t0 = time.time()
    doc_texts = [" | ".join(p for p in (d.get("title", ""), d["text"][:5000]) if p) for d in evalset.docs]
    doc_vecs = encode_passages(doc_texts)
    passages, owners = [], []
    for d in evalset.docs:
        for i, p in enumerate(chunk_text(d.get("title", ""), d["text"])):
            passages.append(p)
            owners.append((d["_id"], i))
    passage_vecs = encode_passages(passages) if passages else np.zeros((0, doc_vecs.shape[1]), np.float32)
    log(f"  embedded {len(doc_texts)} documents and {len(passages)} passages ({time.time() - t0:.0f}s)")
    return ({d["_id"]: v for d, v in zip(evalset.docs, doc_vecs)},
            {"passages": passages, "owners": owners, "vecs": passage_vecs})


def load_user(session, username: str, docs: List[Dict], queries: Dict[str, str], doc_vecs, passages,
              model_name: str, batch: int = 500) -> Dict:
    """Create one benchmark user with bookmarks, passage chunks and one project + task per query."""
    from sqlalchemy import text
    from models import Project, SavedContent, Task, User

    # Database-level ON DELETE CASCADE removes the old run's bookmarks, chunks and projects.
    session.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
    session.commit()
    user = User(username=username, email=f"{username}@example.invalid", password_hash="x")
    session.add(user)
    session.flush()

    content_ids: Dict[str, int] = {}
    for start in range(0, len(docs), batch):
        rows = []
        for d in docs[start:start + batch]:
            rows.append(SavedContent(
                user_id=user.id, url=URL_PREFIX + d["_id"], title=(d.get("title") or d["_id"])[:200],
                extracted_text=d["text"], embedding=doc_vecs[d["_id"]].tolist(),
                embedding_metadata={"model": model_name}, scrape_status="SUCCESS", embedding_status="SUCCESS"))
        session.add_all(rows)
        session.flush()
        content_ids.update({r.url[len(URL_PREFIX):]: r.id for r in rows})

    n_chunks = 0
    if _postgres(session):
        from services.hybrid_search import _vec_literal
        params = [{"cid": content_ids[did], "uid": user.id, "idx": i, "text": p, "emb": _vec_literal(v),
                   "model": model_name}
                  for (did, i), p, v in zip(passages["owners"], passages["passages"], passages["vecs"])
                  if did in content_ids]
        for start in range(0, len(params), 1000):
            session.execute(text(
                "INSERT INTO content_chunks (content_id, user_id, chunk_index, text, embedding, embedding_model) "
                "VALUES (:cid, :uid, :idx, :text, CAST(:emb AS vector), :model)"), params[start:start + 1000])
        n_chunks = len(params)

    projects, tasks = {}, {}
    review = Project(user_id=user.id, title=TASK_PROJECT_TITLE, description="")
    session.add(review)
    session.flush()
    for qid, qtext in queries.items():
        title, description = project_context(qtext)
        p = Project(user_id=user.id, title=title, description=description)
        t = Task(project_id=review.id, title=title, description=description)
        session.add_all([p, t])
        session.flush()
        projects[qid], tasks[qid] = p.id, t.id
    session.commit()
    return {"user_id": user.id, "content_ids": content_ids, "projects": projects, "tasks": tasks,
            "chunks": n_chunks}


def find_user(session, username: str, queries: Dict[str, str]) -> Optional[Dict]:
    """Ids of an already-loaded benchmark user (re-runs without --load)."""
    from models import Project, SavedContent, Task, User
    user = session.query(User).filter_by(username=username).first()
    if user is None:
        return None
    content_ids = {u[len(URL_PREFIX):]: i for i, u in session.query(SavedContent.id, SavedContent.url)
                   .filter(SavedContent.user_id == user.id)}
    by_title = {}
    for p in session.query(Project).filter(Project.user_id == user.id,
                                           Project.title != TASK_PROJECT_TITLE).order_by(Project.id):
        by_title.setdefault((p.title, p.description or ""), []).append(p.id)
    task_by_title = {}
    for t in (session.query(Task).join(Project, Task.project_id == Project.id)
              .filter(Project.user_id == user.id).order_by(Task.id)):
        task_by_title.setdefault((t.title, t.description or ""), []).append(t.id)
    projects, tasks = {}, {}
    for qid, qtext in sorted(queries.items()):
        key = project_context(qtext)
        if not by_title.get(key) or not task_by_title.get(key):
            return None
        projects[qid] = by_title[key].pop(0)
        tasks[qid] = task_by_title[key].pop(0)
    return {"user_id": user.id, "content_ids": content_ids, "projects": projects, "tasks": tasks}


# --------------------------------------------------------------------------- metrics

def ndcg_at_k(ranked, rels, k=10):
    dcg = sum(rels.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked[:k]))
    ideal = sorted(rels.values(), reverse=True)[:k]
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def recall_at_k(ranked, rels, k):
    return len(set(ranked[:k]) & set(rels)) / len(rels) if rels else 0.0


def mrr_at_k(ranked, rels, k=10):
    for i, d in enumerate(ranked[:k]):
        if d in rels:
            return 1.0 / (i + 1)
    return 0.0


def intra_list_diversity(ranked, doc_vecs, k=10) -> Optional[float]:
    """Mean pairwise cosine distance between the top-k documents' vectors."""
    vecs = [doc_vecs[d] for d in ranked[:k] if d in doc_vecs]
    if len(vecs) < 2:
        return None
    m = np.asarray(vecs, dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    sims = m @ m.T
    iu = np.triu_indices(len(vecs), 1)
    return float(np.mean(1.0 - sims[iu]))


def bootstrap_ci(values, n=1000, seed=7):
    """95% percentile bootstrap interval of the mean."""
    if not values:
        return [0.0, 0.0]
    rnd = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=np.float64)
    means = arr[rnd.integers(0, len(arr), size=(n, len(arr)))].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def summarize(per_query: List[Dict], n_docs: int) -> Dict:
    lat = sorted(r["latency_ms"] for r in per_query)
    ild = [r["ild"] for r in per_query if r["ild"] is not None]
    seen = {d for r in per_query for d in r["top10"]}
    ndcg = [r["ndcg@10"] for r in per_query]
    return {
        "queries": len(per_query),
        "ndcg@10": round(float(np.mean(ndcg)), 4),
        "ndcg@10_ci95": bootstrap_ci(ndcg),
        "mrr@10": round(float(np.mean([r["mrr@10"] for r in per_query])), 4),
        "recall@20": round(float(np.mean([r["recall@20"] for r in per_query])), 4),
        "ild@10": round(float(np.mean(ild)), 4) if ild else None,
        "catalog_coverage@10": round(len(seen) / n_docs, 4) if n_docs else 0.0,
        "query_coverage": round(sum(1 for r in per_query if r["top10"]) / len(per_query), 4) if per_query else 0.0,
        "latency_p50_ms": round(float(np.percentile(lat, 50)), 1) if lat else None,
        "latency_p95_ms": round(float(np.percentile(lat, 95)), 1) if lat else None,
        "leaked_results": sum(r["leaks"] for r in per_query),
    }


# --------------------------------------------------------------------------- running

@dataclass
class Config:
    name: str
    mmr_lambda: float = 0.7
    intent: str = "off"          # off | template
    mode: str = "project"        # project | task | query
    rerank: bool = False


def template_statement(intent) -> Optional[str]:
    ctx = intent.context
    title = ctx.task_title or ctx.project_title or ctx.query
    body = ctx.task_description or ctx.project_description or ctx.query or title
    return TEMPLATE.format(title=title, text=body) if title else None


@contextlib.contextmanager
def configured_engine(cfg: Config):
    """Set MMR lambda and the intent statement source for the duration of one configuration."""
    from ml.intent_engine import engine
    from ml.intent_engine.intent import Intent, _hash, compose_intent_text

    def resolve(ctx):
        # resolve_intent() minus the Redis lookup and job scheduling: never a cached Gemini statement.
        text = compose_intent_text(ctx)
        intent = Intent(context=ctx, text=text, hash=_hash(text))
        if cfg.intent == "template" and text:
            intent.statement = template_statement(intent)
        return intent

    # The response-cache key reads a per-user content version from Redis even with use_cache=False;
    # pin it so latency is the engine's (Postgres + Python), not a Redis round trip.
    with mock.patch.object(engine, "MMR_LAMBDA", cfg.mmr_lambda), \
         mock.patch.object(engine, "resolve_intent", resolve), \
         mock.patch("utils.content_version.get_content_version", lambda user_id: 0):
        yield engine


def intent_texts(cfg: Config, user: Dict, evalset_queries: Dict[str, str]) -> List[str]:
    """All texts the engine will embed for this configuration (for precomputing vectors)."""
    from ml.intent_engine.intent import Intent, IntentContext, compose_intent_text
    out = []
    for qid, qtext in evalset_queries.items():
        title, description = project_context(qtext)
        if cfg.mode == "project":
            ctx = IntentContext(user_id=0, project_title=title, project_description=description)
        elif cfg.mode == "task":
            ctx = IntentContext(user_id=0, project_title=TASK_PROJECT_TITLE, task_title=title,
                                task_description=description)
        else:
            ctx = IntentContext(user_id=0, query=qtext)
        text = compose_intent_text(ctx)
        out.append(text)
        if cfg.intent == "template":
            out.append(template_statement(Intent(context=ctx, text=text, hash="")))
    return out


def run_config(session, cfg: Config, users: List[Dict], doc_vecs: Dict[str, np.ndarray],
               qids_subset: Optional[set] = None) -> List[Dict]:
    """recommend() for every (user, query); one row of metrics per query."""
    rows = []
    with configured_engine(cfg) as engine:
        for u in users:
            owner_ids = set(u["content_ids"].values())
            for qid in sorted(u["queries"]):
                if qids_subset is not None and qid not in qids_subset:
                    continue
                kwargs = {"project": {"project_id": u["projects"].get(qid)},
                          "task": {"task_id": u["tasks"].get(qid)},
                          "query": {"query": u["queries"][qid]}}[cfg.mode]
                t = time.perf_counter()
                res10 = engine.recommend(session, u["user_id"], limit=10, rerank=cfg.rerank, use_cache=False, **kwargs)
                latency = (time.perf_counter() - t) * 1000
                session.rollback()
                res20 = engine.recommend(session, u["user_id"], limit=20, rerank=cfg.rerank, use_cache=False, **kwargs)
                session.rollback()
                leaks = sum(1 for r in res10["results"] + res20["results"] if r["id"] not in owner_ids)
                top10 = [r["url"][len(URL_PREFIX):] for r in res10["results"]]
                top20 = [r["url"][len(URL_PREFIX):] for r in res20["results"]]
                rels = u["qrels"][qid]
                rows.append({"qid": qid, "top10": top10, "latency_ms": latency, "leaks": leaks,
                             "ndcg@10": ndcg_at_k(top10, rels), "mrr@10": mrr_at_k(top10, rels),
                             "recall@20": recall_at_k(top20, rels, 20),
                             "ild": intra_list_diversity(top10, doc_vecs)})
    return rows


def ann_recall(session, users: List[Dict], query_vectors: Dict[str, np.ndarray], texts_by_qid: Dict[str, str],
               model_name: str, k: int = 60, force_hnsw: bool = False) -> Dict:
    """Recall of the production passage ANN query (per-user filter, HNSW iterative scan) against
    exact search for the same user, at the chunk level, plus the plan Postgres chose.

    On a small table the planner reads the user's rows through the (user_id, model) b-tree and
    sorts them, which is exact. force_hnsw makes it walk the HNSW graph with the user filter, as
    it would for large libraries: inside the (rolled back) transaction the b-tree is dropped and
    sequential/bitmap scans are disabled. Only for a throwaway benchmark database."""
    from sqlalchemy import text
    from services.hybrid_search import _vec_literal
    sql = ("SELECT c.id FROM content_chunks c WHERE c.user_id = :uid AND c.embedding_model = :model "
           "ORDER BY c.embedding <=> CAST(:emb AS vector) LIMIT :k")
    recalls, plan = [], None
    for u in users:
        for qid in sorted(u["queries"]):
            p = {"uid": u["user_id"], "model": model_name, "k": k,
                 "emb": _vec_literal(query_vectors[texts_by_qid[qid]])}
            session.execute(text("SELECT set_config('hnsw.iterative_scan', 'relaxed_order', true)"))
            session.execute(text("SELECT set_config('hnsw.ef_search', :ef, true)"), {"ef": str(max(k, 40))})
            if force_hnsw:
                session.execute(text("SET LOCAL enable_seqscan = off"))
                session.execute(text("SET LOCAL enable_bitmapscan = off"))
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
                session.execute(text("DROP INDEX IF EXISTS idx_content_chunks_user_model"))
            if plan is None:
                plan = [r[0] for r in session.execute(text("EXPLAIN (COSTS OFF) " + sql), p)]
            ann = {r[0] for r in session.execute(text(sql), p)}
            session.rollback()
            session.execute(text("SET LOCAL enable_indexscan = off"))
            exact = {r[0] for r in session.execute(text(sql), p)}
            session.rollback()
            if exact:
                recalls.append(len(ann & exact) / len(exact))
    uses_hnsw = any("hnsw" in line for line in (plan or []))
    return {"k": k, "queries": len(recalls), "forced_hnsw": force_hnsw, "mean_recall_vs_exact": round(float(np.mean(recalls)), 4) if recalls else None,
            "min_recall_vs_exact": round(float(np.min(recalls)), 4) if recalls else None,
            "plan_uses_hnsw": uses_hnsw, "plan": plan}


# --------------------------------------------------------------------------- reporting

def git_info():
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=backend_dir, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--", "."], cwd=backend_dir, text=True).strip())
        return {"sha": sha, "dirty": dirty}
    except Exception:
        return {"sha": None, "dirty": None}


def markdown_summary(out: Dict) -> str:
    ds = out["dataset"]
    lines = [
        f"# Recommendation engine offline evaluation: {ds['name']}",
        "",
        f"- Generated: {out['generated_at']} | git `{(out['git']['sha'] or 'unknown')[:10]}`"
        f"{' (dirty)' if out['git']['dirty'] else ''}",
        f"- Dataset: BEIR {ds['name']} ({ds['split']} split): {ds['documents']} documents"
        f"{' (sampled from ' + str(ds['corpus_size']) + ')' if ds['sampled'] else ''}, {ds['queries']} queries, "
        f"relevance grades {ds['relevance_grades']}, {ds['mean_relevant_per_query']} relevant docs per query on average",
        f"- Embedding model: {out['embedding_model']}; {out['chunks_single_user']} passages for the single user",
        f"- Engine: {out['engine']['candidates_per_query']} ANN candidates per query vector, pool "
        f"{out['engine']['pool']}, results 10 (Recall@20 from a separate limit=20 call)",
        f"- Context: project title = first {TITLE_WORDS} words of the query, description = full query",
        "",
        "| configuration | nDCG@10 (95% CI) | MRR@10 | Recall@20 | ILD@10 | coverage@10 | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, r in out["results"].items():
        lines.append(f"| {name} | {r['ndcg@10']:.4f} ({r['ndcg@10_ci95'][0]:.3f}-{r['ndcg@10_ci95'][1]:.3f}) | "
                     f"{r['mrr@10']:.4f} | {r['recall@20']:.4f} | {r['ild@10']:.4f} | {r['catalog_coverage@10']:.3f} | "
                     f"{r['latency_p50_ms']} | {r['latency_p95_ms']} |")
    if out.get("rerank"):
        rr = out["rerank"]
        lines += ["", f"Reranker (cross-encoder, CPU) on a seeded sample of {rr['sample_queries']} queries, "
                      f"MMR 0.7, intent off:", "",
                  "| | nDCG@10 | MRR@10 | Recall@20 | p50 ms | p95 ms |", "|---|---|---|---|---|---|"]
        for k in ("off", "on"):
            r = rr[k]
            lines.append(f"| rerank {k} | {r['ndcg@10']:.4f} | {r['mrr@10']:.4f} | {r['recall@20']:.4f} | "
                         f"{r['latency_p50_ms']} | {r['latency_p95_ms']} |")
    mu = out.get("multi_user")
    if mu:
        lines += ["", f"Multi-user: {mu['users']} users with disjoint slices "
                      f"({min(mu['docs_per_user'])}-{max(mu['docs_per_user'])} docs each), {mu['queries']} queries "
                      f"({mu['dropped_queries']} dropped: no owned relevant doc). Same database also holds the single user.",
                  "",
                  f"- Results belonging to another user: **{mu['metrics']['leaked_results']}**",
                  f"- nDCG@10 {mu['metrics']['ndcg@10']:.4f}, Recall@20 {mu['metrics']['recall@20']:.4f}, "
                  f"p50 {mu['metrics']['latency_p50_ms']} ms (relevance restricted to each user's own slice)"]
    if out.get("ann_recall"):
        lines += ["", "Passage ANN recall@60 against exact search for the same user (production query: "
                      "per-user filter, hnsw.iterative_scan=relaxed_order, ef_search=60):", "",
                  "| library | planner's choice | recall (mean / min) | HNSW forced: recall (mean / min) |",
                  "|---|---|---|---|"]
        for label, r in out["ann_recall"].items():
            p, f = r["planner"], r["forced_hnsw"]
            lines.append(f"| {label.replace('_', ' ')} | {'HNSW' if p['plan_uses_hnsw'] else 'b-tree + sort (exact)'} | "
                         f"{p['mean_recall_vs_exact']} / {p['min_recall_vs_exact']} | "
                         f"{f['mean_recall_vs_exact']} / {f['min_recall_vs_exact']}"
                         f"{'' if f['plan_uses_hnsw'] else ' (HNSW not used!)'} |")
    lines += ["", f"Query encoding ({out['embedding_model']}, CPU, one text): p50 "
                  f"{out['query_encode_ms']['p50']} ms, p95 {out['query_encode_ms']['p95']} ms; not included in "
                  "the latencies above (production caches query vectors in Redis).", "",
              "Caveats: `intent=template` replaces the Gemini statement with a fixed template built from the "
              "same words, so it measures the extra query vector, not Gemini. Queries are dataset queries "
              "rewritten as project contexts, not real users' projects."]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- main

DEFAULT_CONFIGS = [
    Config("mmr1.0_intent-off", 1.0, "off"),
    Config("mmr0.7_intent-off", 0.7, "off"),
    Config("mmr0.5_intent-off", 0.5, "off"),
    Config("mmr1.0_intent-template", 1.0, "template"),
    Config("mmr0.7_intent-template", 0.7, "template"),
    Config("mmr0.5_intent-template", 0.5, "template"),
    Config("mmr0.7_intent-off_task", 0.7, "off", mode="task"),
    Config("mmr0.7_intent-off_query", 0.7, "off", mode="query"),
]


def evaluate(session, evalset: EvalSet, model_name: str, encode_passages, encode_queries, *,
             load: bool, configs: Sequence[Config] = tuple(DEFAULT_CONFIGS), users: int = 4,
             rerank_sample: int = 100, username_prefix: str = "receval", log=print) -> Dict:
    """Load (optionally) and evaluate; returns the result document."""
    from ml.intent_engine import engine as rec_engine

    tag = hashlib.md5(f"{evalset.name}:{len(evalset.docs)}:{len(evalset.queries)}:{model_name}".encode()).hexdigest()[:10]
    single_name = f"{username_prefix}_{tag}_single"
    slices, dropped = partition(evalset, users) if users > 1 else ([], 0)
    docs_by_id = {d["_id"]: d for d in evalset.docs}

    doc_vecs = passages = None
    if load:
        doc_vecs, passages = embed_corpus(evalset, encode_passages, log)
    single = find_user(session, single_name, evalset.queries) if not load else None
    if single is None:
        if doc_vecs is None:
            doc_vecs, passages = embed_corpus(evalset, encode_passages, log)
        log(f"  loading single user ({len(evalset.docs)} docs)")
        single = load_user(session, single_name, evalset.docs, evalset.queries, doc_vecs, passages, model_name)
    single.update({"queries": evalset.queries, "qrels": evalset.qrels})

    multi = []
    for i, s in enumerate(slices):
        name = f"{username_prefix}_{tag}_mu{users}_{i}"
        u = find_user(session, name, s["queries"]) if not load else None
        if u is None:
            if doc_vecs is None:
                doc_vecs, passages = embed_corpus(evalset, encode_passages, log)
            log(f"  loading user {i + 1}/{users} ({len(s['docs'])} docs)")
            u = load_user(session, name, [docs_by_id[d] for d in s["docs"]], s["queries"], doc_vecs, passages, model_name)
        u.update({"queries": s["queries"], "qrels": s["qrels"]})
        multi.append(u)
    if _postgres(session) and load:
        from sqlalchemy import text
        session.execute(text("ANALYZE saved_content"))
        session.execute(text("ANALYZE content_chunks"))
        session.commit()

    if doc_vecs is None:   # re-run: read the stored document vectors back for diversity
        from models import SavedContent
        doc_vecs = {}
        for url, emb in session.query(SavedContent.url, SavedContent.embedding).filter(
                SavedContent.user_id == single["user_id"]):
            doc_vecs[url[len(URL_PREFIX):]] = np.asarray(emb, dtype=np.float32)

    # Precompute every query vector the engine will ask for.
    query_vectors: Dict[str, np.ndarray] = {}
    wanted = sorted({t for cfg in list(configs) + [Config("base")]
                     for t in intent_texts(cfg, single, evalset.queries)})
    log(f"  encoding {len(wanted)} intent texts")
    for start in range(0, len(wanted), 64):
        chunk = wanted[start:start + 64]
        for t, v in zip(chunk, encode_queries(chunk)):
            query_vectors[t] = v
    enc = []
    for t in wanted[:30]:
        t0 = time.perf_counter()
        encode_queries([t])
        enc.append((time.perf_counter() - t0) * 1000)

    results, per_query = {}, {}
    MISSES.clear()
    with engine_embeddings(model_name, query_vectors, encode_queries):
        # Warm-up: first calls pay for imports and connection setup.
        warm = Config("warmup")
        run_config(session, warm, [{**single, "queries": dict(list(single["queries"].items())[:3])}], doc_vecs)
        for cfg in configs:
            t0 = time.time()
            rows = run_config(session, cfg, [single], doc_vecs)
            per_query[cfg.name] = rows
            results[cfg.name] = {**summarize(rows, len(evalset.docs)),
                                 "config": {"mmr_lambda": cfg.mmr_lambda, "intent": cfg.intent, "mode": cfg.mode,
                                            "rerank": cfg.rerank}}
            r = results[cfg.name]
            log(f"  {cfg.name:28} nDCG@10={r['ndcg@10']:.4f} MRR={r['mrr@10']:.4f} R@20={r['recall@20']:.4f} "
                f"ILD={r['ild@10']} cov={r['catalog_coverage@10']} p50={r['latency_p50_ms']}ms "
                f"p95={r['latency_p95_ms']}ms ({time.time() - t0:.0f}s)")

        rerank = None
        if rerank_sample:
            sample = set(random.Random(5).sample(sorted(evalset.queries), min(rerank_sample, len(evalset.queries))))
            base = Config("rerank-off", 0.7, "off")
            on = Config("rerank-on", 0.7, "off", rerank=True)
            from utils.reranker import rerank_passages
            if rerank_passages("warmup", ["warmup passage"]) is not None:
                rerank = {"sample_queries": len(sample),
                          "off": summarize(run_config(session, base, [single], doc_vecs, sample), len(evalset.docs)),
                          "on": summarize(run_config(session, on, [single], doc_vecs, sample), len(evalset.docs))}
                log(f"  rerank sample ({len(sample)}): off nDCG@10={rerank['off']['ndcg@10']:.4f} "
                    f"p50={rerank['off']['latency_p50_ms']}ms | on nDCG@10={rerank['on']['ndcg@10']:.4f} "
                    f"p50={rerank['on']['latency_p50_ms']}ms")
            else:
                log("  reranker unavailable; skipped")

        multi_out = None
        if multi:
            rows = run_config(session, Config("multi", 0.7, "off"), multi, doc_vecs)
            multi_out = {"users": users, "docs_per_user": [len(s["docs"]) for s in slices],
                         "queries": len(rows), "dropped_queries": dropped,
                         "metrics": summarize(rows, len(evalset.docs))}
            log(f"  multi-user ({users}): leaks={multi_out['metrics']['leaked_results']} "
                f"nDCG@10={multi_out['metrics']['ndcg@10']:.4f} R@20={multi_out['metrics']['recall@20']:.4f}")

    project_text = {qid: intent_texts(Config("x"), single, {qid: q})[0] for qid, q in evalset.queries.items()}
    ann = None
    if _postgres(session):
        ann = {}
        for label, group in (("single_user", [single]), ("multi_user", multi)):
            if not group:
                continue
            ann[label] = {"planner": ann_recall(session, group, query_vectors, project_text, model_name),
                          "forced_hnsw": ann_recall(session, group, query_vectors, project_text, model_name,
                                                    force_hnsw=True)}
            log(f"  ANN recall@60 vs exact, {label}: " + ", ".join(
                f"{k}={v['mean_recall_vs_exact']} (min {v['min_recall_vs_exact']}, hnsw={v['plan_uses_hnsw']})"
                for k, v in ann[label].items()))

    from sqlalchemy import text
    n_chunks = session.execute(text("SELECT count(*) FROM content_chunks WHERE user_id = :u"),
                               {"u": single["user_id"]}).scalar() if _postgres(session) else 0
    return {
        "dataset": {"name": evalset.name, **evalset.info},
        "embedding_model": model_name,
        "chunks_single_user": n_chunks,
        "engine": {"candidates_per_query": rec_engine.CANDIDATES_PER_QUERY,
                   "rerank_top_n": rec_engine.RERANK_TOP_N, "pool": "max(30, 3 x limit)",
                   "production_mmr_lambda": 0.7},
        "context_mapping": {"project_title": f"first {TITLE_WORDS} words of the query",
                            "project_description": f"full query when longer than {TITLE_WORDS} words",
                            "task_mode": f"task with the same title/description under a project titled "
                                         f"'{TASK_PROJECT_TITLE}'", "intent_template": TEMPLATE},
        "results": results,
        "rerank": rerank,
        "multi_user": multi_out,
        "ann_recall": ann,
        "query_encode_ms": {"p50": round(float(np.percentile(enc, 50)), 1) if enc else None,
                            "p95": round(float(np.percentile(enc, 95)), 1) if enc else None},
        "query_vectors_encoded_during_timing": len(MISSES),
        "per_query": {name: [{k: r[k] for k in ("qid", "ndcg@10", "recall@20", "mrr@10")} for r in rows]
                      for name, rows in per_query.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--load", action="store_true", help="(re)create the benchmark users and embed the corpus")
    ap.add_argument("--max-docs", type=int, default=5000)
    ap.add_argument("--max-queries", type=int, default=0)
    ap.add_argument("--users", type=int, default=4, help="users in the multi-user variant (0/1 = skip)")
    ap.add_argument("--rerank-sample", type=int, default=100, help="queries for the reranker comparison (0 = skip)")
    ap.add_argument("--out-dir", default=os.path.join(backend_dir, "eval", "results"))
    ap.add_argument("--threads", type=int, default=4, help="CPU threads for the encoders")
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5", help="embedding model (production default)")
    ap.add_argument("--redis-url", default="redis://127.0.0.1:6379/14",
                    help="local Redis for module imports; the run itself makes no Redis calls")
    ap.add_argument("--i-know", metavar="DB_HOST", help="Confirm a non-local or non-development target by typing its host")
    args = ap.parse_args()

    # No load_dotenv(): .env holds production settings (Redis, model choice) a benchmark must not pick up.
    from core.destructive_guard import require_safe_target
    require_safe_target(args.db_url)

    os.environ["DATABASE_URL"] = args.db_url
    os.environ["REDIS_URL"] = args.redis_url
    os.environ["EMBEDDING_MODEL_NAME"] = args.model
    import torch
    torch.set_num_threads(args.threads)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    evalset = load_beir(args.data_dir, max_docs=args.max_docs, max_queries=args.max_queries)
    print(f"{evalset.name}: {len(evalset.docs)} docs, {len(evalset.queries)} queries", flush=True)
    model_name, encode_passages, encode_queries = real_embedder()

    engine = create_engine(args.db_url)
    with Session(engine) as session:
        out = evaluate(session, evalset, model_name, encode_passages, encode_queries, load=args.load,
                       users=args.users, rerank_sample=args.rerank_sample,
                       log=lambda m: print(m, flush=True))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {"generated_at": stamp, "git": git_info(), **out}
    os.makedirs(args.out_dir, exist_ok=True)
    base = os.path.join(args.out_dir, f"recs_{evalset.name}_{model_name.split('/')[-1]}_{stamp}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(markdown_summary(out))
    print(f"\nSaved {base}.json and .md")


if __name__ == "__main__":
    main()
