from typing import List, Optional
from core.events import Event
from core.logging_config import get_logger

logger = get_logger(__name__)


class UnitOfWork:
    """
    Reactive Unit of Work context manager.
    Coordinates repositories and ensures atomic commits.
    Dispatches domain events post-commit in a failure-safe loop.
    """

    def __init__(self, session=None):
        from models import db
        self.session = session or db.session
        self._events: List[Event] = []

        self._user_repo = None
        self._project_repo = None
        self._recommendation_repo = None
        self._bookmark_repo = None
        self._analysis_repo = None
        self._token_families = None

    @property
    def events(self) -> List[Event]:
        """Read-only view of queued events."""
        return list(self._events)

    @property
    def users(self):
        if self._user_repo is None:
            from repositories.user_repository import UserRepository
            self._user_repo = UserRepository(self.session)
        return self._user_repo

    @property
    def projects(self):
        if self._project_repo is None:
            from repositories.project_repository import ProjectRepository
            self._project_repo = ProjectRepository(self.session)
        return self._project_repo

    @property
    def recommendations(self):
        if self._recommendation_repo is None:
            from repositories.recommendation_repository import RecommendationRepository
            self._recommendation_repo = RecommendationRepository(self.session)
        return self._recommendation_repo

    @property
    def bookmarks(self):
        if self._bookmark_repo is None:
            from repositories.bookmark_repository import BookmarkRepository
            self._bookmark_repo = BookmarkRepository(self.session)
        return self._bookmark_repo

    @property
    def analyses(self):
        if self._analysis_repo is None:
            from repositories.analysis_repository import AnalysisRepository
            self._analysis_repo = AnalysisRepository(self.session)
        return self._analysis_repo

    @property
    def token_families(self):
        if self._token_families is None:
            from repositories.token_family_repository import TokenFamilyRepository
            self._token_families = TokenFamilyRepository(self.session)
        return self._token_families

    def flush(self):
        """Flush session to get IDs without committing."""
        self.session.flush()

    def emit(self, event: Event):
        """Record a domain event to be dispatched post-commit."""
        self._events.append(event)
        logger.debug("event_recorded", extra={"event_type": type(event).__name__, "event_id": getattr(event, 'event_id', None)})

    def add_event(self, event: Event):
        """Alias for emit() — backwards-compatible hook registration."""
        self.emit(event)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.info("uow_rollback", extra={"reason": "exception_detected"})
            self.session.rollback()
        else:
            try:
                self.session.commit()
            except Exception as e:
                logger.error("uow_commit_failed", extra={"error": str(e)})
                self.session.rollback()
                raise

            # Post-commit event dispatch — exception isolated from transaction rollback
            try:
                self._dispatch_events()
            except Exception as dispatch_err:
                logger.error("uow_post_commit_dispatch_failed", extra={"error": str(dispatch_err)})

    def _dispatch_events(self):
        """
        Safe dispatch loop. Failures in handlers are caught and logged
        but do not bubble up to affect the request success.
        Events list is cleared in a finally block to prevent duplicate dispatch.
        """
        from services.handlers import EVENT_HANDLERS

        events_to_dispatch = list(self._events)
        try:
            for event in events_to_dispatch:
                event_type = type(event)
                event_handlers = EVENT_HANDLERS.get(event_type, [])

                for handler in event_handlers:
                    try:
                        handler_name = getattr(handler, '__name__', str(handler))
                        logger.debug("dispatching_event", extra={"event_type": event_type.__name__, "handler": handler_name})
                        handler(event)
                    except Exception as e:
                        logger.exception(
                            "event_handler_failed",
                            extra={
                                "handler": getattr(handler, '__name__', str(handler)),
                                "event_type_name": event_type.__name__,
                                "event_id": getattr(event, 'event_id', None),
                                "error": str(e)
                            }
                        )
        finally:
            self._events.clear()
