-- Drop and recreate to ensure latest version
DROP FUNCTION IF EXISTS match_user_content(vector, uuid, float, int);

CREATE OR REPLACE FUNCTION match_user_content(
  query_embedding    vector(384),
  target_user_id     int,
  match_threshold    float   DEFAULT 0.25,
  match_count        int     DEFAULT 50
)
RETURNS TABLE (
  id             int,
  title          text,
  url            text,
  notes          text,
  extracted_text text,
  quality_score  float,
  saved_at     timestamptz,
  tags           text,
  similarity     float
)
LANGUAGE sql
STABLE          -- tells PostgreSQL this won't modify DB, enables optimization
PARALLEL SAFE   -- can run in parallel query plans
AS $$
  SELECT
    sc.id,
    sc.title,
    sc.url,
    sc.notes,
    sc.extracted_text,
    sc.quality_score,
    sc.saved_at,
    sc.tags,
    1 - (sc.embedding <=> query_embedding) AS similarity
  FROM saved_content sc
  WHERE 
    sc.user_id = target_user_id
    AND sc.embedding IS NOT NULL
    AND 1 - (sc.embedding <=> query_embedding) > match_threshold
  ORDER BY sc.embedding <=> query_embedding   -- ASC = closest first
  LIMIT match_count;
$$;

-- Grant execute to authenticated role (Supabase RLS applies automatically)
GRANT EXECUTE ON FUNCTION match_user_content TO authenticated;
GRANT EXECUTE ON FUNCTION match_user_content TO service_role;

-- Second RPC for task-specific recommendations (subtask embeddings)
CREATE OR REPLACE FUNCTION match_task_content(
  query_embedding    vector(384),
  target_user_id     int,
  target_project_id  int,
  match_threshold    float  DEFAULT 0.2,
  match_count        int    DEFAULT 30
)
RETURNS TABLE (
  id          int,
  title       text,
  url         text,
  similarity  float
)
LANGUAGE sql STABLE PARALLEL SAFE
AS $$
  SELECT
    sc.id,
    sc.title,
    sc.url,
    1 - (sc.embedding <=> query_embedding) AS similarity
  FROM saved_content sc
  JOIN projects p ON p.user_id = sc.user_id
  WHERE 
    sc.user_id = target_user_id
    AND p.id = target_project_id
    AND sc.embedding IS NOT NULL
    AND 1 - (sc.embedding <=> query_embedding) > match_threshold
  ORDER BY sc.embedding <=> query_embedding
  LIMIT match_count;
$$;

GRANT EXECUTE ON FUNCTION match_task_content TO authenticated;
GRANT EXECUTE ON FUNCTION match_task_content TO service_role;
