#!/usr/bin/env python3
"""
Debug script to investigate embedding storage issues
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding
import json

# Load environment variables
load_dotenv()

def debug_embedding_storage():
    """Debug what's happening with embedding storage"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔍 Debugging Embedding Storage")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Get a few sample bookmarks
        print("\n1. Getting sample bookmarks...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, embedding"
        ).limit(3).execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} sample bookmarks")
        
        for i, bookmark in enumerate(bookmarks, 1):
            print(f"\n   Bookmark {i}:")
            print(f"      ID: {bookmark['id']}")
            print(f"      Title: {bookmark['title'][:50]}...")
            
            if 'embedding' in bookmark and bookmark['embedding']:
                embedding = bookmark['embedding']
                print(f"      Embedding type: {type(embedding)}")
                print(f"      Embedding length: {len(embedding)}")
                print(f"      First 5 values: {embedding[:5]}")
                print(f"      Last 5 values: {embedding[-5:]}")
            else:
                print(f"      No embedding found")
        
        # Test embedding generation
        print(f"\n2. Testing embedding generation...")
        test_text = "Test embedding generation"
        test_embedding = get_embedding(test_text)
        
        if hasattr(test_embedding, 'tolist'):
            test_embedding_list = test_embedding.tolist()
        else:
            test_embedding_list = list(test_embedding)
        
        print(f"   Generated embedding type: {type(test_embedding_list)}")
        print(f"   Generated embedding length: {len(test_embedding_list)}")
        print(f"   First 5 values: {test_embedding_list[:5]}")
        print(f"   Last 5 values: {test_embedding_list[-5:]}")
        
        # Try to update a single bookmark and see what happens
        print(f"\n3. Testing single bookmark update...")
        if bookmarks:
            test_bookmark = bookmarks[0]
            bookmark_id = test_bookmark['id']
            
            print(f"   Updating bookmark ID: {bookmark_id}")
            
            # Update with new embedding
            update_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": test_embedding_list
            }).eq("id", bookmark_id).execute()
            
            print(f"   Update result: {update_result.data}")
            
            # Check what was actually stored
            check_response = supabase.table(SUPABASE_TABLE).select(
                "id, embedding"
            ).eq("id", bookmark_id).execute()
            
            if check_response.data:
                stored_bookmark = check_response.data[0]
                stored_embedding = stored_bookmark.get('embedding')
                
                if stored_embedding:
                    print(f"   Stored embedding type: {type(stored_embedding)}")
                    print(f"   Stored embedding length: {len(stored_embedding)}")
                    print(f"   Stored first 5 values: {stored_embedding[:5]}")
                    print(f"   Stored last 5 values: {stored_embedding[-5:]}")
                    
                    # Check if they match
                    if len(stored_embedding) == len(test_embedding_list):
                        print(f"   ✅ Lengths match!")
                        if stored_embedding[:5] == test_embedding_list[:5]:
                            print(f"   ✅ Values match!")
                        else:
                            print(f"   ❌ Values don't match!")
                    else:
                        print(f"   ❌ Lengths don't match!")
                else:
                    print(f"   ❌ No embedding stored after update")
        
        # Check database schema
        print(f"\n4. Checking database schema...")
        try:
            # Try to get table info
            schema_response = supabase.rpc('get_table_info', {
                'table_name': SUPABASE_TABLE
            }).execute()
            print(f"   Schema info: {schema_response.data}")
        except Exception as e:
            print(f"   Could not get schema info: {e}")
        
        # Check for any triggers or constraints
        print(f"\n5. Checking for potential issues...")
        print(f"   - Are there any database triggers?")
        print(f"   - Are there any constraints on the embedding column?")
        print(f"   - Is the embedding column the correct type?")
        print(f"   - Are there any row-level security policies?")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def check_database_constraints():
    """Check for database constraints that might prevent updates"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print(f"\n🔍 Checking Database Constraints")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Try to get table structure
        print("1. Checking table structure...")
        
        # Try different approaches to get table info
        try:
            # Try to get column info
            response = supabase.table(SUPABASE_TABLE).select("*").limit(1).execute()
            if response.data:
                sample_row = response.data[0]
                print(f"   Sample row keys: {list(sample_row.keys())}")
                
                if 'embedding' in sample_row:
                    embedding_value = sample_row['embedding']
                    print(f"   Embedding column type: {type(embedding_value)}")
                    if embedding_value:
                        print(f"   Embedding column length: {len(embedding_value)}")
        except Exception as e:
            print(f"   Error getting table structure: {e}")
        
        # Check if we can update with different data types
        print("\n2. Testing different update approaches...")
        
        # Test 1: Update with None
        try:
            test_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": None
            }).eq("id", 1).execute()
            print(f"   ✅ Can update with None")
        except Exception as e:
            print(f"   ❌ Cannot update with None: {e}")
        
        # Test 2: Update with empty list
        try:
            test_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": []
            }).eq("id", 1).execute()
            print(f"   ✅ Can update with empty list")
        except Exception as e:
            print(f"   ❌ Cannot update with empty list: {e}")
        
        # Test 3: Update with small list
        try:
            test_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": [1.0, 2.0, 3.0]
            }).eq("id", 1).execute()
            print(f"   ✅ Can update with small list")
        except Exception as e:
            print(f"   ❌ Cannot update with small list: {e}")
        
    except Exception as e:
        print(f"❌ Error checking constraints: {str(e)}")

def main():
    """Main function"""
    debug_embedding_storage()
    check_database_constraints()

if __name__ == "__main__":
    main() 