"""
Events Blueprint: Multiplexed Server-Sent Events (SSE) Gateway for FUZE
Provides /api/realtime/stream with Last-Event-ID replay from Redis Streams.
"""

import json
import time
from typing import Generator
from flask import Blueprint, Response, request, jsonify, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
from core.logging_config import get_logger
from utils.event_bus import read_events_for_replay

logger = get_logger(__name__)

events_bp = Blueprint('events', __name__, url_prefix='/api')


@events_bp.route('/realtime/stream', methods=['GET'])
@events_bp.route('/bookmarks/progress/stream', methods=['GET'])
@jwt_required(optional=True)
def stream_realtime_events():
    """
    Multiplexed Server-Sent Events (SSE) stream for real-time pipeline & domain events.
    Supports Last-Event-ID header for automatic event replay upon reconnection.
    """
    user_id = get_jwt_identity()
    if not user_id:
        # Check token in query param for SSE EventSource compatibility
        token_param = request.args.get('token')
        if token_param:
            try:
                from flask_jwt_extended import decode_token
                decoded = decode_token(token_param)
                user_id = decoded.get('sub')
            except Exception:
                pass

    if not user_id:
        return jsonify({'message': 'Authentication required for SSE stream'}), 401

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return jsonify({'message': 'Invalid user identity'}), 400

    last_event_id = request.headers.get('Last-Event-ID') or request.args.get('last_event_id')

    @stream_with_context
    def generate_sse_stream() -> Generator[str, None, None]:
        # 1. Initial Connection Handshake
        yield f"event: system.connected\ndata: {json.dumps({'status': 'connected', 'user_id': user_id_int, 'time': time.time()})}\n\n"

        # 2. Replay missed events if Last-Event-ID is provided
        if last_event_id:
            try:
                replayed_events = read_events_for_replay(user_id_int, last_event_id=last_event_id)
                for evt in replayed_events:
                    evt_type = evt.get('type', 'message')
                    evt_id = evt.get('event_id', '')
                    yield f"id: {evt_id}\nevent: {evt_type}\ndata: {json.dumps(evt)}\n\n"
            except Exception as replay_err:
                logger.warning(f"sse_replay_error: {replay_err}", extra={"user_id": user_id_int})

        # 3. Live Event Loop using Redis Pub/Sub / Stream polling
        from utils.redis_utils import redis_cache
        if not redis_cache or not redis_cache.client:
            yield f"event: system.warning\ndata: {json.dumps({'message': 'Redis unavailable for live stream'})}\n\n"
            return

        pubsub = None
        try:
            pubsub = redis_cache.client.pubsub()
            user_channel = f"fuze:events:channel:{user_id_int}"
            pubsub.subscribe(user_channel)

            last_ping = time.time()
            consecutive_errors = 0

            while True:
                # Keep-alive heartbeat every 15 seconds
                if time.time() - last_ping > 15:
                    yield f": heartbeat {int(time.time())}\n\n"
                    last_ping = time.time()

                try:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message['type'] == 'message':
                        raw_data = message['data']
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode('utf-8')
                        
                        evt_obj = json.loads(raw_data)
                        evt_type = evt_obj.get('type', 'message')
                        evt_id = evt_obj.get('event_id', '')
                        
                        yield f"id: {evt_id}\nevent: {evt_type}\ndata: {json.dumps(evt_obj)}\n\n"
                        consecutive_errors = 0
                except Exception as loop_err:
                    consecutive_errors += 1
                    if consecutive_errors > 10:
                        logger.error(f"sse_loop_fatal_errors: {loop_err}", extra={"user_id": user_id_int})
                        break
                    time.sleep(1)

        except Exception as stream_err:
            logger.error(f"sse_stream_exception: {stream_err}", extra={"user_id": user_id_int})
        finally:
            if pubsub:
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception:
                    pass

    return Response(
        generate_sse_stream(),
        mimetype='text/event-stream',
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': request.headers.get('Origin', '*'),
            'Access-Control-Allow-Credentials': 'true'
        }
    )
