"""Schema cleanup for the intent x content engine

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-12

- Index the foreign keys the intent engine joins on (tasks.project_id, subtasks.task_id).
- Drop indexes whose leading column is already covered by a composite index.
- Drop columns nothing reads any more: project/task/subtask embeddings (intent is built from
  their text), the old intent JSON on projects (intent statements are cached per context), and
  content_analysis.relevance_score (the query-independent multiplier removed from ranking).
"""
from alembic import op

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_created ON tasks (project_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_subtasks_task_created ON subtasks (task_id, created_at)")

    # Covered by _user_url_uc (user_id, url) / idx_saved_content_user_* composites.
    op.execute("DROP INDEX IF EXISTS ix_saved_content_user_id")
    op.execute("DROP INDEX IF EXISTS ix_saved_content_quality_score")
    # Covered by idx_projects_user_created (user_id, created_at).
    op.execute("DROP INDEX IF EXISTS ix_projects_user_id")
    op.execute("DROP INDEX IF EXISTS ix_projects_created_at")

    op.execute("DROP INDEX IF EXISTS idx_subtask_embedding_hnsw")
    for table in ("projects", "tasks", "subtasks"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS embedding")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS embedding_metadata")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS intent_analysis")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS intent_analysis_updated")
    op.execute("ALTER TABLE content_analysis DROP COLUMN IF EXISTS relevance_score")


def downgrade():
    op.execute("ALTER TABLE content_analysis ADD COLUMN IF NOT EXISTS relevance_score INTEGER DEFAULT 0")
    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS intent_analysis_updated TIMESTAMP")
    op.execute("ALTER TABLE projects ADD COLUMN IF NOT EXISTS intent_analysis JSON")
    for table in ("projects", "tasks", "subtasks"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedding_metadata JSON")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS embedding vector(384)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_subtask_embedding_hnsw ON subtasks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_created_at ON projects (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_projects_user_id ON projects (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_saved_content_quality_score ON saved_content (quality_score)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_saved_content_user_id ON saved_content (user_id)")
    op.execute("DROP INDEX IF EXISTS idx_subtasks_task_created")
    op.execute("DROP INDEX IF EXISTS idx_tasks_project_created")
