#!/usr/bin/env python3
"""
Test script to verify embedding dimension fix
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding
import numpy as np

# Load environment variables
load_dotenv()

def test_embedding_consistency():
    """Test if all embeddings have consistent dimensions"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🧪 Testing Embedding Consistency")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Get current embedding model dimensions
        print("\n1. Checking current embedding model...")
        test_embedding = get_embedding("test")
        if hasattr(test_embedding, 'tolist'):
            test_embedding_list = test_embedding.tolist()
        else:
            test_embedding_list = list(test_embedding)
        
        expected_dim = len(test_embedding_list)
        print(f"📊 Expected embedding dimensions: {expected_dim}")
        
        # Get all bookmarks with embeddings
        print("\n2. Checking stored embeddings...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, embedding"
        ).not_.is_("embedding", "null").execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} bookmarks with embeddings")
        
        if not bookmarks:
            print("❌ No bookmarks with embeddings found")
            return False
        
        # Check dimensions
        mismatched = []
        correct = 0
        
        for bookmark in bookmarks:
            if 'embedding' in bookmark and bookmark['embedding']:
                actual_dim = len(bookmark['embedding'])
                if actual_dim != expected_dim:
                    mismatched.append({
                        'id': bookmark['id'],
                        'title': bookmark['title'],
                        'expected': expected_dim,
                        'actual': actual_dim
                    })
                else:
                    correct += 1
        
        # Report results
        print(f"\n📊 Embedding dimension analysis:")
        print(f"   ✅ Correct dimensions ({expected_dim}): {correct} bookmarks")
        print(f"   ❌ Mismatched dimensions: {len(mismatched)} bookmarks")
        
        if mismatched:
            print(f"\n❌ Found {len(mismatched)} bookmarks with mismatched dimensions:")
            for i, item in enumerate(mismatched[:5], 1):  # Show first 5
                print(f"   {i}. ID {item['id']}: {item['title'][:50]}...")
                print(f"      Expected: {item['expected']}, Actual: {item['actual']}")
            
            if len(mismatched) > 5:
                print(f"   ... and {len(mismatched) - 5} more")
            
            return False
        else:
            print(f"\n✅ All embeddings have consistent dimensions!")
            return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_vector_search():
    """Test if vector search works with current embeddings"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("\n🧪 Testing Vector Search")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Generate query embedding
        print("1. Generating query embedding...")
        test_query = "React hooks"
        query_embedding = get_embedding(test_query)
        
        if hasattr(query_embedding, 'tolist'):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = list(query_embedding)
        
        print(f"📊 Query embedding dimensions: {len(query_embedding_list)}")
        
        # Perform vector search
        print("\n2. Performing vector search...")
        pg_vector = f"[{','.join(map(str, query_embedding_list))}]"
        
        response = (
            supabase.table(SUPABASE_TABLE)
            .select("id, title, url, embedding")
            .not_.is_("embedding", "null")
            .order(f"embedding.<=>.{pg_vector}")
            .limit(3)
            .execute()
        )
        
        if response.data:
            print("✅ Vector search successful!")
            print(f"📋 Found {len(response.data)} results:")
            
            for i, result in enumerate(response.data, 1):
                bookmark_embedding = result['embedding']
                if len(bookmark_embedding) == len(query_embedding_list):
                    similarity = np.dot(query_embedding_list, bookmark_embedding)
                    print(f"  {i}. {result['title']} (Similarity: {similarity:.4f})")
                else:
                    print(f"  {i}. {result['title']} (Dimension mismatch!)")
            
            return True
        else:
            print("ℹ️  No results found")
            return False
        
    except Exception as e:
        print(f"❌ Vector search failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🔧 Embedding Fix Verification")
    print("=" * 50)
    
    # Test embedding consistency
    consistency_ok = test_embedding_consistency()
    
    # Test vector search
    search_ok = test_vector_search()
    
    # Final report
    print(f"\n📊 Test Results:")
    print(f"   Embedding consistency: {'✅ PASS' if consistency_ok else '❌ FAIL'}")
    print(f"   Vector search: {'✅ PASS' if search_ok else '❌ FAIL'}")
    
    if consistency_ok and search_ok:
        print(f"\n🎉 All tests passed! Vector search is working correctly.")
    else:
        print(f"\n⚠️  Some tests failed. Consider running:")
        print(f"   python fix_embedding_dimensions.py")

if __name__ == "__main__":
    main() 