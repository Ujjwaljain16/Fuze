#!/usr/bin/env python3
"""
Check pgvector setup and test vector search syntax
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def check_pgvector_setup():
    """Check if pgvector is properly set up"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔍 Checking pgvector setup...")
    print(f"🔗 Supabase URL: {SUPABASE_URL}")
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Check if vector extension is enabled
        print("\n1. Checking pgvector extension...")
        try:
            # Try to query the extension
            response = supabase.rpc('exec_sql', {
                "query": "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
            }).execute()
            print("✅ pgvector extension query successful")
        except:
            print("⚠️  Could not query pgvector extension directly")
        
        # Check if embedding column exists
        print("\n2. Checking embedding column...")
        response = supabase.table(SUPABASE_TABLE).select("id, title, embedding").limit(1).execute()
        
        if response.data:
            sample_record = response.data[0]
            if 'embedding' in sample_record:
                embedding = sample_record['embedding']
                if embedding:
                    print(f"✅ Embedding column exists with {len(embedding)} dimensions")
                else:
                    print("⚠️  Embedding column exists but is null")
            else:
                print("❌ Embedding column not found")
        else:
            print("⚠️  No data in table to check")
        
        # Test different vector search syntaxes
        print("\n3. Testing vector search syntaxes...")
        
        # Create a test embedding (384-dimensional)
        test_embedding = [0.1] * 384
        
        # Test 1: Basic vector similarity
        print("   Testing basic vector similarity...")
        try:
            response = supabase.table(SUPABASE_TABLE).select(
                "id, title"
            ).not_.is_("embedding", "null").order(
                f"embedding.<=>.[{','.join(map(str, test_embedding))}]"
            ).limit(3).execute()
            print("   ✅ Basic vector similarity works!")
        except Exception as e:
            print(f"   ❌ Basic vector similarity failed: {str(e)[:100]}...")
        
        # Test 2: Raw SQL approach
        print("   Testing raw SQL approach...")
        try:
            response = supabase.rpc('exec_sql', {
                "query": f"""
                    SELECT id, title, 
                           embedding <=> '{test_embedding}'::vector AS distance
                    FROM {SUPABASE_TABLE}
                    WHERE embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT 3;
                """
            }).execute()
            print("   ✅ Raw SQL approach works!")
        except Exception as e:
            print(f"   ❌ Raw SQL approach failed: {str(e)[:100]}...")
        
        # Test 3: Simple query without vector search
        print("   Testing simple query...")
        try:
            response = supabase.table(SUPABASE_TABLE).select(
                "id, title"
            ).limit(3).execute()
            print("   ✅ Simple query works!")
        except Exception as e:
            print(f"   ❌ Simple query failed: {str(e)[:100]}...")
        
        print("\n📋 Summary:")
        print("- If you see ✅ for vector similarity, pgvector is working!")
        print("- If you see ❌ for vector similarity, you need to enable pgvector")
        print("- The fallback system will still work regardless")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_pgvector_setup() 