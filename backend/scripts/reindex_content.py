#!/usr/bin/env python3
"""
Rebuild every bookmark's vectors with the active embedding model: the document
embedding, its passage chunks, and (if it has a current content profile) the
profile chunk. Run after changing EMBEDDING_MODEL_NAME or deploying chunking.

Safe to stop and re-run: rows already embedded with the active model are skipped.

Usage (from backend/):
    python scripts/reindex_content.py --verify
    python scripts/reindex_content.py --limit 500
"""

import argparse
import os
import sys
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

PENDING_SQL = """
    SELECT id FROM saved_content
    WHERE COALESCE(embedding_metadata->>'model', '') <> :model
       OR NOT EXISTS (SELECT 1 FROM content_chunks c
                      WHERE c.content_id = saved_content.id AND c.embedding_model = :model)
    ORDER BY id
    LIMIT :limit
"""


def main():
    ap = argparse.ArgumentParser(description="Re-embed bookmarks with the active embedding model")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--verify", action="store_true", help="Only print counts")
    args = ap.parse_args()

    from run_production import create_app
    from models import db, ContentAnalysis, SavedContent
    from services.bookmark_processing_service import generate_comprehensive_embedding, validate_embedding
    from services.content_profile import PROFILE_VERSION, index_profile_chunk
    from services.hybrid_search import index_content_chunks
    from utils.embedding_utils import active_embedding_model_name

    app = create_app()
    with app.app_context():
        model = active_embedding_model_name()
        total = db.session.execute(text("SELECT count(*) FROM saved_content")).scalar() or 0
        pending = db.session.execute(text(
            "SELECT count(*) FROM (" + PENDING_SQL.replace("LIMIT :limit", "") + ") p"), {"model": model}).scalar() or 0
        print(f"[reindex] model={model} bookmarks={total} pending={pending}")
        if args.verify or not pending:
            return

        ids = [r[0] for r in db.session.execute(text(PENDING_SQL), {"model": model, "limit": args.limit})]
        started, done, failed = time.time(), 0, 0
        for i, content_id in enumerate(ids, 1):
            try:
                item = db.session.get(SavedContent, content_id)
                emb = generate_comprehensive_embedding(
                    title=item.title, description=item.notes or "", meta_description="", headings=[],
                    extracted_text=item.extracted_text or "", url=item.url)
                if validate_embedding(emb):
                    item.embedding = emb
                    item.embedding_metadata = {"model": model}
                    item.embedding_status = "SUCCESS"
                index_content_chunks(db.session, content_id)
                db.session.execute(text(
                    "DELETE FROM content_chunks WHERE content_id = :id AND embedding_model <> :model"),
                    {"id": content_id, "model": model})
                analysis = db.session.query(ContentAnalysis).filter_by(content_id=content_id).first()
                profile = analysis.analysis_data if analysis else None
                if profile and profile.get("profile_version") == PROFILE_VERSION:
                    index_profile_chunk(db.session, content_id, item.user_id, item.title or "", profile)
                db.session.commit()
                done += 1
            except Exception as e:
                db.session.rollback()
                failed += 1
                print(f"  content_id={content_id} FAILED: {e}")
            if i % 25 == 0:
                print(f"  {i}/{len(ids)} ({time.time() - started:.0f}s)", flush=True)

        from services.cache_invalidation_service import cache_invalidator
        for (user_id,) in db.session.execute(text("SELECT DISTINCT user_id FROM saved_content")):
            cache_invalidator.invalidate_user_cache(user_id)
        print(f"[reindex] reindexed={done} failed={failed} (re-run to continue)")


if __name__ == "__main__":
    main()
