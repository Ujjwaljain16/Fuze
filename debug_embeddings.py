#!/usr/bin/env python3
"""
Debug embeddings in the database
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def debug_embeddings():
    """Debug the current state of embeddings"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔍 Debugging Embeddings")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Check a few bookmarks
        print("\n1. Checking sample bookmarks...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, embedding"
        ).limit(5).execute()
        
        if response.data:
            for i, bookmark in enumerate(response.data, 1):
                print(f"\nBookmark {i}:")
                print(f"  ID: {bookmark['id']}")
                print(f"  Title: {bookmark['title'][:50]}...")
                if 'embedding' in bookmark and bookmark['embedding']:
                    print(f"  Embedding: {len(bookmark['embedding'])} dimensions")
                    print(f"  Sample values: {bookmark['embedding'][:3]}...")
                else:
                    print(f"  Embedding: None or empty")
        else:
            print("❌ No bookmarks found")
        
        # Check total count
        print("\n2. Checking total bookmarks...")
        response = supabase.table(SUPABASE_TABLE).select("id").execute()
        total_bookmarks = len(response.data)
        print(f"📊 Total bookmarks: {total_bookmarks}")
        
        # Check bookmarks with embeddings
        print("\n3. Checking bookmarks with embeddings...")
        response = supabase.table(SUPABASE_TABLE).select("id").not_.is_("embedding", "null").execute()
        bookmarks_with_embeddings = len(response.data)
        print(f"📊 Bookmarks with embeddings: {bookmarks_with_embeddings}")
        
        if total_bookmarks > 0:
            percentage = (bookmarks_with_embeddings / total_bookmarks) * 100
            print(f"📊 Percentage with embeddings: {percentage:.1f}%")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    debug_embeddings() 