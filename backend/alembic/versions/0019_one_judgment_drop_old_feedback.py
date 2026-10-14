"""One current judgment per bookmark and project; drop the superseded feedback table and a dead column

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-14

user_feedback is where recommendation ratings are stored, but nothing stopped the same rating from being stored
again: five quick clicks on one thumb made five identical rows, and an evaluation would count that one opinion
five times. Keep the newest row of each (user, bookmark, project) and make a second one impossible. The index covers
ratings that name a project only: deleting a project sets its ratings' project_id to NULL (0016), and those must
not collide with a rating the user gave the same bookmark for no project. Ratings with no project are kept to one
by the application, which replaces the earlier one.

`feedback` was an earlier, separate table with its own endpoint (`/api/feedback`) that nothing in the app called.
It held no rows in production, and its UNIQUE constraint and a second index covered the same two columns.
user_feedback replaced it.

`saved_content.published_at` was never written by any code path and is NULL in every row. (The fetchers do read
a publication date, but it stays inside the fetch result.) `language` stays: the extension's page capture sets it.

The duplicate rows deleted here cannot be restored by downgrade(), which only restores the structure.
"""
from alembic import op

revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DELETE FROM user_feedback AS older
        USING user_feedback AS newer
        WHERE older.user_id = newer.user_id
          AND older.content_id = newer.content_id
          AND COALESCE(older.project_id, 0) = COALESCE(newer.project_id, 0)
          AND older.id < newer.id
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_feedback_judgment "
               "ON user_feedback (user_id, content_id, project_id) WHERE project_id IS NOT NULL")
    op.execute("DROP TABLE IF EXISTS feedback")
    op.execute("ALTER TABLE saved_content DROP COLUMN IF EXISTS published_at")


def downgrade():
    op.execute("ALTER TABLE saved_content ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE")
    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            content_id INTEGER NOT NULL REFERENCES saved_content(id) ON DELETE CASCADE,
            feedback_type VARCHAR(20) NOT NULL,
            timestamp TIMESTAMP DEFAULT now(),
            CONSTRAINT _user_content_feedback_uc UNIQUE (user_id, content_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_user_id ON feedback (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_project_id ON feedback (project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_content_id ON feedback (content_id)")
    op.execute("DROP INDEX IF EXISTS uq_user_feedback_judgment")
