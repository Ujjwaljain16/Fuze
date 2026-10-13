"""Record which project a piece of recommendation feedback was given for

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-13

A thumbs up on a recommendation means "useful for THIS project". The feedback row only kept the bookmark,
so the same bookmark liked for one project and disliked for another could not be told apart, and quality
could not be measured per project. The client could already send a project id (it was stored inside the
free-form context_data JSON); this makes it a real, indexed, queryable column.

ON DELETE SET NULL: deleting a project keeps the judgment about the bookmark, without the project.
Existing rows are backfilled from context_data where it names a project the same user owns.
"""
from alembic import op

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS project_id INTEGER "
               "REFERENCES projects(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_project ON user_feedback (project_id)")
    op.execute("""
        UPDATE user_feedback AS uf
        SET project_id = (uf.context_data ->> 'project_id')::integer
        WHERE uf.project_id IS NULL
          AND uf.context_data ->> 'project_id' ~ '^[0-9]{1,9}$'
          AND EXISTS (SELECT 1 FROM projects p
                      WHERE p.id = (uf.context_data ->> 'project_id')::integer AND p.user_id = uf.user_id)
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_user_feedback_project")
    op.execute("ALTER TABLE user_feedback DROP COLUMN IF EXISTS project_id")
