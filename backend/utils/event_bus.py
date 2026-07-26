"""
Event Bus & Redis Streams Integration for FUZE
Handles event publishing, Redis Streams append (XADD), persistent database logging,
event translation, and Last-Event-ID replay for real-time SSE consumers.
"""

import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from core.logging_config import get_logger

logger = get_logger(__name__)

STREAM_MAX_LEN = 10000

def generate_event_id() -> str:
    """Generate a globally unique, time-ordered event ID."""
    return f"evt_{uuid.uuid4().hex}"

def generate_pipeline_run_id() -> str:
    """Generate a unique correlation ID for a pipeline execution run."""
    return f"run_{uuid.uuid4().hex}"


class EventTranslator:
    """Translates internal system events into clean, public, client-facing SSE payloads."""

    @staticmethod
    def translate_to_public(event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Strip internal worker metadata and return clean public payload."""
        event_type = event_dict.get('type', 'system.notification')
        
        # Determine client-friendly status category
        category = "info"
        if ".failed" in event_type:
            category = "error"
        elif ".completed" in event_type:
            category = "success"
        elif ".started" in event_type:
            category = "progress"

        data_payload = event_dict.get('data') or {}
        
        return {
            "event_id": event_dict.get('event_id'),
            "schema_version": event_dict.get('schema_version', 1),
            "pipeline_run_id": event_dict.get('pipeline_run_id'),
            "bookmark_id": event_dict.get('bookmark_id'),
            "sequence": event_dict.get('sequence', 1),
            "type": event_type,
            "category": category,
            "data": data_payload,
            "error": event_dict.get('error'),
            "timestamp": event_dict.get('timestamp') or datetime.utcnow().isoformat()
        }


def publish_pipeline_event(
    event_type: str,
    bookmark_id: int,
    user_id: int,
    pipeline_run_id: str,
    sequence: int,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Publish an event after a database commit.
    Appends event to Redis Stream and persists event record to bookmark_events table.
    """
    try:
        event_id = generate_event_id()
        timestamp_str = datetime.utcnow().isoformat()

        event_payload = {
            "event_id": event_id,
            "schema_version": 1,
            "pipeline_run_id": pipeline_run_id,
            "bookmark_id": bookmark_id,
            "user_id": user_id,
            "sequence": sequence,
            "type": event_type,
            "data": data or {},
            "error": error,
            "metadata": metadata or {},
            "timestamp": timestamp_str
        }

        # 1. Append to Redis Stream (XADD) for real-time SSE gateway
        try:
            from utils.redis_utils import redis_cache
            if redis_cache and redis_cache.client:
                user_stream_key = f"fuze:events:stream:{user_id}"
                raw_json = json.dumps(event_payload)
                
                # XADD into user-specific Redis Stream with capped length
                redis_cache.client.xadd(
                    user_stream_key,
                    {"event": raw_json},
                    maxlen=STREAM_MAX_LEN,
                    approximate=True
                )
        except Exception as redis_err:
            logger.warning(f"redis_stream_xadd_failed: {redis_err}", extra={"event_id": event_id})

        # 2. Persist event to DB for audit logging
        try:
            from uow.unit_of_work import UnitOfWork
            from models import BookmarkEvent
            with UnitOfWork() as uow:
                evt_record = BookmarkEvent(
                    event_id=event_id,
                    bookmark_id=bookmark_id,
                    user_id=user_id,
                    pipeline_run_id=pipeline_run_id,
                    sequence=sequence,
                    type=event_type,
                    schema_version=1,
                    data=data,
                    error=error,
                    metadata_json=metadata
                )
                uow.session.add(evt_record)
        except Exception as db_err:
            logger.warning(f"bookmark_event_db_persist_failed: {db_err}", extra={"event_id": event_id})

        # 3. Emit Prometheus metrics alongside events
        try:
            from core.metrics import pipeline_events_total
            stage_name = event_type.split('.')[2] if len(event_type.split('.')) > 2 else "unknown"
            status = "completed" if ".completed" in event_type else ("failed" if ".failed" in event_type else "started")
            pipeline_events_total.labels(stage=stage_name, status=status).inc()
        except Exception:
            pass

        return EventTranslator.translate_to_public(event_payload)

    except Exception as e:
        logger.error(f"publish_pipeline_event_fatal_error: {e}", extra={"bookmark_id": bookmark_id})
        return None


def read_events_for_replay(user_id: int, last_event_id: Optional[str] = None, count: int = 50) -> List[Dict[str, Any]]:
    """
    Read events for a user from Redis Stream (Fast Replay) with automatic DB fallback to bookmark_events.
    """
    events = []
    try:
        from utils.redis_utils import redis_cache
        if redis_cache and redis_cache.client:
            user_stream_key = f"fuze:events:stream:{user_id}"
            stream_start_id = "0-0" if not last_event_id else f"{last_event_id}"

            response = redis_cache.client.xread({user_stream_key: stream_start_id}, count=count)
            if response:
                for stream_key, message_list in response:
                    for msg_id, msg_data in message_list:
                        if b'event' in msg_data or 'event' in msg_data:
                            raw_val = msg_data.get(b'event') or msg_data.get('event')
                            if isinstance(raw_val, bytes):
                                raw_val = raw_val.decode('utf-8')
                            evt_obj = json.loads(raw_val)
                            events.append(EventTranslator.translate_to_public(evt_obj))
    except Exception as e:
        logger.warning(f"redis_stream_replay_failed_falling_back_to_db: {e}", extra={"user_id": user_id})

    # DB Fallback Replay if Redis stream is trimmed or empty
    if not events and last_event_id:
        try:
            from uow.unit_of_work import UnitOfWork
            from models import BookmarkEvent
            with UnitOfWork() as uow:
                ref_evt = uow.session.query(BookmarkEvent).filter_by(event_id=last_event_id).first()
                query = uow.session.query(BookmarkEvent).filter_by(user_id=user_id)
                if ref_evt:
                    query = query.filter(BookmarkEvent.id > ref_evt.id)
                db_records = query.order_by(BookmarkEvent.id.asc()).limit(count).all()
                for rec in db_records:
                    events.append(EventTranslator.translate_to_public({
                        "event_id": rec.event_id,
                        "schema_version": rec.schema_version,
                        "pipeline_run_id": rec.pipeline_run_id,
                        "bookmark_id": rec.bookmark_id,
                        "user_id": rec.user_id,
                        "sequence": rec.sequence,
                        "type": rec.type,
                        "data": rec.data or {},
                        "error": rec.error,
                        "metadata": rec.metadata_json or {},
                        "timestamp": rec.created_at.isoformat() if rec.created_at else datetime.utcnow().isoformat()
                    }))
        except Exception as db_err:
            logger.warning(f"db_fallback_replay_failed: {db_err}", extra={"user_id": user_id})

    return events
