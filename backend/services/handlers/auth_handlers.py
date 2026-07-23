from core.events import UserRegistered
from core.logging_config import get_logger

logger = get_logger(__name__)


def handle_user_registered(event: UserRegistered):
    """
    React to a new user registration.

    Current behavior: observability only — logs registration for audit trail.
    Future side effects (welcome emails, default project scaffolding, analytics
    pipeline) will be added here without touching the auth route or AuthService.

    IDEMPOTENCY: This handler is safe to re-run; it produces no writes.
    """
    logger.info(
        "auth_user_registered",
        user_id=event.user_id,
        email=event.email
    )


HANDLERS = {
    UserRegistered: [handle_user_registered],
}
