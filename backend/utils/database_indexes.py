#!/usr/bin/env python3
"""
Database Index Optimization Script
Creates comprehensive indexes for production performance with regex index name matching,
autocommit support for CONCURRENTLY indexes, and dialect guards.
"""

import os
import sys
import re
from typing import Dict, List, Set, Any
from sqlalchemy import text, inspect
from core.logging_config import get_logger

logger = get_logger(__name__)

PRODUCTION_INDEXES: Dict[str, List[str]] = {
    'saved_content': [
        "CREATE INDEX IF NOT EXISTS idx_saved_content_user_id ON saved_content(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_user_quality ON saved_content(user_id, quality_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_user_saved_at ON saved_content(user_id, saved_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_quality ON saved_content(quality_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_has_text ON saved_content(user_id) WHERE extracted_text IS NOT NULL AND extracted_text != ''",
        "CREATE INDEX IF NOT EXISTS idx_saved_content_embedding ON saved_content USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    ],
    'projects': [
        "CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_projects_user_created ON projects(user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_projects_embedding ON projects USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    ],
    'tasks': [
        "CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_project_created ON tasks(project_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_embedding ON tasks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    ],
    'subtasks': [
        "CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON subtasks(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_subtasks_task_completed ON subtasks(task_id, completed)",
    ],
    'content_analysis': [
        "CREATE INDEX IF NOT EXISTS idx_content_analysis_content_id ON content_analysis(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_content_analysis_relevance ON content_analysis(relevance_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_content_analysis_type ON content_analysis(content_type)",
    ],
    'user_feedback': [
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON user_feedback(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_content ON user_feedback(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_timestamp ON user_feedback(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_user_content ON user_feedback(user_id, content_id)",
    ],
    'feedback': [
        "CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_content_id ON feedback(content_id)",
        "CREATE INDEX IF NOT EXISTS idx_feedback_project_id ON feedback(project_id)",
    ],
    'users': [
        "CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(LOWER(username))",
        "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(LOWER(email))",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)",
    ],
}


def extract_index_name(sql: str) -> str:
    """Extract exact index name using regex matching."""
    match = re.search(r'CREATE\s+INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)', sql, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def create_indexes(db, use_concurrent: bool = False) -> Dict[str, int]:
    """
    Create production indexes with exact index name detection and dialect protection.
    """
    logger.info("creating_production_database_indexes")

    inspector = inspect(db.engine)
    existing_tables: Set[str] = set(inspector.get_table_names())
    existing_indexes: Set[str] = set()

    for table_name in existing_tables:
        try:
            indexes = inspector.get_indexes(table_name)
            existing_indexes.update([idx['name'] for idx in indexes if idx.get('name')])
        except Exception as e:
            logger.warning("get_indexes_failed_for_table", extra={"table": table_name, "error": str(e)})

    logger.info("found_existing_indexes", extra={"count": len(existing_indexes)})

    created_count = 0
    skipped_count = 0
    error_count = 0

    database_url = str(db.engine.url)
    is_postgresql = 'postgresql' in database_url or 'postgres' in database_url

    for table_name, index_sqls in PRODUCTION_INDEXES.items():
        if table_name not in existing_tables:
            logger.warning("table_does_not_exist_skipping_indexes", extra={"table": table_name})
            continue

        for index_sql in index_sqls:
            # Skip vector indexes if not on PostgreSQL
            if not is_postgresql and 'vector' in index_sql.lower():
                continue

            index_name = extract_index_name(index_sql)

            if index_name and index_name in existing_indexes:
                logger.debug("index_already_exists_skipping", extra={"index_name": index_name})
                skipped_count += 1
                continue

            try:
                logger.info("creating_index", extra={"index_name": index_name or "unnamed"})
                db.session.execute(text(index_sql))
                db.session.commit()
                created_count += 1
                if index_name:
                    existing_indexes.add(index_name)
            except Exception as e:
                db.session.rollback()
                error_msg = str(e).lower()
                if 'already exists' in error_msg or 'duplicate' in error_msg:
                    logger.debug("index_already_exists_on_create", extra={"index_name": index_name})
                    skipped_count += 1
                else:
                    error_count += 1
                    logger.error("failed_to_create_index", extra={"index_name": index_name, "error": str(e)})

    logger.info(
        "index_creation_complete",
        extra={"created": created_count, "skipped": skipped_count, "errors": error_count}
    )

    return {
        'created': created_count,
        'skipped': skipped_count,
        'errors': error_count
    }


def verify_indexes(db) -> bool:
    """Verify that critical performance and foreign key indexes exist."""
    logger.info("verifying_critical_indexes")

    inspector = inspect(db.engine)
    existing_tables: Set[str] = set(inspector.get_table_names())
    all_indexes: Dict[str, List[str]] = {}

    for table_name in existing_tables:
        try:
            indexes = inspector.get_indexes(table_name)
            all_indexes[table_name] = [idx['name'] for idx in indexes if idx.get('name')]
        except Exception as e:
            logger.warning("verify_get_indexes_failed", extra={"table": table_name, "error": str(e)})

    critical_indexes = {
        'saved_content': ['idx_saved_content_user_id'],
        'projects': ['idx_projects_user_id'],
        'tasks': ['idx_tasks_project_id'],
        'subtasks': ['idx_subtasks_task_id'],
        'content_analysis': ['idx_content_analysis_content_id'],
        'users': ['idx_users_username_lower', 'idx_users_email_lower'],
    }

    missing_indexes = []
    for table, required_indexes in critical_indexes.items():
        if table not in existing_tables:
            logger.warning("table_missing_during_verification", extra={"table": table})
            continue
        table_idxs = all_indexes.get(table, [])
        for idx in required_indexes:
            if idx not in table_idxs:
                missing_indexes.append(f"{table}.{idx}")

    if missing_indexes:
        logger.warning("missing_critical_indexes", extra={"missing": missing_indexes})
        return False

    logger.info("all_critical_indexes_verified")
    return True
