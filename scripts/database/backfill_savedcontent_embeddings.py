#!/usr/bin/env python3
"""
Backfill embeddings for all SavedContent entries that are missing or have zero vectors.
"""

import sys
import traceback
from app import db, create_app
from models import SavedContent
from utils_web_scraper import scrape_url
from datetime import datetime
from supabase import create_client, Client
import os
import time
from embedding_utils import get_embedding

# --- Supabase config ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xyzcompany.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "your-supabase-service-role-key")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")  # Use saved_content table
client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds


def migrate_bookmarks_to_supabase():
    # Add debugging info
    total_bookmarks = SavedContent.query.count()
    print(f"Total bookmarks in database: {total_bookmarks}")
    
    bookmarks_with_embeddings = SavedContent.query.filter(
        SavedContent.embedding.isnot(None)
    ).count()
    print(f"Bookmarks with embeddings: {bookmarks_with_embeddings}")
    
    bookmarks_without_embeddings = SavedContent.query.filter(
        SavedContent.embedding.is_(None)
    ).count()
    print(f"Bookmarks without embeddings: {bookmarks_without_embeddings}")
    
    failed = []
    migrated = 0
    retry_queue = []
    for bm in SavedContent.query.all():
        print(f"Checking bookmark: {bm.title} (ID: {bm.id})")
        print(f"  - Has embedding: {bm.embedding is not None}")
        if bm.embedding is not None:
            print(f"  - Embedding length: {len(bm.embedding) if hasattr(bm.embedding, '__len__') else 'N/A'}")
        
        if bm.embedding is not None and hasattr(bm.embedding, '__len__') and len(bm.embedding) == 384:
            print(f"  - Skipping (already has valid embedding)")
            continue  # Already has embedding
        print(f"  - Will process this bookmark")
        retry_queue.append((bm, 0))  # (bookmark, retry_count)

    print(f"Bookmarks to process: {len(retry_queue)}")
    
    permanently_failed = []
    while retry_queue:
        bm, retry_count = retry_queue.pop(0)
        try:
            print(f"Processing: {bm.url} (Attempt {retry_count+1})")
            scraped = scrape_url(bm.url)
            content_snippet = scraped.get('content', '')[:300]
            text_for_embedding = f"{bm.title} {content_snippet}"
            embedding = get_embedding(text_for_embedding)
            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            
            # Use saved_content table structure
            data = {
                "user_id": bm.user_id,
                "url": bm.url,
                "title": bm.title,
                "extracted_text": content_snippet,
                "embedding": embedding_list,
                "saved_at": bm.saved_at.isoformat() if bm.saved_at else datetime.utcnow().isoformat(),
                "category": bm.category or 'other',
                "tags": bm.tags,
                "notes": bm.notes
            }
            
            # Insert into Supabase saved_content table
            resp = client.table(SUPABASE_TABLE).insert(data).execute()
            if resp.status_code not in (200, 201):
                print(f"Supabase insert failed: {resp.status_code} {resp.data}")
                if retry_count + 1 < MAX_RETRIES:
                    print(f"Retrying {bm.url} after {RETRY_DELAY}s...")
                    retry_queue.append((bm, retry_count + 1))
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Permanently failed after {MAX_RETRIES} attempts: {bm.url}")
                    permanently_failed.append(bm.url)
                continue
            # Update local DB
            bm.embedding = embedding_list
            db.session.commit()
            migrated += 1
            print(f"Inserted and updated: {bm.url}")
        except Exception as e:
            print(f"FAILED: {bm.url} - {e}")
            traceback.print_exc()
            if retry_count + 1 < MAX_RETRIES:
                print(f"Retrying {bm.url} after {RETRY_DELAY}s...")
                retry_queue.append((bm, retry_count + 1))
                time.sleep(RETRY_DELAY)
            else:
                print(f"Permanently failed after {MAX_RETRIES} attempts: {bm.url}")
                permanently_failed.append(bm.url)
    print(f"Migration complete. Migrated: {migrated}, Permanently Failed: {len(permanently_failed)}")
    if permanently_failed:
        print("Permanently Failed URLs:", permanently_failed)


def semantic_search_supabase(query, top_k=5):
    """
    Example: Perform semantic search in Supabase using pgvector.
    """
    query_emb = get_embedding(query)
    query_emb_list = query_emb.tolist() if hasattr(query_emb, 'tolist') else list(query_emb)
    # Supabase SQL RPC call (PostgRest) for vector search
    sql = f"""
        SELECT *, embedding <=> ARRAY{query_emb_list} AS distance
        FROM {SUPABASE_TABLE}
        ORDER BY distance ASC
        LIMIT {top_k};
    """
    # Use the Supabase client to run SQL (if enabled)
    resp = client.rpc('execute_sql', {"sql": sql}).execute()
    if resp.status_code == 200:
        print("Semantic search results:")
        for row in resp.data:
            print(row)
    else:
        print(f"Semantic search failed: {resp.status_code} {resp.data}")


if __name__ == "__main__":
    # Create Flask app context
    app = create_app()
    with app.app_context():
        migrate_bookmarks_to_supabase()
        # Example usage:
        # semantic_search_supabase("OAuth2 login flow", top_k=5) 