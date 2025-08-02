# 🚀 pgvector Setup Guide for True Vector Similarity Search

## Overview

This guide will help you enable **true AI-powered vector similarity search** in your Supabase database using pgvector. This will make your semantic search much more powerful and accurate.

## Prerequisites

- ✅ Supabase project set up
- ✅ Supabase credentials configured in `.env` file
- ✅ Python environment with required packages

## Step-by-Step Setup

### Step 1: Enable pgvector Extension

1. **Go to Supabase Dashboard**
   - Visit [https://supabase.com/dashboard](https://supabase.com/dashboard)
   - Select your project (`fuze-backend`)

2. **Open SQL Editor**
   - In the left sidebar, click **"SQL Editor"**
   - Click **"New Query"**

3. **Run the Extension Command**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

4. **Click "Run"** to execute the command

5. **Verify Installation**
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

### Step 2: Add Vector Column to Table

1. **In the same SQL Editor**, run this command:
   ```sql
   -- Add vector column to saved_content table
   ALTER TABLE saved_content 
   ADD COLUMN IF NOT EXISTS embedding vector(384);
   ```

2. **Create Vector Index** (for fast similarity search):
   ```sql
   -- Create an index for vector similarity search
   CREATE INDEX IF NOT EXISTS saved_content_embedding_idx 
   ON saved_content 
   USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   ```

3. **Verify the column was added**:
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'saved_content' 
   AND column_name = 'embedding';
   ```

### Step 3: Generate Embeddings for Existing Bookmarks

1. **Run the backfill script**:
   ```bash
   python backfill_supabase_embeddings.py
   ```

2. **The script will**:
   - Connect to your Supabase database
   - Find all bookmarks without embeddings
   - Generate AI embeddings for each bookmark
   - Store the embeddings in the database
   - Test vector similarity search

### Step 4: Update Your Search Code

The search code is already updated to use vector similarity when available. The system will automatically:

1. **Try vector similarity search first** (if embeddings exist)
2. **Fall back to enhanced local search** (if vector search fails)
3. **Provide the best results possible**

## What This Enables

### Before pgvector:
- ✅ Basic text search
- ✅ Enhanced local search with word matching
- ✅ Fallback mechanisms

### After pgvector:
- 🚀 **True AI-powered semantic search**
- 🚀 **Vector similarity matching**
- 🚀 **Understanding of meaning, not just keywords**
- 🚀 **Much more accurate search results**

## Example Queries That Will Work Better

| Query | What it finds |
|-------|---------------|
| "React hooks" | Finds React hooks tutorials, useState, useEffect articles |
| "OAuth2 login" | Finds authentication guides, login flows, security articles |
| "API best practices" | Finds REST API guides, endpoint design, documentation |
| "CSS animations" | Finds animation tutorials, keyframes, transitions |

## Testing Your Setup

### 1. Check Extension Status
```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### 2. Check Vector Column
```sql
SELECT COUNT(*) as total_bookmarks,
       COUNT(embedding) as bookmarks_with_embeddings
FROM saved_content;
```

### 3. Test Vector Search
```sql
-- Test with a sample query
SELECT title, url, 
       embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM saved_content 
WHERE embedding IS NOT NULL
ORDER BY distance ASC
LIMIT 5;
```

## Troubleshooting

### "Extension not found" Error
- Make sure you're in the correct Supabase project
- Check that the extension was created successfully
- Try running the CREATE EXTENSION command again

### "Column already exists" Error
- This is normal if the column was already added
- The script will handle this gracefully

### "Vector dimension mismatch" Error
- Make sure the vector column is created with `vector(384)`
- This matches the embedding dimension from your AI model

### "Index creation failed" Error
- This might happen if there's not enough data
- The index will be created automatically when you have more bookmarks

## Performance Tips

1. **Index Size**: The `lists = 100` parameter is good for small to medium datasets
2. **Batch Processing**: The backfill script processes bookmarks one by one to avoid rate limits
3. **Query Optimization**: Vector similarity queries are automatically optimized by pgvector

## Monitoring

### Check Embedding Status
```sql
-- See how many bookmarks have embeddings
SELECT 
    COUNT(*) as total,
    COUNT(embedding) as with_embeddings,
    ROUND(COUNT(embedding) * 100.0 / COUNT(*), 2) as percentage
FROM saved_content;
```

### Monitor Search Performance
- Vector similarity searches are typically very fast
- The index makes queries efficient even with thousands of bookmarks

## Next Steps

After completing this setup:

1. **Test semantic search** in your bookmarks page
2. **Add new bookmarks** - they'll automatically get embeddings
3. **Enjoy AI-powered search** that understands meaning, not just keywords!

## Need Help?

If you encounter any issues:

1. Check the Supabase logs in your dashboard
2. Verify your `.env` file has the correct credentials
3. Make sure the pgvector extension is enabled
4. Run the backfill script to generate embeddings

Your semantic search will now be powered by true AI vector similarity! 🚀 