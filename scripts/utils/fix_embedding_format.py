#!/usr/bin/env python3
"""
Fix embedding format by converting string representations to proper vectors
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

def fix_embedding_format():
    """Fix embedding format in the database"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔧 Fixing Embedding Format")
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
            return
        
        # Analyze current format
        print("\n2. Analyzing current embedding format...")
        string_embeddings = 0
        list_embeddings = 0
        correct_dimensions = 0
        
        for bookmark in bookmarks:
            embedding = bookmark.get('embedding')
            if embedding:
                if isinstance(embedding, str):
                    string_embeddings += 1
                    # Try to parse the string
                    parsed = parse_embedding_string(embedding)
                    if parsed and len(parsed) == 384:
                        correct_dimensions += 1
                elif isinstance(embedding, list):
                    list_embeddings += 1
                    if len(embedding) == 384:
                        correct_dimensions += 1
        
        print(f"   String embeddings: {string_embeddings}")
        print(f"   List embeddings: {list_embeddings}")
        print(f"   Correct dimensions (384): {correct_dimensions}")
        
        # Check if we need to regenerate or just fix format
        if string_embeddings > 0:
            print(f"\n3. Found {string_embeddings} embeddings stored as strings")
            print("   These need to be converted to proper vector format")
            
            # Ask for confirmation
            response = input("Do you want to fix the embedding format? (y/N): ").strip().lower()
            if response != 'y':
                print("❌ Operation cancelled")
                return
            
            # Fix string embeddings
            print(f"\n4. Fixing string embeddings...")
            success_count = 0
            error_count = 0
            regenerate_count = 0
            
            for bookmark in tqdm(bookmarks, desc="🔄 Fixing embeddings"):
                try:
                    embedding = bookmark.get('embedding')
                    if not embedding:
                        continue
                    
                    if isinstance(embedding, str):
                        # Try to parse the string
                        parsed_embedding = parse_embedding_string(embedding)
                        
                        if parsed_embedding and len(parsed_embedding) == 384:
                            # Successfully parsed, update with proper list
                            update_result = supabase.table(SUPABASE_TABLE).update({
                                "embedding": parsed_embedding
                            }).eq("id", bookmark['id']).execute()
                            
                            if update_result.data:
                                success_count += 1
                            else:
                                error_count += 1
                        else:
                            # Can't parse or wrong dimensions, regenerate
                            print(f"\n⚠️  Cannot parse embedding for bookmark {bookmark['id']}, regenerating...")
                            
                            # Create text for embedding
                            text_parts = []
                            if bookmark.get('title'):
                                text_parts.append(bookmark['title'])
                            if bookmark.get('notes'):
                                text_parts.append(bookmark['notes'])
                            if bookmark.get('extracted_text'):
                                text_parts.append(bookmark['extracted_text'][:1000])
                            
                            if text_parts:
                                text = " ".join(text_parts)
                                new_embedding = get_embedding(text)
                                
                                if hasattr(new_embedding, 'tolist'):
                                    new_embedding_list = new_embedding.tolist()
                                else:
                                    new_embedding_list = list(new_embedding)
                                
                                if len(new_embedding_list) == 384:
                                    update_result = supabase.table(SUPABASE_TABLE).update({
                                        "embedding": new_embedding_list
                                    }).eq("id", bookmark['id']).execute()
                                    
                                    if update_result.data:
                                        regenerate_count += 1
                                    else:
                                        error_count += 1
                                else:
                                    error_count += 1
                            else:
                                error_count += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    error_count += 1
                    print(f"\n❌ Error fixing bookmark {bookmark.get('id')}: {str(e)}")
                    continue
            
            print(f"\n🎉 Embedding format fix completed!")
            print(f"✅ Successfully converted: {success_count} embeddings")
            print(f"🔄 Regenerated: {regenerate_count} embeddings")
            print(f"❌ Errors: {error_count} embeddings")
        
        # Verify the fix
        print(f"\n5. Verifying the fix...")
        verify_embedding_format()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def verify_embedding_format():
    """Verify that embeddings are now in the correct format"""
    
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
        
    except Exception as e:
        print(f"❌ Error verifying embeddings: {str(e)}")

def main():
    """Main function"""
    fix_embedding_format()

if __name__ == "__main__":
    main() 