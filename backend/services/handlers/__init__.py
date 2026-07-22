from typing import Dict, List, Type
from core.events import Event
from core.logging_config import get_logger

logger = get_logger(__name__)

# System-wide event handler registry.
# Populated by merging domain-level HANDLERS dicts — one per domain module.
# UnitOfWork._dispatch_events() reads this registry post-commit.
EVENT_HANDLERS: Dict[Type[Event], List] = {}


def _merge_handlers(source: Dict) -> None:
    """Merge a domain-level HANDLERS dict into the system-wide registry."""
    for event_type, handlers in source.items():
        if event_type not in EVENT_HANDLERS:
            EVENT_HANDLERS[event_type] = []
        EVENT_HANDLERS[event_type].extend(handlers)


# --- Domain Handler Registries ---
# Each domain module owns its own HANDLERS dict.
# Add new domains here; never import ML/Redis/workers at this level.

from .project_handlers import HANDLERS as PROJECT_HANDLERS          # noqa: E402
from .auth_handlers import HANDLERS as AUTH_HANDLERS                # noqa: E402
from .recommendation_handlers import HANDLERS as REC_HANDLERS       # noqa: E402

_merge_handlers(PROJECT_HANDLERS)
_merge_handlers(AUTH_HANDLERS)
_merge_handlers(REC_HANDLERS)

logger.debug(
    "event_bus_initialized",
    registered_event_types=len(EVENT_HANDLERS),
    event_types=[t.__name__ for t in EVENT_HANDLERS],
)
