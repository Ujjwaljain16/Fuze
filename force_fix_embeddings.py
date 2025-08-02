#!/usr/bin/env python3
"""
Force fix embeddings by completely removing and regenerating them
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding
import time
from tqdm import tqdm

# Load environment variables
load_dotenv()

def force_fix_embeddings():
    """Completely remove and regenerate all embeddings"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔧 Force Fix Embeddings")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Clear Redis cache
        print("\n1. Clearing Redis cache...")
        try:
            from redis_utils import redis_cache
            if redis_cache.connected:
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
        
        # Get all bookmarks that need embeddings
        print("\n2. Getting all bookmarks...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, notes, extracted_text"
        ).execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} total bookmarks")
        
        if not bookmarks:
            print("❌ No bookmarks found")
            return
        
        # Test embedding generation
        print("\n3. Testing embedding generation...")
        test_embedding = get_embedding("test")
        if hasattr(test_embedding, 'tolist'):
            test_embedding_list = test_embedding.tolist()
        else:
            test_embedding_list = list(test_embedding)
        
        target_dim = len(test_embedding_list)
        print(f"📊 Target embedding dimensions: {target_dim}")
        
        # Ask for confirmation
        print(f"\n⚠️  About to regenerate embeddings for {len(bookmarks)} bookmarks")
        print(f"   This will completely replace all existing embeddings")
        print(f"   Target dimensions: {target_dim}")
        response = input("Do you want to continue? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Operation cancelled")
            return
        
        # First, clear all existing embeddings
        print(f"\n4. Clearing all existing embeddings...")
        try:
            # Set all embeddings to NULL
            clear_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": None
            }).execute()
            print(f"✅ Cleared all existing embeddings")
        except Exception as e:
            print(f"⚠️  Error clearing embeddings: {e}")
        
        # Regenerate embeddings
        print(f"\n5. Regenerating embeddings...")
        success_count = 0
        error_count = 0
        
        for bookmark in tqdm(bookmarks, desc="🔄 Regenerating embeddings"):
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
                
                # Verify dimensions
                if len(new_embedding_list) != target_dim:
                    print(f"\n⚠️  Generated embedding has wrong dimensions: {len(new_embedding_list)} vs {target_dim}")
                    print(f"   Bookmark ID: {bookmark['id']}")
                    continue
                
                # Update the bookmark with new embedding
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
            print("Test it with: python test_embedding_fix.py")
            
            # Verify the fix
            print("\n📊 Verifying the fix...")
            verify_embeddings()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def verify_embeddings():
    """Verify that embeddings are now correct"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Get all bookmarks with embeddings
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, embedding"
        ).not_.is_("embedding", "null").execute()
        
        bookmarks = response.data
        print(f"📊 Found {len(bookmarks)} bookmarks with embeddings")
        
        if not bookmarks:
            print("❌ No bookmarks with embeddings found")
            return
        
        # Check dimensions
        correct = 0
        wrong = 0
        dimensions = {}
        
        for bookmark in bookmarks:
            if 'embedding' in bookmark and bookmark['embedding']:
                dim = len(bookmark['embedding'])
                dimensions[dim] = dimensions.get(dim, 0) + 1
                
                if dim == 384:
                    correct += 1
                else:
                    wrong += 1
        
        print(f"\n📊 Final embedding analysis:")
        for dim, count in sorted(dimensions.items()):
            percentage = (count / len(bookmarks)) * 100
            print(f"   {dim} dimensions: {count} bookmarks ({percentage:.1f}%)")
        
        if wrong == 0:
            print(f"\n✅ All embeddings now have correct dimensions!")
        else:
            print(f"\n⚠️  {wrong} bookmarks still have wrong dimensions")
            print(f"   This indicates a deeper issue with the embedding generation or storage.")
        
    except Exception as e:
        print(f"❌ Error verifying embeddings: {str(e)}")

def main():
    """Main function"""
    force_fix_embeddings()

if __name__ == "__main__":
    main() 