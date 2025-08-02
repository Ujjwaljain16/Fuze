#!/usr/bin/env python3
"""
Check column structure in the database
"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def check_column_structure():
    """Check the column structure of the table"""
    
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")
    
    print("🔍 Checking Column Structure")
    print("=" * 50)
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        print(f"\n📋 Table: {SUPABASE_TABLE}")
        print("\n🔍 Current column information:")
        
        # Try to get column information by querying a sample
        response = supabase.table(SUPABASE_TABLE).select("*").limit(1).execute()
        
        if response.data:
            sample_record = response.data[0]
            print(f"📊 Found {len(sample_record)} columns:")
            
            for column_name, value in sample_record.items():
                if column_name == 'embedding':
                    if value is None:
                        print(f"  - {column_name}: NULL")
                    else:
                        print(f"  - {column_name}: {len(value)} dimensions (vector)")
                else:
                    value_type = type(value).__name__
                    print(f"  - {column_name}: {value_type}")
        else:
            print("❌ No data found in table")
        
        print("\n⚠️  If the embedding column shows wrong dimensions, you need to:")
        print("1. Go to Supabase SQL Editor")
        print("2. Run: ALTER TABLE saved_content DROP COLUMN IF EXISTS embedding;")
        print("3. Run: ALTER TABLE saved_content ADD COLUMN embedding vector(384);")
        print("4. Run: python generate_all_embeddings.py")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_column_structure() 