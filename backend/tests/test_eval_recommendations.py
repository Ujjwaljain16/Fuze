"""Smoke test for the offline recommendation evaluation (scripts/eval_recommendations.py).

A tiny synthetic BEIR-format corpus and a bag-of-words embedder stand in for the real dataset
and model, so this runs in seconds on both lanes (SQLite: document vectors; Postgres: passage
chunks + HNSW) and keeps the harness from rotting.
"""
import hashlib
import json
import uuid

import numpy as np
import pytest

from scripts import eval_recommendations as er

TOPICS = {
    "volcano": ["volcano", "lava", "magma", "eruption", "crater", "ash"],
    "orchestra": ["orchestra", "violin", "symphony", "conductor", "cello", "concert"],
    "database": ["database", "index", "query", "postgres", "transaction", "table"],
}


def _bow(texts):
    """Hashed bag of words, unit length: documents about the same topic share dimensions."""
    out = np.zeros((len(texts), 384), dtype=np.float32)
    for row, t in enumerate(texts):
        for w in t.lower().replace(".", " ").replace(":", " ").split():
            out[row, int(hashlib.md5(w.encode()).hexdigest(), 16) % 384] += 1.0
        out[row] /= np.linalg.norm(out[row]) or 1.0
    return out


def _write_beir(root):
    docs, queries, qrels = [], [], []
    for t, words in TOPICS.items():
        for i in range(4):
            body = " ".join(words[(i + j) % len(words)] for j in range(5)) + f" note {t}{i}"
            docs.append({"_id": f"{t}-{i}", "title": f"{words[i]} {words[i + 1]}", "text": body})
            qrels.append((f"q-{t}", f"{t}-{i}", 2 if i < 2 else 1))
        queries.append({"_id": f"q-{t}", "text": f"how {words[0]} {words[1]} {words[2]} relate to {words[3]} "
                                                    f"and {words[4]} in practice"})
    (root / "qrels").mkdir()
    (root / "corpus.jsonl").write_text("\n".join(json.dumps(d) for d in docs), encoding="utf-8")
    (root / "queries.jsonl").write_text("\n".join(json.dumps(q) for q in queries), encoding="utf-8")
    (root / "qrels" / "test.tsv").write_text(
        "query-id\tcorpus-id\tscore\n" + "\n".join(f"{q}\t{d}\t{s}" for q, d, s in qrels), encoding="utf-8")


def test_project_context_splits_title_and_description():
    assert er.project_context("short query") == ("short query", "")
    long_q = "one two three four five six seven eight nine ten"
    assert er.project_context(long_q) == ("one two three four five six seven eight", long_q)


def test_metrics():
    rels = {"a": 2, "b": 1}
    assert er.ndcg_at_k(["a", "b", "x"], rels) == pytest.approx(1.0)
    assert er.ndcg_at_k(["x", "y"], rels) == 0.0
    assert er.mrr_at_k(["x", "b"], rels) == 0.5
    assert er.recall_at_k(["a", "x"], rels, 20) == 0.5
    same = {"a": np.ones(3), "b": np.ones(3)}
    assert er.intra_list_diversity(["a", "b"], same) == pytest.approx(0.0, abs=1e-5)


def test_partition_gives_disjoint_slices_with_owned_relevance(tmp_path):
    _write_beir(tmp_path)
    evalset = er.load_beir(str(tmp_path), max_docs=0)
    slices, dropped = er.partition(evalset, 2)
    owned = [set(s["docs"]) for s in slices]
    assert not owned[0] & owned[1]
    assert owned[0] | owned[1] == {d["_id"] for d in evalset.docs}
    for s, docs in zip(slices, owned):
        for rels in s["qrels"].values():
            assert set(rels) <= docs
    assert dropped == 0


def test_end_to_end_on_a_tiny_corpus(app, tmp_path):
    from models import User, db

    _write_beir(tmp_path)
    evalset = er.load_beir(str(tmp_path), max_docs=0)
    prefix = f"smoke_{uuid.uuid4().hex[:8]}"
    configs = [er.Config("mmr1.0", 1.0), er.Config("mmr0.5_template", 0.5, "template"),
               er.Config("task", mode="task"), er.Config("query", mode="query")]
    with app.app_context():
        try:
            out = er.evaluate(db.session, evalset, "fake-bow", _bow, _bow, load=True, configs=configs,
                              users=2, rerank_sample=0, username_prefix=prefix, log=lambda m: None)
        finally:
            for user in User.query.filter(User.username.like(f"{prefix}%")).all():
                db.session.delete(user)
            db.session.commit()

    assert set(out["results"]) == {c.name for c in configs}
    for name, r in out["results"].items():
        assert r["queries"] == 3
        # Topics are trivially separable; MMR 0.5 may legitimately interleave other topics.
        assert r["ndcg@10"] > (0.0 if name == "mmr0.5_template" else 0.8), name
        assert r["recall@20"] == pytest.approx(1.0), name
        assert 0.0 <= r["ild@10"] <= 2.0
        assert 0.0 < r["catalog_coverage@10"] <= 1.0
        assert r["latency_p50_ms"] is not None
    assert out["query_vectors_encoded_during_timing"] == 0
    mu = out["multi_user"]
    assert mu["metrics"]["leaked_results"] == 0
    assert mu["queries"] + mu["dropped_queries"] == 3
    if db.engine.dialect.name == "postgresql":
        for group in ("single_user", "multi_user"):
            assert out["ann_recall"][group]["planner"]["mean_recall_vs_exact"] == pytest.approx(1.0)
            forced = out["ann_recall"][group]["forced_hnsw"]
            assert forced["plan_uses_hnsw"] and forced["mean_recall_vs_exact"] > 0.9

    md = er.markdown_summary({"generated_at": "now", "git": {"sha": "abc", "dirty": False}, **out})
    assert "nDCG@10" in md and "mmr0.5_template" in md
