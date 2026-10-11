"""
Account self-service: export everything a user stored, or delete the account and all of it.

Deletion removes the user's rows table by table, children first, instead of relying only on
ON DELETE CASCADE: SQLite (the default test database) doesn't enforce foreign keys, an ORM
cascade would load every bookmark into memory first, and content_chunks.user_id has no foreign
key at all. On Postgres the cascades would do the same work; doing it explicitly means a table
that ever loses its cascade still gets emptied rather than failing the delete.

Redis holds caches, quota counters, progress keys and the live-event stream keyed by user id.
Nothing expired the stream or the monthly counters soon, so they are purged after the commit.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import delete, or_, select

from core import cache_keys
from core.logging_config import get_logger
from models import (
    BookmarkEvent, BookmarkMetadata, ContentAnalysis, ContentChunk, Feedback, Project,
    SavedContent, Subtask, Task, TokenFamily, User, UserFeedback,
)
from uow.unit_of_work import UnitOfWork
from utils.timefmt import iso_utc

logger = get_logger(__name__)

EXPORT_FORMAT_VERSION = 1


def has_usable_password(user: User) -> bool:
    """Accounts created by Google sign-in hold a random password nobody knows until one is set."""
    meta = user.user_metadata or {}
    return not meta.get('supabase_user_id') or bool(meta.get('password_set'))


def _user_redis_keys(user_id: int):
    return (*cache_keys.user_summary_keys(user_id),
            f"fuze:events:stream:{user_id}",
            f"import_progress:{user_id}",
            f"analysis_progress:{user_id}")


def _user_redis_patterns(user_id: int):
    return (cache_keys.bookmarks_pattern(user_id),
            cache_keys.projects_pattern(user_id),
            f"fuze:rate:{user_id}:*",
            f"fuze:system_key_uses:{user_id}:*",
            f"login_fail:{user_id}:*")


def purge_user_redis(user_id: int) -> None:
    """Best effort: the account is already gone, so a Redis outage only leaves keys to expire."""
    from utils.redis_utils import redis_cache
    for key in _user_redis_keys(user_id):
        try:
            redis_cache.delete_cache(key)
        except Exception as e:
            logger.warning("account_redis_key_purge_failed", user_id=user_id, key=key, error=str(e))
    for pattern in _user_redis_patterns(user_id):
        try:
            redis_cache.invalidate_query_cache(pattern)
        except Exception as e:
            logger.warning("account_redis_pattern_purge_failed", user_id=user_id, pattern=pattern, error=str(e))


class AccountService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    # --- Export ---

    def export_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Everything the user put into Fuze. No password hash, API keys, embeddings or sessions."""
        user = self.uow.users.get_by_id(user_id)
        if not user:
            return None
        session = self.uow.session

        profile = user.to_dict()
        profile['created_at'] = iso_utc(user.created_at)

        # Named columns only: loading SavedContent rows would pull every embedding vector too.
        bookmark_rows = session.execute(
            select(SavedContent.id, SavedContent.url, SavedContent.title, SavedContent.notes,
                   SavedContent.tags, SavedContent.category, SavedContent.saved_at,
                   SavedContent.scrape_status, SavedContent.extracted_text)
            .where(SavedContent.user_id == user_id)
            .order_by(SavedContent.saved_at, SavedContent.id)
        ).all()
        bookmarks = [{
            'id': row.id,
            'url': row.url,
            'title': row.title,
            'notes': row.notes,
            'tags': row.tags,
            'category': row.category,
            'saved_at': iso_utc(row.saved_at),
            'scrape_status': row.scrape_status,
            'extracted_text': row.extracted_text,
        } for row in bookmark_rows]

        return {
            'format_version': EXPORT_FORMAT_VERSION,
            'exported_at': iso_utc(datetime.now(timezone.utc)),
            'profile': profile,
            'bookmarks': bookmarks,
            'projects': self._export_projects(user_id),
            'feedback': [{
                'content_id': f.content_id,
                'project_id': f.project_id,
                'feedback_type': f.feedback_type,
                'timestamp': iso_utc(f.timestamp),
            } for f in session.scalars(
                select(Feedback).where(Feedback.user_id == user_id).order_by(Feedback.id))],
            'recommendation_feedback': [{
                'content_id': f.content_id,
                'recommendation_id': f.recommendation_id,
                'feedback_type': f.feedback_type,
                'context': f.context_data or {},
                'timestamp': iso_utc(f.timestamp),
            } for f in session.scalars(
                select(UserFeedback).where(UserFeedback.user_id == user_id).order_by(UserFeedback.id))],
        }

    def _export_projects(self, user_id: int):
        session = self.uow.session
        projects = session.scalars(
            select(Project).where(Project.user_id == user_id).order_by(Project.created_at, Project.id)).all()
        tasks = session.scalars(
            select(Task).join(Project, Task.project_id == Project.id)
            .where(Project.user_id == user_id).order_by(Task.created_at, Task.id)).all()
        subtasks = session.scalars(
            select(Subtask).join(Task, Subtask.task_id == Task.id).join(Project, Task.project_id == Project.id)
            .where(Project.user_id == user_id).order_by(Subtask.created_at, Subtask.id)).all()

        subtasks_by_task: Dict[int, list] = {}
        for s in subtasks:
            subtasks_by_task.setdefault(s.task_id, []).append({
                'id': s.id,
                'title': s.title,
                'description': s.description,
                'completed': bool(s.completed),
                'created_at': iso_utc(s.created_at),
                'updated_at': iso_utc(s.updated_at),
            })
        tasks_by_project: Dict[int, list] = {}
        for t in tasks:
            tasks_by_project.setdefault(t.project_id, []).append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'created_at': iso_utc(t.created_at),
                'subtasks': subtasks_by_task.get(t.id, []),
            })
        return [{
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'technologies': p.technologies,
            'created_at': iso_utc(p.created_at),
            'tasks': tasks_by_project.get(p.id, []),
        } for p in projects]

    # --- Deletion ---

    def delete_account(self, user_id: int) -> bool:
        """End every session, then delete the user and everything they own. Commit is the caller's
        (the UnitOfWork); purge_user_redis() should run once it has committed."""
        if not self.uow.users.get_by_id(user_id):
            return False

        from core.sessions import revoke_user_sessions
        revoke_user_sessions(self.uow, user_id, reason='account_deleted')

        content_ids = select(SavedContent.id).where(SavedContent.user_id == user_id)
        project_ids = select(Project.id).where(Project.user_id == user_id)
        task_ids = select(Task.id).where(Task.project_id.in_(project_ids))
        statements = (
            delete(ContentChunk).where(or_(ContentChunk.user_id == user_id, ContentChunk.content_id.in_(content_ids))),
            delete(BookmarkEvent).where(or_(BookmarkEvent.user_id == user_id, BookmarkEvent.bookmark_id.in_(content_ids))),
            delete(Feedback).where(or_(Feedback.user_id == user_id, Feedback.content_id.in_(content_ids),
                                       Feedback.project_id.in_(project_ids))),
            delete(UserFeedback).where(or_(UserFeedback.user_id == user_id, UserFeedback.content_id.in_(content_ids))),
            delete(ContentAnalysis).where(ContentAnalysis.content_id.in_(content_ids)),
            delete(BookmarkMetadata).where(BookmarkMetadata.bookmark_id.in_(content_ids)),
            delete(Subtask).where(Subtask.task_id.in_(task_ids)),
            delete(Task).where(Task.project_id.in_(project_ids)),
            delete(Project).where(Project.user_id == user_id),
            delete(SavedContent).where(SavedContent.user_id == user_id),
            delete(TokenFamily).where(TokenFamily.user_id == user_id),
            delete(User).where(User.id == user_id),
        )
        for statement in statements:
            self.uow.session.execute(statement.execution_options(synchronize_session=False))
        # The deleted rows may still sit in the identity map; nothing may flush them back.
        self.uow.session.expunge_all()
        logger.info("account_deleted", user_id=user_id)
        return True
