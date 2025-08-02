#!/usr/bin/env python3
"""
Test script to check Supabase connection and data
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_supabase_connection():
    """Test Supabase connection and check data"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print(f"🔍 Testing Supabase Connection")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key: {SUPABASE_KEY[:10] if SUPABASE_KEY else 'None'}...")
    print(f"Table: {SUPABASE_TABLE}")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase credentials not found")
        return False
    
    try:
        # Create client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client created successfully")
        
        # Test basic connection
        print("\n🔍 Testing basic table access...")
        resp = supabase.table(SUPABASE_TABLE).select("count").execute()
        print(f"✅ Table access successful: {resp}")
        
        # Check if table has data
        print("\n🔍 Checking table data...")
        resp = supabase.table(SUPABASE_TABLE).select("id, title, user_id").limit(5).execute()
        
        if resp.data:
            print(f"✅ Found {len(resp.data)} records in table")
            for i, record in enumerate(resp.data):
                print(f"  {i+1}. ID: {record.get('id')}, Title: {record.get('title', 'No title')}, User: {record.get('user_id')}")
        else:
            print("❌ No data found in table")
            return False
        
        # Check for embeddings
        print("\n🔍 Checking for embeddings...")
        resp = supabase.table(SUPABASE_TABLE).select("id, title, embedding").not_.is_("embedding", "null").limit(3).execute()
        
        if resp.data:
            print(f"✅ Found {len(resp.data)} records with embeddings")
            for i, record in enumerate(resp.data):
                embedding = record.get('embedding')
                if embedding:
                    print(f"  {i+1}. ID: {record.get('id')}, Title: {record.get('title', 'No title')}, Embedding length: {len(embedding)}")
                else:
                    print(f"  {i+1}. ID: {record.get('id')}, Title: {record.get('title', 'No title')}, No embedding")
        else:
            print("❌ No records with embeddings found")
            print("💡 You may need to run the embedding generation script")
        
        # Test vector similarity query
        print("\n🔍 Testing vector similarity query...")
        try:
            # Create a dummy embedding (384-dimensional vector)
            dummy_embedding = [0.1] * 384
            
            resp = supabase.table(SUPABASE_TABLE).select(
                'id, title, embedding'
            ).not_.is_("embedding", "null").order(
                f'embedding.<=>.{dummy_embedding}'
            ).limit(3).execute()
            
            if resp.data:
                print(f"✅ Vector similarity query successful: {len(resp.data)} results")
            else:
                print("❌ Vector similarity query returned no results")
                
        except Exception as e:
            print(f"❌ Vector similarity query failed: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_supabase_connection() 