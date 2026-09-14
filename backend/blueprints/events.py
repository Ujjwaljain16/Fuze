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
from utils.cors_utils import is_allowed_origin
from utils.stream_tickets import mint_stream_ticket, consume_stream_ticket

logger = get_logger(__name__)

events_bp = Blueprint('events', __name__, url_prefix='/api')


@events_bp.route('/realtime/stream-ticket', methods=['POST'])
@jwt_required()
def mint_realtime_stream_ticket():
    """
    Mint a short-lived, single-use ticket for opening an SSE connection.

    EventSource can't send an Authorization header, so the stream endpoint
    below authenticates via a query param instead -- this endpoint lets the
    frontend get a purpose-specific, seconds-lived ticket via a normal
    Authorization-header request first, rather than putting the actual JWT
    access token in a URL (which would leak into access logs and browser
    history for the life of that token).
    """
    user_id = int(get_jwt_identity())
    ticket = mint_stream_ticket(user_id)
    if not ticket:
        return jsonify({'message': 'Failed to create stream ticket'}), 503
    return jsonify({'ticket': ticket}), 200


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
        # SSE (EventSource) can't set an Authorization header, so fall back to
        # a single-use ticket minted via POST /api/realtime/stream-ticket.
        ticket_param = request.args.get('ticket')
        if ticket_param:
            user_id = consume_stream_ticket(ticket_param)

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
        # Uses a dedicated pubsub connection pool (utils.redis_utils.get_pubsub_client),
        # separate from the shared request-path cache pool -- see that function's
        # docstring for why sharing the pool would let SSE viewers starve every
        # other Redis-backed request in this worker.
        from utils.redis_utils import get_pubsub_client
        client = get_pubsub_client()
        if not client:
            yield f"event: system.warning\ndata: {json.dumps({'message': 'Redis unavailable for live stream'})}\n\n"
            return

        pubsub = None
        try:
            pubsub = client.pubsub()
            user_channel = f"fuze:events:channel:{user_id_int}"
            pubsub.subscribe(user_channel)

            last_ping = time.time()
            consecutive_errors = 0
            stream_started = time.time()
            MAX_STREAM_SECONDS = 30 * 60  # force periodic reconnect so any one
            # connection can't hold its pool slot indefinitely; EventSource
            # clients auto-reconnect (with Last-Event-ID replay) on close.

            while True:
                if time.time() - stream_started > MAX_STREAM_SECONDS:
                    yield f"event: system.reconnect\ndata: {json.dumps({'message': 'stream_ttl_reached'})}\n\n"
                    break

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

    sse_headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
    }
    origin = request.headers.get('Origin')
    if is_allowed_origin(origin):
        sse_headers['Access-Control-Allow-Origin'] = origin
        sse_headers['Access-Control-Allow-Credentials'] = 'true'

    return Response(
        generate_sse_stream(),
        mimetype='text/event-stream',
        headers=sse_headers
    )
