#!/usr/bin/env python3
"""
Working vector search implementation that handles string-encoded embeddings
"""

import os
import json
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding

# Load environment variables
load_dotenv()

def parse_embedding_string(embedding_str):
    """Parse embedding string to list of floats"""
    try:
        if isinstance(embedding_str, str):
            return json.loads(embedding_str)
        elif isinstance(embedding_str, list):
            return embedding_str
        else:
            return None
    except:
        return None

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    return dot_product / (norm1 * norm2)

def vector_search(query_text, limit=5):
    """Perform vector similarity search"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print(f"🔍 Vector Search: '{query_text}'")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Generate query embedding
        print(f"\n1. Generating query embedding...")
        query_embedding = get_embedding(query_text)
        
        if hasattr(query_embedding, 'tolist'):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = list(query_embedding)
        
        print(f"📊 Query embedding dimensions: {len(query_embedding_list)}")
        
        # Get all bookmarks with embeddings
        print(f"\n2. Fetching bookmarks with embeddings...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, url, notes, embedding"
        ).not_.is_("embedding", "null").execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} bookmarks with embeddings")
        
        if not bookmarks:
            print("❌ No bookmarks with embeddings found")
            return []
        
        # Calculate similarities
        print(f"\n3. Calculating similarities...")
        similarities = []
        
        for bookmark in bookmarks:
            try:
                embedding_str = bookmark.get('embedding')
                if not embedding_str:
                    continue
                
                # Parse the embedding string
                bookmark_embedding = parse_embedding_string(embedding_str)
                if not bookmark_embedding:
                    continue
                
                # Calculate similarity
                similarity = cosine_similarity(query_embedding_list, bookmark_embedding)
                
                similarities.append({
                    'id': bookmark['id'],
                    'title': bookmark.get('title', ''),
                    'url': bookmark.get('url', ''),
                    'notes': bookmark.get('notes', ''),
                    'similarity': similarity
                })
                
            except Exception as e:
                print(f"⚠️  Error processing bookmark {bookmark.get('id')}: {str(e)}")
                continue
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Return top results
        top_results = similarities[:limit]
        
        print(f"\n4. Top {len(top_results)} results:")
        for i, result in enumerate(top_results, 1):
            print(f"   {i}. {result['title'][:60]}...")
            print(f"      Similarity: {result['similarity']:.4f}")
            print(f"      URL: {result['url']}")
            if result['notes']:
                print(f"      Notes: {result['notes'][:100]}...")
            print()
        
        return top_results
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def test_vector_search():
    """Test the vector search functionality"""
    
    print("🧪 Testing Vector Search Functionality")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "React hooks",
        "JavaScript promises",
        "Python machine learning",
        "Database design",
        "Web development"
    ]
    
    for query in test_queries:
        print(f"\n{'='*20} Testing: '{query}' {'='*20}")
        results = vector_search(query, limit=3)
        
        if results:
            print(f"✅ Found {len(results)} results for '{query}'")
        else:
            print(f"❌ No results found for '{query}'")
    
    print(f"\n🎉 Vector search test completed!")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        # Search for the provided query
        query = " ".join(sys.argv[1:])
        vector_search(query)
    else:
        # Run test
        test_vector_search()

if __name__ == "__main__":
    main() 