"""Add user_url unique constraint

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-12 17:00:00.000000

"""
from alembic import op
from core.logging_config import get_logger

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'

logger = get_logger(__name__)

def upgrade():
    # 1. Clean up duplicate bookmarks before adding constraint
    # Keep the most recently saved bookmark for a given (user_id, url)
    cleanup_sql = """
    DELETE FROM saved_content
    WHERE id IN (
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER(PARTITION BY user_id, url ORDER BY saved_at DESC) as rn
            FROM saved_content
        ) t WHERE t.rn > 1
    );
    """
    op.execute(cleanup_sql)
    logger.info("migration_duplicates_cleaned", table="saved_content")

    # 2. Add the UNIQUE constraint
    op.create_unique_constraint('_user_url_uc', 'saved_content', ['user_id', 'url'])
    logger.info("migration_unique_constraint_added", constraint="_user_url_uc")

def downgrade():
    op.drop_constraint('_user_url_uc', 'saved_content', type_='unique')
