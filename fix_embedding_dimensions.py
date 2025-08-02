#!/usr/bin/env python3
"""
Fix embedding dimension mismatch by regenerating embeddings
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding
import time
from tqdm import tqdm

# Load environment variables
load_dotenv()

def analyze_embedding_dimensions():
    """Analyze the current state of embeddings in the database"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔍 Analyzing Embedding Dimensions")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Get all bookmarks with embeddings
        print("\n1. Getting all bookmarks with embeddings...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, embedding"
        ).not_.is_("embedding", "null").execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} bookmarks with embeddings")
        
        if not bookmarks:
            print("❌ No bookmarks with embeddings found")
            return None
        
        # Analyze dimensions
        dimensions = {}
        for bookmark in bookmarks:
            if 'embedding' in bookmark and bookmark['embedding']:
                dim = len(bookmark['embedding'])
                dimensions[dim] = dimensions.get(dim, 0) + 1
        
        print(f"\n📊 Embedding dimension analysis:")
        for dim, count in sorted(dimensions.items()):
            percentage = (count / len(bookmarks)) * 100
            print(f"   {dim} dimensions: {count} bookmarks ({percentage:.1f}%)")
        
        return dimensions
        
    except Exception as e:
        print(f"❌ Error analyzing embeddings: {str(e)}")
        return None

def fix_embedding_dimensions():
    """Regenerate embeddings with correct dimensions"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔧 Fixing Embedding Dimensions")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Clear Redis cache to ensure fresh embeddings
        print("\n1. Clearing Redis cache...")
        try:
            from redis_utils import redis_cache
            if redis_cache.connected:
                # Clear all embedding cache keys
                keys = redis_cache.redis_client.keys("fuze:embedding:*")
                if keys:
                    redis_cache.redis_client.delete(*keys)
                    print(f"✅ Cleared {len(keys)} cached embeddings")
                else:
                    print("ℹ️  No cached embeddings found")
            else:
                print("⚠️  Redis not connected, skipping cache clear")
        except Exception as e:
            print(f"⚠️  Error clearing cache: {e}")
        
        # Analyze current state
        dimensions = analyze_embedding_dimensions()
        if not dimensions:
            return
        
        # Generate a test embedding to check target dimensions
        print("\n2. Checking target embedding dimensions...")
        test_embedding = get_embedding("test")
        if hasattr(test_embedding, 'tolist'):
            test_embedding_list = test_embedding.tolist()
        else:
            test_embedding_list = list(test_embedding)
        
        target_dim = len(test_embedding_list)
        print(f"📊 Target embedding dimensions: {target_dim}")
        
        # Verify the embedding model is working correctly
        print(f"📊 Test embedding type: {type(test_embedding)}")
        print(f"📊 Test embedding shape: {test_embedding.shape if hasattr(test_embedding, 'shape') else 'N/A'}")
        
        # Check if all embeddings already have correct dimensions
        if target_dim in dimensions and len(dimensions) == 1:
            print("✅ All embeddings already have correct dimensions!")
            return
        
        # Get bookmarks that need fixing
        print("\n3. Getting bookmarks that need fixing...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, notes, extracted_text, embedding"
        ).not_.is_("embedding", "null").execute()
        
        bookmarks = response.data
        bookmarks_to_fix = []
        
        for bookmark in bookmarks:
            if 'embedding' in bookmark and bookmark['embedding']:
                current_dim = len(bookmark['embedding'])
                if current_dim != target_dim:
                    bookmarks_to_fix.append(bookmark)
        
        print(f"📊 Found {len(bookmarks_to_fix)} bookmarks needing dimension fix")
        
        if not bookmarks_to_fix:
            print("✅ No bookmarks need fixing!")
            return
        
        # Ask for confirmation
        print(f"\n⚠️  About to regenerate embeddings for {len(bookmarks_to_fix)} bookmarks")
        print(f"   Target dimensions: {target_dim}")
        response = input("Do you want to continue? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Operation cancelled")
            return
        
        # Regenerate embeddings
        print(f"\n4. Regenerating embeddings...")
        success_count = 0
        error_count = 0
        
        for bookmark in tqdm(bookmarks_to_fix, desc="🔄 Regenerating embeddings"):
            try:
                # Create text for embedding
                text_parts = []
                if bookmark.get('title'):
                    text_parts.append(bookmark['title'])
                if bookmark.get('notes'):
                    text_parts.append(bookmark['notes'])
                if bookmark.get('extracted_text'):
                    text_parts.append(bookmark['extracted_text'][:1000])
                
                if not text_parts:
                    print(f"\n⚠️  No text content for bookmark {bookmark['id']}, skipping...")
                    continue
                
                text = " ".join(text_parts)
                
                # Generate new embedding
                new_embedding = get_embedding(text)
                
                # Convert to list format
                if hasattr(new_embedding, 'tolist'):
                    new_embedding_list = new_embedding.tolist()
                else:
                    new_embedding_list = list(new_embedding)
                
                # Verify dimensions before storing
                if len(new_embedding_list) != target_dim:
                    print(f"\n⚠️  Generated embedding has wrong dimensions: {len(new_embedding_list)} vs {target_dim}")
                    print(f"   Bookmark ID: {bookmark['id']}")
                    print(f"   Text: {text[:100]}...")
                    continue
                
                # Additional verification - check if it's a valid embedding
                if not isinstance(new_embedding_list, list) or len(new_embedding_list) == 0:
                    print(f"\n⚠️  Invalid embedding generated for bookmark {bookmark['id']}")
                    continue
                
                # Update the bookmark
                update_result = supabase.table(SUPABASE_TABLE).update({
                    "embedding": new_embedding_list
                }).eq("id", bookmark['id']).execute()
                
                # Verify the update was successful
                if update_result.data:
                    success_count += 1
                else:
                    error_count += 1
                    print(f"\n⚠️  Failed to update bookmark {bookmark['id']}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                print(f"\n❌ Error updating bookmark {bookmark.get('id')}: {str(e)}")
                continue
        
        print(f"\n🎉 Embedding regeneration completed!")
        print(f"✅ Successfully updated: {success_count} bookmarks")
        print(f"❌ Errors: {error_count} bookmarks")
        
        if success_count > 0:
            print("\n🚀 Vector similarity search should now work!")
            print("Test it with: python test_vector_search.py")
            
            # Show final analysis
            print("\n📊 Final embedding analysis:")
            final_dimensions = analyze_embedding_dimensions()
            if final_dimensions:
                if target_dim in final_dimensions and len(final_dimensions) == 1:
                    print("✅ All embeddings now have consistent dimensions!")
                else:
                    print("⚠️  Some embeddings may still have inconsistent dimensions")
                    print("   This might indicate a deeper issue with the embedding model or storage.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Main function with options"""
    print("🔧 Embedding Dimension Fix Tool")
    print("=" * 50)
    print("1. Analyze current embedding dimensions")
    print("2. Fix embedding dimensions")
    print("3. Both")
    
    choice = input("\nChoose an option (1-3): ").strip()
    
    if choice == "1":
        analyze_embedding_dimensions()
    elif choice == "2":
        fix_embedding_dimensions()
    elif choice == "3":
        analyze_embedding_dimensions()
        print("\n" + "="*50)
        fix_embedding_dimensions()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main() 