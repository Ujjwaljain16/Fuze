from core.events import UserRegistered  # noqa: F401 — used as type annotation and HANDLERS dict key
from core.logging_config import get_logger

logger = get_logger(__name__)

def handle_user_registered(event: UserRegistered):
    """
    React to a new user registration.
    Potential side effects: welcome emails, default project setup, analytics.
    """
    logger.info("auth_handler_user_registered_received", email=event.email, user_id=event.user_id)
    # Placeholder for future background tasks
    # Example: SendWelcomeEmail(event.email)
    pass

HANDLERS = {
    UserRegistered: [handle_user_registered]
}
