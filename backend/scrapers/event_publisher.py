"""
Scraping Event Publisher Module
Emits namespaced domain lifecycle events to Redis Pub/Sub for telemetry and pipeline orchestration.
"""

import json
from dataclasses import asdict
from typing import Any
from utils.redis_utils import get_redis_client
from core.events import Event
from core.logging_config import get_logger

logger = get_logger(__name__)

REDIS_SCRAPING_EVENTS_CHANNEL = "fuze:events:scraping"


class ScrapingEventPublisher:
    """
    Publishes immutable domain events to Redis Pub/Sub.
    """
    def __init__(self, channel_name: str = REDIS_SCRAPING_EVENTS_CHANNEL):
        self.channel_name = channel_name
        self._redis = get_redis_client()

    def publish(self, event: Event) -> bool:
        """
        Serialize domain Event and publish to Redis.
        """
        if not self._redis:
            logger.debug("redis_not_configured_skipping_event", extra={"event_class": event.__class__.__name__})
            return False

        try:
            event_data = {
                "event_type": event.__class__.__name__,
                "data": asdict(event)
            }
            # Convert datetime objects to ISO strings in JSON serialization
            payload = json.dumps(event_data, default=str)
            self._redis.publish(self.channel_name, payload)
            logger.info("scraping_event_published", extra={"event_type": event.__class__.__name__})
            return True
        except Exception as e:
            logger.warning("scraping_event_publish_failed", extra={"event_type": event.__class__.__name__, "error": str(e)})
            return False
