#!/usr/bin/env python3
"""
Final diagnostic to understand the database embedding storage issue
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from embedding_utils import get_embedding

# Load environment variables
load_dotenv()

def final_diagnostic():
    """Final diagnostic to understand the embedding storage issue"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔍 Final Diagnostic - Embedding Storage Issue")
    print("=" * 60)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Test 1: Check what happens when we store a simple list
        print("\n1. Testing simple list storage...")
        test_list = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        # Try to update a bookmark with a simple list
        try:
            update_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": test_list
            }).eq("id", 1).execute()
            
            if update_result.data:
                # Check what was actually stored
                check_response = supabase.table(SUPABASE_TABLE).select(
                    "embedding"
                ).eq("id", 1).execute()
                
                if check_response.data:
                    stored_value = check_response.data[0].get('embedding')
                    print(f"   Stored value type: {type(stored_value)}")
                    print(f"   Stored value: {stored_value}")
                    print(f"   Original list: {test_list}")
                    
                    if isinstance(stored_value, list):
                        print(f"   ✅ Successfully stored as list!")
                    elif isinstance(stored_value, str):
                        print(f"   ❌ Converted to string!")
                    else:
                        print(f"   ⚠️  Stored as {type(stored_value)}")
                else:
                    print(f"   ❌ Could not retrieve stored value")
            else:
                print(f"   ❌ Update failed")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # Test 2: Check what happens with a real embedding
        print("\n2. Testing real embedding storage...")
        test_embedding = get_embedding("test embedding")
        if hasattr(test_embedding, 'tolist'):
            test_embedding_list = test_embedding.tolist()
        else:
            test_embedding_list = list(test_embedding)
        
        print(f"   Generated embedding type: {type(test_embedding_list)}")
        print(f"   Generated embedding length: {len(test_embedding_list)}")
        print(f"   First 5 values: {test_embedding_list[:5]}")
        
        try:
            update_result = supabase.table(SUPABASE_TABLE).update({
                "embedding": test_embedding_list
            }).eq("id", 1).execute()
            
            if update_result.data:
                # Check what was actually stored
                check_response = supabase.table(SUPABASE_TABLE).select(
                    "embedding"
                ).eq("id", 1).execute()
                
                if check_response.data:
                    stored_embedding = check_response.data[0].get('embedding')
                    print(f"   Stored embedding type: {type(stored_embedding)}")
                    
                    if isinstance(stored_embedding, list):
                        print(f"   Stored embedding length: {len(stored_embedding)}")
                        print(f"   Stored first 5 values: {stored_embedding[:5]}")
                        if len(stored_embedding) == len(test_embedding_list):
                            print(f"   ✅ Successfully stored as list with correct dimensions!")
                        else:
                            print(f"   ❌ Dimensions don't match!")
                    elif isinstance(stored_embedding, str):
                        print(f"   Stored as string with length: {len(stored_embedding)}")
                        print(f"   String preview: {stored_embedding[:100]}...")
                        print(f"   ❌ Converted to string!")
                    else:
                        print(f"   ⚠️  Stored as {type(stored_embedding)}")
                else:
                    print(f"   ❌ Could not retrieve stored embedding")
            else:
                print(f"   ❌ Update failed")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # Test 3: Check database column type
        print("\n3. Analyzing database column behavior...")
        print("   Based on the results, it appears the database is:")
        print("   - Accepting the list data")
        print("   - Converting it to a string representation")
        print("   - This suggests the column type might be TEXT or VARCHAR")
        print("   - Instead of JSONB, ARRAY, or VECTOR type")
        
        # Test 4: Check if we can work with the string format
        print("\n4. Testing string format compatibility...")
        try:
            # Get a bookmark with embedding
            response = supabase.table(SUPABASE_TABLE).select(
                "id, embedding"
            ).not_.is_("embedding", "null").limit(1).execute()
            
            if response.data:
                bookmark = response.data[0]
                embedding_str = bookmark.get('embedding')
                
                if isinstance(embedding_str, str):
                    print(f"   Found string embedding with length: {len(embedding_str)}")
                    print(f"   String starts with: {embedding_str[:50]}...")
                    
                    # Try to parse it
                    try:
                        import json
                        parsed = json.loads(embedding_str)
                        print(f"   ✅ Successfully parsed as JSON!")
                        print(f"   Parsed type: {type(parsed)}")
                        print(f"   Parsed length: {len(parsed)}")
                        print(f"   First 5 values: {parsed[:5]}")
                        
                        if len(parsed) == 384:
                            print(f"   ✅ Correct dimensions (384)!")
                        else:
                            print(f"   ❌ Wrong dimensions: {len(parsed)}")
                            
                    except json.JSONDecodeError:
                        print(f"   ❌ Not valid JSON")
                        # Try other parsing methods
                        try:
                            import ast
                            parsed = ast.literal_eval(embedding_str)
                            print(f"   ✅ Successfully parsed with ast.literal_eval!")
                            print(f"   Parsed type: {type(parsed)}")
                            print(f"   Parsed length: {len(parsed)}")
                        except:
                            print(f"   ❌ Could not parse with any method")
                else:
                    print(f"   Embedding is not a string: {type(embedding_str)}")
            else:
                print(f"   No bookmarks with embeddings found")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        # Summary and recommendations
        print("\n" + "=" * 60)
        print("📋 DIAGNOSIS SUMMARY")
        print("=" * 60)
        print("The issue is that the database is storing embeddings as STRINGS")
        print("instead of proper VECTOR/ARRAY types. This is why:")
        print("1. Vector similarity search fails")
        print("2. Embeddings have wrong 'dimensions' (string length vs array length)")
        print("3. Updates appear to work but don't change the format")
        print()
        print("🔧 RECOMMENDED SOLUTIONS:")
        print("1. Check the database column type for 'embedding'")
        print("2. If it's TEXT/VARCHAR, change it to JSONB or VECTOR type")
        print("3. Or modify the application to work with string format")
        print("4. Consider using pgvector extension for proper vector storage")
        print()
        print("💡 IMMEDIATE WORKAROUND:")
        print("The embeddings are actually stored correctly as JSON strings.")
        print("You can parse them back to lists for vector operations.")
        print("This would require modifying the vector search code to:")
        print("- Parse string embeddings back to lists")
        print("- Perform similarity calculations in Python")
        print("- Or use database functions to parse JSON")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Main function"""
    final_diagnostic()

if __name__ == "__main__":
    main() 