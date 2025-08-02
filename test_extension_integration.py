from supabase import create_client
import openai  # or your embedding generator
import numpy as np

# Setup
SUPABASE_URL = "https://your-project-url.supabase.co"
SUPABASE_KEY = "your-anon-or-service-role-key"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Replace with your actual embedding function
def generate_embedding(text):
    # Example using OpenAI
    return openai.Embedding.create(
        input=text,
        model="text-embedding-3-small"
    )['data'][0]['embedding']

def fix_bookmark_embedding(bookmark_id, title):
    print(f"🔧 Fixing embedding for bookmark ID: {bookmark_id}")
    
    # Step 1: Generate fresh embedding
    new_embedding = generate_embedding(title)

    # Step 2: Ensure it's a raw Python list of floats (not string or JSON)
    assert isinstance(new_embedding, list)
    assert isinstance(new_embedding[0], float)

    # Step 3: Update in Supabase directly as pgvector (not text)
    response = supabase.table("bookmarks").update({
        "embedding": new_embedding
    }).eq("id", bookmark_id).execute()

    if response.data:
        print("✅ Embedding updated successfully.")
    else:
        print("❌ Failed to update embedding.", response)

# Example usage
fix_bookmark_embedding(bookmark_id=199, title="JavaScript-Projects/Projects starting with S/Sorting-Visualization")
