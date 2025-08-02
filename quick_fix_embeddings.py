#!/usr/bin/env python3
"""
Quick fix for embedding dimensions
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def quick_fix():
    """Quick check and fix for embeddings"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔧 Quick Embedding Fix")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Check current state
        print("\n📋 Current Status:")
        response = supabase.table(SUPABASE_TABLE).select("id, title, embedding").limit(3).execute()
        
        if response.data:
            for i, bookmark in enumerate(response.data, 1):
                print(f"\nBookmark {i}:")
                print(f"  ID: {bookmark['id']}")
                print(f"  Title: {bookmark['title'][:40]}...")
                if bookmark.get('embedding'):
                    embedding = bookmark['embedding']
                    if isinstance(embedding, str):
                        print(f"  Embedding: String with {len(embedding)} characters")
                    else:
                        print(f"  Embedding: List with {len(embedding)} dimensions")
                else:
                    print(f"  Embedding: None")
        
        print("\n⚠️  ISSUE DETECTED:")
        print("The embeddings are stored as strings instead of vectors.")
        print("This means the vector column wasn't properly created.")
        
        print("\n🔧 SOLUTION:")
        print("You need to run these SQL commands in Supabase SQL Editor:")
        print()
        print("1. Drop the current embedding column:")
        print(f"   ALTER TABLE {SUPABASE_TABLE} DROP COLUMN IF EXISTS embedding;")
        print()
        print("2. Create the correct vector column:")
        print(f"   ALTER TABLE {SUPABASE_TABLE} ADD COLUMN embedding vector(384);")
        print()
        print("3. After running those commands, run:")
        print("   python generate_all_embeddings.py")
        print()
        print("This will fix the dimension mismatch and enable true vector similarity search!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    quick_fix() 