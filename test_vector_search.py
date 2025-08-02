#!/usr/bin/env python3
"""
Test vector search with real embeddings
"""

import os
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding

# Load environment variables
load_dotenv()

class VectorSearchTester:
    def __init__(self):
        """Initialize Supabase client and configuration"""
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self.SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
        
        # Create Supabase client
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")

    def get_sample_bookmark(self):
        """
        Retrieve a sample bookmark with embedding
        
        Returns:
            dict: Sample bookmark with embedding, or None if not found
        """
        print("\n1. Getting sample bookmark with embedding...")
        response = (
            self.supabase.table(self.SUPABASE_TABLE)
            .select("id, title, embedding")
            .not_.is_("embedding", "null")
            .limit(1)
            .execute()
        )
        
        if not response.data:
            print("❌ No bookmarks with embeddings found")
            return None
        
        sample_bookmark = response.data[0]
        print(f"✅ Found bookmark: {sample_bookmark['title']}")
        print(f"📊 Embedding dimensions: {len(sample_bookmark['embedding'])}")
        return sample_bookmark

    def check_embedding_compatibility(self, query_embedding, bookmark_embedding):
        """
        Check if embeddings are compatible for vector search
        
        Args:
            query_embedding (list): Query embedding vector
            bookmark_embedding (list): Bookmark embedding vector
        
        Returns:
            bool: True if compatible, False otherwise
        """
        query_dim = len(query_embedding)
        bookmark_dim = len(bookmark_embedding)
        
        print(f"\n🔍 Checking embedding compatibility:")
        print(f"   Query embedding: {query_dim} dimensions")
        print(f"   Bookmark embedding: {bookmark_dim} dimensions")
        
        if query_dim == bookmark_dim:
            print("✅ Embeddings are compatible!")
            return True
        else:
            print("❌ Embedding dimension mismatch!")
            print(f"   Expected: {query_dim} dimensions")
            print(f"   Found: {bookmark_dim} dimensions")
            return False

    def fix_embedding_dimensions(self, query_embedding, bookmark_embedding):
        """
        Fix embedding dimension mismatch by normalizing to query dimensions
        
        Args:
            query_embedding (list): Query embedding vector
            bookmark_embedding (list): Bookmark embedding vector
        
        Returns:
            tuple: (fixed_query_embedding, fixed_bookmark_embedding)
        """
        print(f"\n🔧 Fixing embedding dimensions...")
        
        # Convert to numpy arrays
        query_array = np.array(query_embedding, dtype=np.float32)
        bookmark_array = np.array(bookmark_embedding, dtype=np.float32)
        
        target_dim = len(query_embedding)
        
        # Resize bookmark embedding to match query dimensions
        if len(bookmark_array) > target_dim:
            # Truncate if too long
            bookmark_array = bookmark_array[:target_dim]
            print(f"   📏 Truncated bookmark embedding from {len(bookmark_embedding)} to {target_dim} dimensions")
        elif len(bookmark_array) < target_dim:
            # Pad with zeros if too short
            padding = np.zeros(target_dim - len(bookmark_array), dtype=np.float32)
            bookmark_array = np.concatenate([bookmark_array, padding])
            print(f"   📏 Padded bookmark embedding from {len(bookmark_embedding)} to {target_dim} dimensions")
        
        # Normalize both embeddings
        query_normalized = query_array / np.linalg.norm(query_array)
        bookmark_normalized = bookmark_array / np.linalg.norm(bookmark_array)
        
        print(f"   ✅ Normalized embeddings to unit vectors")
        
        return query_normalized.tolist(), bookmark_normalized.tolist()

    def perform_vector_search(self, query_embedding):
        """
        Perform vector similarity search using custom RPC
        
        Args:
            query_embedding (list): Embedding to search with
        
        Returns:
            list: Search results
        """
        print("\n3. Testing vector similarity search...")
        
        try:
            # Prepare the embedding for Supabase vector search
            # Convert to Postgres vector type compatible format
            pg_vector = f"[{','.join(map(str, query_embedding))}]"
            
            # Use direct table query with vector similarity
            response = (
                self.supabase.table(self.SUPABASE_TABLE)
                .select("id, title, url, embedding")
                .not_.is_("embedding", "null")
                .order(f"embedding.<=>.{pg_vector}")
                .limit(5)
                .execute()
            )
            
            if response.data:
                print("✅ Vector similarity search successful!")
                print(f"📋 Found {len(response.data)} results:")
                for i, result in enumerate(response.data, 1):
                    # Calculate and print similarity (optional)
                    bookmark_embedding = result['embedding']
                    if len(bookmark_embedding) == len(query_embedding):
                        similarity = np.dot(query_embedding, bookmark_embedding)
                        print(f"  {i}. {result['title']} (Similarity: {similarity:.4f})")
                    else:
                        print(f"  {i}. {result['title']} (Dimension mismatch: {len(bookmark_embedding)} vs {len(query_embedding)})")
                return response.data
            else:
                print("ℹ️  No results found with vector search")
                return []
        
        except Exception as e:
            print(f"❌ Vector similarity search failed: {str(e)}")
            return []

    def test_vector_search(self):
        """
        Comprehensive vector search test
        """
        print("🧪 Testing Real Vector Search")
        print("=" * 50)
        
        # Get sample bookmark
        sample_bookmark = self.get_sample_bookmark()
        if not sample_bookmark:
            return
        
        # Generate query embedding
        print("\n2. Generating query embedding...")
        test_query = "React hooks"
        query_embedding = get_embedding(test_query)
        
        # Ensure embedding is a list
        if hasattr(query_embedding, 'tolist'):
            query_embedding_list = query_embedding.tolist()
        else:
            query_embedding_list = list(query_embedding)
        
        print(f"📊 Query embedding dimensions: {len(query_embedding_list)}")
        
        # Check compatibility
        if not self.check_embedding_compatibility(query_embedding_list, sample_bookmark['embedding']):
            print("\n⚠️  Dimension mismatch detected!")
            print("💡 Solutions:")
            print("   1. Run: python fix_embedding_dimensions.py")
            print("   2. Or use: python generate_all_embeddings.py")
            print("   3. Or manually regenerate embeddings with consistent dimensions")
            return
        
        # Perform vector search
        results = self.perform_vector_search(query_embedding_list)

def main():
    try:
        tester = VectorSearchTester()
        tester.test_vector_search()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("\n💡 This error suggests a dimension mismatch between stored and query embeddings.")
        print("   Run 'python fix_embedding_dimensions.py' to fix this issue.")

if __name__ == "__main__":
    main()