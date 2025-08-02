#!/usr/bin/env python3
"""
Backfill Supabase embeddings for existing bookmarks
This script generates embeddings for all existing bookmarks and stores them in Supabase
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding
import time

# Load environment variables
load_dotenv()

def backfill_supabase_embeddings():
    """Generate embeddings for all bookmarks and store in Supabase"""
    
    # Get Supabase credentials
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase credentials not found in environment variables")
        print("Please make sure your .env file has SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return
    
    print("🔧 Backfilling Supabase embeddings for existing bookmarks")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")
    print(f"📋 Table: {SUPABASE_TABLE}")
    print()
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Get all bookmarks without embeddings
        print("🔍 Fetching bookmarks without embeddings...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, notes, extracted_text, url"
        ).is_("embedding", "null").execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} bookmarks without embeddings")
        
        if not bookmarks:
            print("✅ All bookmarks already have embeddings!")
            return
        
        # Process each bookmark
        success_count = 0
        error_count = 0
        
        for i, bookmark in enumerate(bookmarks, 1):
            try:
                print(f"\n🔄 Processing bookmark {i}/{len(bookmarks)}: {bookmark.get('title', 'No title')[:50]}...")
                
                # Create text for embedding
                text_parts = []
                if bookmark.get('title'):
                    text_parts.append(bookmark['title'])
                if bookmark.get('notes'):
                    text_parts.append(bookmark['notes'])
                if bookmark.get('extracted_text'):
                    text_parts.append(bookmark['extracted_text'][:1000])  # Limit text length
                
                if not text_parts:
                    print("⚠️  No text content found, skipping...")
                    continue
                
                text = " ".join(text_parts)
                
                # Generate embedding
                print("🧠 Generating embedding...")
                embedding = get_embedding(text)
                
                # Convert to list format
                if hasattr(embedding, 'tolist'):
                    embedding_list = embedding.tolist()
                else:
                    embedding_list = list(embedding)
                
                # Update the bookmark with embedding
                print("💾 Storing embedding in Supabase...")
                supabase.table(SUPABASE_TABLE).update({
                    "embedding": embedding_list
                }).eq("id", bookmark['id']).execute()
                
                success_count += 1
                print(f"✅ Successfully updated bookmark {bookmark['id']}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                print(f"❌ Error processing bookmark {bookmark.get('id')}: {str(e)}")
                continue
        
        print(f"\n🎉 Backfill completed!")
        print(f"✅ Successfully processed: {success_count} bookmarks")
        print(f"❌ Errors: {error_count} bookmarks")
        
        if success_count > 0:
            print("\n🚀 Vector similarity search is now enabled!")
            print("Your semantic search will now use true AI-powered vector similarity")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Please check your Supabase connection and credentials")

def test_vector_search():
    """Test vector similarity search after backfill"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test query
        test_query = "React hooks"
        print(f"\n🧪 Testing vector search with query: '{test_query}'")
        
        # Generate embedding for test query
        query_embedding = get_embedding(test_query)
        if hasattr(query_embedding, 'tolist'):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = list(query_embedding)
        
        # Try vector similarity search
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, url, extracted_text"
        ).not_.is_("embedding", "null").order(
            f"embedding.<=>.{query_embedding_list}"
        ).limit(3).execute()
        
        if response.data:
            print(f"✅ Vector search successful! Found {len(response.data)} results:")
            for i, result in enumerate(response.data, 1):
                print(f"  {i}. {result.get('title', 'No title')}")
        else:
            print("ℹ️  No results found with vector search")
            
    except Exception as e:
        print(f"❌ Vector search test failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Supabase Embedding Backfill Tool")
    print("=" * 50)
    
    # First, make sure pgvector is enabled
    print("📋 Before running this script, make sure you've:")
    print("1. Enabled pgvector extension in Supabase SQL Editor:")
    print("   CREATE EXTENSION IF NOT EXISTS vector;")
    print("2. Added vector column to saved_content table:")
    print("   ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS embedding vector(384);")
    print()
    
    input("Press Enter to continue with backfill...")
    
    # Run backfill
    backfill_supabase_embeddings()
    
    # Test vector search
    print("\n" + "=" * 50)
    test_vector_search() 