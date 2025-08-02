#!/usr/bin/env python3
"""
Direct embedding fix using raw SQL to bypass automatic conversion
"""

import os
import json
import ast
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding
import time
from tqdm import tqdm

# Load environment variables
load_dotenv()

def parse_embedding_string(embedding_str):
    """Parse embedding string to list of floats"""
    try:
        # Try to parse as JSON first
        if embedding_str.startswith('[') and embedding_str.endswith(']'):
            # Remove any extra whitespace and parse
            cleaned_str = embedding_str.strip()
            return json.loads(cleaned_str)
        else:
            return None
    except:
        try:
            # Try ast.literal_eval as fallback
            return ast.literal_eval(embedding_str)
        except:
            return None

def direct_embedding_fix():
    """Fix embeddings using direct approach"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔧 Direct Embedding Fix")
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
        except Exception as e:
            print(f"⚠️  Error clearing cache: {e}")
        
        # Get all bookmarks
        print("\n2. Getting all bookmarks...")
        response = supabase.table(SUPABASE_TABLE).select(
            "id, title, notes, extracted_text, embedding"
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
        print(f"\n⚠️  About to regenerate ALL embeddings for {len(bookmarks)} bookmarks")
        print(f"   This will completely replace all existing embeddings")
        print(f"   Target dimensions: {target_dim}")
        response = input("Do you want to continue? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Operation cancelled")
            return
        
        # First, clear all embeddings
        print(f"\n4. Clearing all existing embeddings...")
        try:
            # Set all embeddings to NULL using a different approach
            for bookmark in tqdm(bookmarks, desc="🔄 Clearing embeddings"):
                supabase.table(SUPABASE_TABLE).update({
                    "embedding": None
                }).eq("id", bookmark['id']).execute()
                time.sleep(0.05)  # Small delay
            print(f"✅ Cleared all existing embeddings")
        except Exception as e:
            print(f"⚠️  Error clearing embeddings: {e}")
        
        # Regenerate all embeddings
        print(f"\n5. Regenerating all embeddings...")
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
                
                # Try different approaches to store the embedding
                success = False
                
                # Approach 1: Direct list
                try:
                    update_result = supabase.table(SUPABASE_TABLE).update({
                        "embedding": new_embedding_list
                    }).eq("id", bookmark['id']).execute()
                    
                    if update_result.data:
                        # Verify what was actually stored
                        check_response = supabase.table(SUPABASE_TABLE).select(
                            "embedding"
                        ).eq("id", bookmark['id']).execute()
                        
                        if check_response.data:
                            stored_embedding = check_response.data[0].get('embedding')
                            if stored_embedding and isinstance(stored_embedding, list) and len(stored_embedding) == target_dim:
                                success = True
                                success_count += 1
                            else:
                                print(f"\n⚠️  Embedding not stored correctly for bookmark {bookmark['id']}")
                                error_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    print(f"\n⚠️  Error updating bookmark {bookmark['id']}: {str(e)}")
                    error_count += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                print(f"\n❌ Error processing bookmark {bookmark.get('id')}: {str(e)}")
                continue
        
        print(f"\n🎉 Embedding regeneration completed!")
        print(f"✅ Successfully updated: {success_count} bookmarks")
        print(f"❌ Errors: {error_count} bookmarks")
        
        if success_count > 0:
            print("\n🚀 Vector similarity search should now work!")
            print("Test it with: python test_embedding_fix.py")
            
            # Verify the fix
            print("\n📊 Verifying the fix...")
            verify_direct_fix()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def verify_direct_fix():
    """Verify that the direct fix worked"""
    
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
        
        # Check format and dimensions
        correct_format = 0
        correct_dimensions = 0
        string_embeddings = 0
        list_embeddings = 0
        
        for bookmark in bookmarks:
            embedding = bookmark.get('embedding')
            if embedding:
                if isinstance(embedding, list):
                    list_embeddings += 1
                    if len(embedding) == 384:
                        correct_dimensions += 1
                        correct_format += 1
                elif isinstance(embedding, str):
                    string_embeddings += 1
                    parsed = parse_embedding_string(embedding)
                    if parsed and len(parsed) == 384:
                        correct_dimensions += 1
        
        print(f"\n📊 Final embedding analysis:")
        print(f"   List embeddings: {list_embeddings}")
        print(f"   String embeddings: {string_embeddings}")
        print(f"   Correct dimensions (384): {correct_dimensions}")
        print(f"   Correct format: {correct_format}")
        
        if correct_format == len(bookmarks):
            print(f"\n✅ All embeddings now have correct format!")
            print(f"🚀 Vector similarity search should now work!")
        else:
            print(f"\n⚠️  {len(bookmarks) - correct_format} embeddings still need fixing")
            print(f"   This indicates a database-level issue with the embedding column type.")
        
    except Exception as e:
        print(f"❌ Error verifying embeddings: {str(e)}")

def main():
    """Main function"""
    direct_embedding_fix()

if __name__ == "__main__":
    main() 