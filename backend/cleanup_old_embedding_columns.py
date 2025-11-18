#!/usr/bin/env python3
"""
Script to drop old embedding columns that are no longer used
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_production import app, db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_old_embedding_columns():
    """Drop old embedding columns that are no longer needed"""

    with app.app_context():
        try:
            # Check current columns
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('projects')]

            # Old columns to drop
            old_columns = ['tech_embedding', 'description_embedding', 'combined_embedding', 'embeddings_updated']
            columns_to_drop = [col for col in old_columns if col in columns]

            if not columns_to_drop:
                logger.info('✅ No old embedding columns found to drop')
                return True

            logger.info(f'Found {len(columns_to_drop)} old embedding columns to drop: {columns_to_drop}')

            # Drop each column
            for column_name in columns_to_drop:
                try:
                    logger.info(f'Dropping column: {column_name}')

                    # Use raw SQL to drop the column
                    from sqlalchemy import text
                    db.session.execute(text(f'ALTER TABLE projects DROP COLUMN {column_name}'))
                    db.session.commit()

                    logger.info(f'✅ Successfully dropped column: {column_name}')

                except Exception as e:
                    logger.error(f'❌ Failed to drop column {column_name}: {e}')
                    db.session.rollback()
                    return False

            logger.info('✅ All old embedding columns have been successfully dropped!')
            return True

        except Exception as e:
            logger.error(f'❌ Error during column cleanup: {e}')
            db.session.rollback()
            return False

if __name__ == "__main__":
    logger.info("🧹 Starting cleanup of old embedding columns...")
    success = cleanup_old_embedding_columns()

    if success:
        logger.info("✅ Old embedding column cleanup completed successfully!")
    else:
        logger.error("❌ Old embedding column cleanup failed!")
        sys.exit(1)
