import logging
from typing import Dict, List, Type
from core.events import Event

# Import domain-specific handlers
from .project_handlers import HANDLERS as PROJECT_HANDLERS
from .auth_handlers import HANDLERS as AUTH_HANDLERS
from .recommendation_handlers import HANDLERS as REC_HANDLERS

logger = logging.getLogger(__name__)

# Consolidate all domain handlers into a single system-wide registry
EVENT_HANDLERS: Dict[Type[Event], List] = {}

def _merge_handlers(source: Dict):
    for event_type, handlers in source.items():
        if event_type not in EVENT_HANDLERS:
            EVENT_HANDLERS[event_type] = []
        EVENT_HANDLERS[event_type].extend(handlers)

# Merge all domain registries
_merge_handlers(PROJECT_HANDLERS)
_merge_handlers(AUTH_HANDLERS)
_merge_handlers(REC_HANDLERS)

logger.info(f"Synchronous event bus initialized with {len(EVENT_HANDLERS)} event types.")
