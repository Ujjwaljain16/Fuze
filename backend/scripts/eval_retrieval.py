#!/usr/bin/env python3
"""
Retrieval quality benchmark on a BEIR dataset (default: SciFact), run end-to-end
against a real Postgres + pgvector database through the production search code.

Compares (meaning only, no keyword matching):
  doc_vector           current production search (one embedding per bookmark)
  chunk_vector         best-matching passage per bookmark
  chunk_vector_rerank  chunk_vector, top 30 reranked by a cross-encoder

Usage (from backend/, against a throwaway database -- it creates a user and
~5k bookmarks):
    python scripts/eval_retrieval.py --db-url postgresql://postgres:pw@127.0.0.1:5433/fuze_eval \\
        --data-dir /path/to/scifact --load
    python scripts/eval_retrieval.py --db-url ... --data-dir ...            # re-run without reloading
"""

import argparse
import json
import hashlib
import math
import os
import random
import statistics
import sys
import time
from datetime import datetime, timezone

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

METHODS = ["doc_vector", "chunk_vector", "chunk_vector_rerank"]


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_qrels(path):
    qrels = {}
    with open(path, encoding="utf-8") as f:
        next(f)
        for line in f:
            qid, did, score = line.rstrip("\n").split("\t")
            if int(score) > 0:
                qrels.setdefault(qid, {})[did] = int(score)
    return qrels


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


def make_long_docs(corpus, qrels, fillers, n_distractors, seed=13):
    """Bury each document inside a long document of unrelated abstracts.

    The original abstract is never placed first, so a retriever that only reads the
    beginning of a document (the model's token limit) cannot see it. Document ids are
    kept, so the original relevance labels still apply.
    """
    rnd = random.Random(seed)
    by_id = {d["_id"]: d for d in corpus}
    relevant = {d for rels in qrels.values() for d in rels if d in by_id}
    pool = sorted(d for d in by_id if d not in relevant)
    base = sorted(relevant) + rnd.sample(pool, min(n_distractors, len(pool)))
    out = []
    for did in base:
        fill = [by_id[x] for x in rnd.sample(pool, fillers + 1) if x != did][:fillers]
        pos = rnd.randint(1, fillers)
        parts = fill[:pos] + [by_id[did]] + fill[pos:]
        body = "\n\n".join(f"{p.get('title', '')}. {p['text']}" for p in parts)
        out.append({"_id": did, "title": parts[0].get("title", ""), "text": body})
    return out


def load_corpus(session, corpus, username, batch=256):
    from sqlalchemy import text
    from services.hybrid_search import _vec_literal
    from utils.chunking import chunk_text
    from utils.embedding_utils import get_embeddings_batch

    session.execute(text("DELETE FROM users WHERE username = :u"), {"u": username})
    user_id = session.execute(text(
        "INSERT INTO users (username, email, password_hash) VALUES (:u, :e, 'x') RETURNING id"
    ), {"u": username, "e": f"{username}@example.invalid"}).scalar()
    session.commit()

    from utils.embedding_utils import active_embedding_model_name
    model = active_embedding_model_name()
    t0 = time.time()
    for start in range(0, len(corpus), batch):
        docs = corpus[start:start + batch]
        # Same text the production pipeline embeds: "title | first 5000 chars of body"
        doc_texts = [" | ".join(p for p in (d.get("title", ""), d["text"][:5000]) if p) for d in docs]
        doc_vecs = get_embeddings_batch(doc_texts)
        ids = []
        for d, v in zip(docs, doc_vecs):
            ids.append(session.execute(text(
                "INSERT INTO saved_content (user_id, url, title, extracted_text, embedding) "
                "VALUES (:uid, :url, :title, :body, CAST(:emb AS vector)) RETURNING id"
            ), {"uid": user_id, "url": f"beir://{d['_id']}", "title": (d.get("title") or d["_id"])[:200],
                "body": d["text"], "emb": _vec_literal(v)}).scalar())

        passages, owners = [], []
        for cid, d in zip(ids, docs):
            for i, p in enumerate(chunk_text(d.get("title", ""), d["text"])):
                passages.append(p); owners.append((cid, i))
        pvecs = get_embeddings_batch(passages)
        session.execute(text(
            "INSERT INTO content_chunks (content_id, user_id, chunk_index, text, embedding, embedding_model) "
            "VALUES (:cid, :uid, :idx, :text, CAST(:emb AS vector), :model)"
        ), [{"cid": cid, "uid": user_id, "idx": i, "text": p, "emb": _vec_literal(v), "model": model}
            for (cid, i), p, v in zip(owners, passages, pvecs)])
        session.commit()
        print(f"  loaded {min(start + batch, len(corpus))}/{len(corpus)} docs ({time.time() - t0:.0f}s)", flush=True)
    session.execute(text("ANALYZE saved_content; ANALYZE content_chunks"))
    session.commit()
    return user_id


def run_method(method, session, user_id, query, k):
    from sqlalchemy import text
    if method == "doc_vector":
        from services.search_service import SearchService

        class _UoW:
            pass
        uow = _UoW(); uow.session = session
        session.execute(text("SELECT set_config('hnsw.ef_search', '100', true)"))
        return [r["url"] for r in SearchService(uow).semantic_search(user_id, query, k)]
    from services.hybrid_search import semantic_search
    return [r["url"] for r in semantic_search(session, user_id, query, limit=k,
                                              rerank=(method == "chunk_vector_rerank"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--max-queries", type=int, default=0)
    ap.add_argument("--methods", default=",".join(METHODS))
    ap.add_argument("--out-dir", default=os.path.join(backend_dir, "eval", "results"))
    ap.add_argument("--model", default="", help="EMBEDDING_MODEL_NAME to evaluate (default: configured model)")
    ap.add_argument("--long-docs", type=int, default=0,
                    help="bury each document among N unrelated abstracts (0 = original corpus)")
    ap.add_argument("--long-docs-distractors", type=int, default=2000)
    ap.add_argument("--i-know", metavar="DB_HOST", help="Confirm a non-local or non-development target by typing its host")
    args = ap.parse_args()

    # --load deletes and recreates the benchmark user; make sure --db-url is the throwaway database.
    from dotenv import load_dotenv
    load_dotenv()
    from core.destructive_guard import require_safe_target
    require_safe_target(args.db_url)

    if args.model:
        os.environ["EMBEDDING_MODEL_NAME"] = args.model
    os.environ["DATABASE_URL"] = args.db_url
    os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/14")

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    engine = create_engine(args.db_url)
    corpus = read_jsonl(os.path.join(args.data_dir, "corpus.jsonl"))
    queries = {q["_id"]: q["text"] for q in read_jsonl(os.path.join(args.data_dir, "queries.jsonl"))}
    qrels = read_qrels(os.path.join(args.data_dir, "qrels", "test.tsv"))
    qids = [q for q in qrels if q in queries]
    if args.max_queries:
        qids = qids[:args.max_queries]
    variant = f"long{args.long_docs}" if args.long_docs else "orig"
    if args.long_docs:
        corpus = make_long_docs(corpus, qrels, args.long_docs, args.long_docs_distractors)

    from utils.embedding_utils import active_embedding_model_name, embed_query
    model_name = active_embedding_model_name()
    dataset = os.path.basename(os.path.normpath(args.data_dir))
    username = "beir_" + hashlib.md5(f"{dataset}:{variant}:{model_name}".encode()).hexdigest()[:12]

    with Session(engine) as session:
        if args.load:
            print(f"Loading {len(corpus)} documents...", flush=True)
            user_id = load_corpus(session, corpus, username)
        else:
            user_id = session.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).scalar()
            if user_id is None:
                sys.exit(f"No loaded corpus for {dataset}/{variant}/{model_name}; run with --load")
        n_chunks = session.execute(text("SELECT count(*) FROM content_chunks WHERE user_id = :u"), {"u": user_id}).scalar()

    # Warm the embedding model, query-embedding cache and reranker so latency reflects steady state.
    for qid in qids:
        embed_query(queries[qid])
    if "rerank" in args.methods:
        from utils.reranker import rerank_passages
        rerank_passages("warmup", ["warmup passage"])

    results = {}
    for method in args.methods.split(","):
        per_q, lat = [], []
        with Session(engine) as session:
            for qid in qids:
                t = time.perf_counter()
                ranked_urls = run_method(method, session, user_id, queries[qid], 100)
                lat.append((time.perf_counter() - t) * 1000)
                session.rollback()
                ranked = [u.split("beir://", 1)[1] for u in ranked_urls]
                rels = qrels[qid]
                per_q.append((ndcg_at_k(ranked, rels), recall_at_k(ranked, rels, 10),
                              recall_at_k(ranked, rels, 100), mrr_at_k(ranked, rels)))
        lat.sort()
        results[method] = {
            "ndcg@10": statistics.mean(x[0] for x in per_q),
            "recall@10": statistics.mean(x[1] for x in per_q),
            "recall@100": statistics.mean(x[2] for x in per_q),
            "mrr@10": statistics.mean(x[3] for x in per_q),
            "latency_p50_ms": lat[len(lat) // 2],
            "latency_p95_ms": lat[int(len(lat) * 0.95) - 1],
        }
        r = results[method]
        print(f"{method:18} nDCG@10={r['ndcg@10']:.4f} R@10={r['recall@10']:.4f} R@100={r['recall@100']:.4f} "
              f"MRR@10={r['mrr@10']:.4f} p50={r['latency_p50_ms']:.0f}ms p95={r['latency_p95_ms']:.0f}ms", flush=True)

    os.makedirs(args.out_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {
        "dataset": dataset, "variant": variant, "split": "test",
        "queries": len(qids), "documents": len(corpus), "chunks": n_chunks,
        "embedding_model": model_name, "generated_at": stamp, "results": results,
    }
    slug = model_name.split("/")[-1]
    path = os.path.join(args.out_dir, f"{dataset}_{variant}_{slug}_{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
