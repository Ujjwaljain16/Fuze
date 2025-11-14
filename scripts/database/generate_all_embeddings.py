import os
from tqdm import tqdm
from dotenv import load_dotenv
from supabase import create_client, Client
from embedding_utils import get_embedding  # Your local or Gemini-based embedding function

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_TABLE = os.getenv('SUPABASE_TABLE', 'saved_content')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def needs_fixing(embedding):
    """
    Check if the embedding is missing or stored as a malformed string.
    """
    return (
        embedding is None or
        isinstance(embedding, str) or
        (isinstance(embedding, list) and len(embedding) != 384)
    )

def fetch_malformed_bookmarks():
    """
    Fetch bookmarks with missing or malformed embeddings.
    """
    print(f"\n📥 Fetching malformed or missing embeddings from '{SUPABASE_TABLE}'...")
    response = supabase.table(SUPABASE_TABLE)\
        .select("id, title, embedding")\
        .limit(1000)\
        .execute()

    bookmarks = response.data or []
    to_fix = [b for b in bookmarks if needs_fixing(b.get("embedding"))]
    print(f"🔍 Found {len(to_fix)} bookmarks needing embedding fix.")
    return to_fix

def update_bookmark_embedding(bookmark):
    """
    Re-embed and update the given bookmark row.
    """
    id = bookmark["id"]
    title = bookmark.get("title", "")
    print(f"\n🔧 Fixing ID: {id} | Title: {title[:60]}...")

    embedding = get_embedding(title)
    if hasattr(embedding, "tolist"):  # If numpy array
        embedding = embedding.tolist()

    if embedding and isinstance(embedding, list):
        try:
            supabase.table(SUPABASE_TABLE)\
                .update({"embedding": embedding})\
                .eq("id", id)\
                .execute()
            print("✅ Embedding updated.")
        except Exception as e:
            print(f"❌ Failed to update ID {id}: {e}")
    else:
        print("⚠️  Skipped due to generation failure.")

def main():
    if not all([SUPABASE_URL, SUPABASE_KEY]):
        raise ValueError("Missing required environment variables.")
    
    bookmarks_to_fix = fetch_malformed_bookmarks()
    if not bookmarks_to_fix:
        print("🎉 All embeddings are valid!")
        return

    for bookmark in tqdm(bookmarks_to_fix, desc="🔁 Fixing Embeddings"):
        update_bookmark_embedding(bookmark)

    print("\n✅ Embedding reprocessing complete!")

if __name__ == "__main__":
    main()
