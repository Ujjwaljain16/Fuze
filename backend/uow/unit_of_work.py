from core.events import Event, ProjectCreated, ProjectUpdated, ProjectDeleted
from core.logging_config import get_logger

logger = get_logger(__name__)

class UnitOfWork:
    """
    Reactive Unit of Work context manager.
    Coordinates repositories and ensures atomic commits.
    Dispatches domain events post-commit in a failure-safe loop.
    """
    
    def __init__(self, session=None):
        self.session = session or db.session
        self.events: List[Event] = []
        
        # Repositories will be lazily loaded
        self._user_repo = None
        self._project_repo = None
        self._recommendation_repo = None

    @property
    def users(self):
        if not self._user_repo:
            from repositories.user_repository import UserRepository
            self._user_repo = UserRepository(self.session)
        return self._user_repo

    @property
    def projects(self):
        if not self._project_repo:
            from repositories.project_repository import ProjectRepository
            self._project_repo = ProjectRepository(self.session)
        return self._project_repo

    @property
    def recommendations(self):
        if not self._recommendation_repo:
            from repositories.recommendation_repository import RecommendationRepository
            self._recommendation_repo = RecommendationRepository(self.session)
        return self._recommendation_repo

    def emit(self, event: Event):
        """Record a domain event to be dispatched post-commit"""
        self.events.append(event)
        logger.debug("event_recorded", event_type=type(event).__name__, event_id=event.event_id)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.info("uow_rollback", reason="exception_detected")
            self.session.rollback()
        else:
            try:
                self.session.commit()
                # Dispatch events ONLY after successful commit
                self._dispatch_events()
            except Exception as e:
                logger.error("uow_commit_failed", error=str(e))
                self.session.rollback()
                raise

    def _dispatch_events(self):
        """
        Safe dispatch loop. Failures in handlers are caught and logged
        but do not bubble up to affect the request success.
        """
        from services.handlers import EVENT_HANDLERS
        
        for event in self.events:
            event_type = type(event)
            event_handlers = EVENT_HANDLERS.get(event_type, [])
            
            for handler in event_handlers:
                try:
                    handler_name = getattr(handler, '__name__', str(handler))
                    logger.debug("dispatching_event", event_type=event_type.__name__, handler=handler_name)
                    handler(event)
                except Exception as e:
                    # Failure is contained and observable, but not disruptive to the request
                    logger.error(
                        "event_handler_failed",
                        handler=handler_name,
                        event_type=event_type.__name__,
                        event_id=event.event_id,
                        error=str(e)
                    )
