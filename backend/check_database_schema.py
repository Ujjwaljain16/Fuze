#!/usr/bin/env python3
"""
Script to check database schema and embedding status
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_production import app, db
from models import Project, Task, Subtask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_schema():
    """Check database schema and embedding status"""

    with app.app_context():
        # Check projects table
        logger.info('=== PROJECTS TABLE ===')
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('projects')]
        logger.info(f'Columns in projects table: {columns}')

        # Check for old embedding columns
        old_columns = ['tech_embedding', 'description_embedding', 'combined_embedding', 'embeddings_updated']
        existing_old_columns = [col for col in old_columns if col in columns]

        if existing_old_columns:
            logger.warning(f'⚠️  Found old embedding columns in projects table: {existing_old_columns}')
            logger.info('These can be safely dropped since we now use the single "embedding" column')

            # Show SQL to drop them
            for col in existing_old_columns:
                logger.info(f'DROP COLUMN SQL: ALTER TABLE projects DROP COLUMN {col};')
        else:
            logger.info('✅ No old embedding columns found in projects table')

        # Check tasks table
        logger.info('\n=== TASKS TABLE ===')
        task_columns = [col['name'] for col in inspector.get_columns('tasks')]
        logger.info(f'Columns in tasks table: {task_columns}')

        # Check subtasks table
        logger.info('\n=== SUBTASKS TABLE ===')
        subtask_columns = [col['name'] for col in inspector.get_columns('subtasks')]
        logger.info(f'Columns in subtasks table: {subtask_columns}')

        # Check embedding status
        logger.info('\n=== EMBEDDING STATUS ===')
        projects_with_embeddings = Project.query.filter(Project.embedding.isnot(None)).count()
        total_projects = Project.query.count()

        tasks_with_embeddings = Task.query.filter(Task.embedding.isnot(None)).count()
        total_tasks = Task.query.count()

        subtasks_with_embeddings = Subtask.query.filter(Subtask.embedding.isnot(None)).count()
        total_subtasks = Subtask.query.count()

        logger.info(f'Projects: {projects_with_embeddings}/{total_projects} have embeddings')
        logger.info(f'Tasks: {tasks_with_embeddings}/{total_tasks} have embeddings')
        logger.info(f'Subtasks: {subtasks_with_embeddings}/{total_subtasks} have embeddings')

if __name__ == "__main__":
    logger.info("🔍 Checking database schema and embedding status...")
    check_database_schema()
    logger.info("✅ Database schema check completed!")
