#!/usr/bin/env python3
"""Turn a user's thumbs up/down on recommendations into an evaluation set, per project.

    python scripts/export_feedback_eval.py --email you@example.com --out feedback_eval

READ ONLY: it only SELECTs from the database named by DATABASE_URL (which can be production). Writes a
BEIR-format folder, the format scripts/eval_recommendations.py already reads:

    queries.jsonl      one query per judged project: its title, description and technologies
    corpus.jsonl       the user's embedded bookmarks (the pool recommendations are drawn from)
    qrels/test.tsv     query-id, corpus-id, score: 1 = judged useful for that project, 0 = judged not useful
    judgments.jsonl    every judgment with the rank it was shown at, its match score and its time
    SUMMARY.txt        counts per project and the caveats below

Labels: helpful / like / saved / completed count as useful, not_relevant / dislike as not useful. A bare
"clicked" is a weak signal and is left out. If a bookmark was judged more than once for a project, the
latest judgment wins.

Caveats the numbers inherit (also written to SUMMARY.txt): only recommendations that were SHOWN can be
judged, so the labels are biased toward what the current engine ranks high (use the recorded position to
account for that); and a few dozen judgments per project is enough to compare settings, not to publish an
absolute accuracy.

The output contains your bookmarks' text: keep it out of git (the folder name is in .gitignore) and use
--no-text if you only need ids and titles.
"""

import argparse
import json
import os
import sys
from collections import defaultdict

from sqlalchemy import create_engine, text

POSITIVE = {"helpful", "like", "saved", "completed"}
NEGATIVE = {"not_relevant", "dislike"}

CAVEATS = """Read these before quoting a number from this set:
- Only recommendations that were shown could be judged, so the labels favour what the current engine ranks
  high. judgments.jsonl records the rank each item was shown at, to correct for that.
- A few dozen judgments per project can compare two settings (nDCG, MRR on the same labels); they cannot
  support an absolute accuracy claim.
- Run scripts/eval_recommendations.py on a throwaway LOCAL database with --data-dir pointing at this folder;
  never against production (it recreates its benchmark users).
"""


def _context(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


def export(conn, user_id: int, out_dir: str, include_text: bool = True, max_chars: int = 4000) -> dict:
    """Write the evaluation set for one user; returns a summary of what was written."""
    judged = conn.execute(text("""
        SELECT uf.id, uf.project_id, uf.content_id, uf.feedback_type, uf.timestamp, uf.context_data,
               p.title, p.description, p.technologies
        FROM user_feedback uf
        JOIN projects p ON p.id = uf.project_id AND p.user_id = uf.user_id
        WHERE uf.user_id = :uid AND uf.project_id IS NOT NULL
        ORDER BY uf.id"""), {"uid": user_id}).mappings().all()

    latest = {}          # (project, content) -> the newest usable judgment
    projects = {}
    for row in judged:
        label = 1 if row["feedback_type"] in POSITIVE else 0 if row["feedback_type"] in NEGATIVE else None
        if label is None:
            continue
        latest[(row["project_id"], row["content_id"])] = (label, row)
        projects[row["project_id"]] = row

    os.makedirs(os.path.join(out_dir, "qrels"), exist_ok=True)
    with open(os.path.join(out_dir, "queries.jsonl"), "w", encoding="utf-8") as f:
        for pid, row in sorted(projects.items()):
            query = ". ".join(part.strip() for part in (row["title"], row["description"], row["technologies"]) if part and part.strip())
            f.write(json.dumps({"_id": f"p{pid}", "text": query}, ensure_ascii=False) + "\n")

    body = f"substr(s.extracted_text, 1, {int(max_chars)})" if include_text else "''"
    bookmarks = conn.execute(text(f"""
        SELECT s.id, s.title, s.url, {body} AS body FROM saved_content s
        WHERE s.user_id = :uid AND s.embedding IS NOT NULL ORDER BY s.id"""), {"uid": user_id}).mappings().all()
    with open(os.path.join(out_dir, "corpus.jsonl"), "w", encoding="utf-8") as f:
        for b in bookmarks:
            f.write(json.dumps({"_id": f"b{b['id']}", "title": b["title"] or "", "text": b["body"] or "",
                                "url": b["url"]}, ensure_ascii=False) + "\n")

    in_corpus = {b["id"] for b in bookmarks}
    with open(os.path.join(out_dir, "qrels", "test.tsv"), "w", encoding="utf-8") as f:
        f.write("query-id\tcorpus-id\tscore\n")
        for (pid, cid), (label, _) in sorted(latest.items()):
            if cid in in_corpus:
                f.write(f"p{pid}\tb{cid}\t{label}\n")
    with open(os.path.join(out_dir, "judgments.jsonl"), "w", encoding="utf-8") as f:
        for (pid, cid), (label, row) in sorted(latest.items()):
            ctx = _context(row["context_data"])
            f.write(json.dumps({"query": f"p{pid}", "doc": f"b{cid}", "label": label,
                                "feedback_type": row["feedback_type"], "position": ctx.get("position"),
                                "score": ctx.get("score"), "at": str(row["timestamp"])}) + "\n")

    per_project = defaultdict(lambda: [0, 0])
    for (pid, _), (label, _) in latest.items():
        per_project[pid][0 if label else 1] += 1
    summary = {"projects": len(projects), "judgments": len(latest), "useful": sum(v[0] for v in per_project.values()),
               "not_useful": sum(v[1] for v in per_project.values()), "bookmarks_in_corpus": len(bookmarks),
               "per_project": {pid: {"title": projects[pid]["title"], "useful": v[0], "not_useful": v[1]}
                               for pid, v in sorted(per_project.items())}}
    with open(os.path.join(out_dir, "SUMMARY.txt"), "w", encoding="utf-8") as f:
        f.write(f"{summary['judgments']} judgments over {summary['projects']} projects "
                f"({summary['useful']} useful, {summary['not_useful']} not useful); "
                f"{summary['bookmarks_in_corpus']} bookmarks in the corpus.\n\n")
        for pid, info in summary["per_project"].items():
            f.write(f"  p{pid} {info['title']!r}: {info['useful']} useful, {info['not_useful']} not useful\n")
        f.write("\n" + CAVEATS)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--email")
    who.add_argument("--user-id", type=int)
    parser.add_argument("--out", default="feedback_eval")
    parser.add_argument("--no-text", action="store_true", help="export ids and titles only, no page text")
    parser.add_argument("--max-chars", type=int, default=4000, help="page text kept per bookmark")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set.")

    engine = create_engine(url)
    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SET TRANSACTION READ ONLY"))
        if args.user_id is not None:
            user_id = args.user_id
        else:
            user_id = conn.execute(text("SELECT id FROM users WHERE lower(email) = lower(:e)"), {"e": args.email}).scalar()
            if user_id is None:
                sys.exit("No user with that email.")
        summary = export(conn, user_id, args.out, include_text=not args.no_text, max_chars=args.max_chars)

    print(f"Wrote {args.out}/: {summary['judgments']} judgments over {summary['projects']} projects "
          f"({summary['useful']} useful, {summary['not_useful']} not useful), {summary['bookmarks_in_corpus']} bookmarks.")
    if summary["judgments"] < 30:
        print("Few judgments so far: keep using the thumbs buttons on the Recommendations page "
              "(each project needs about 10) before running the evaluation.")
    print("Caveats are in SUMMARY.txt. The folder holds your bookmarks' text: do not commit it.")


if __name__ == "__main__":
    main()
