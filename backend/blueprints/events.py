"""
Events Blueprint: Multiplexed Server-Sent Events (SSE) Gateway for FUZE
Provides /api/realtime/stream with Last-Event-ID replay from Redis Streams.
"""

import json
import time
from typing import Generator
from flask import Blueprint, Response, request, jsonify, stream_with_context
from core.http_errors import error_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from core.logging_config import get_logger
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
        return error_response('stream_ticket_unavailable', 'Failed to create stream ticket', 503)
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
        return error_response('authorization_required', 'Authentication required for SSE stream', 401)

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return error_response('invalid_user_identity', 'Invalid user identity', 400)

    last_event_id = request.headers.get('Last-Event-ID') or request.args.get('last_event_id')

    @stream_with_context
    def generate_sse_stream() -> Generator[str, None, None]:
        # 1. Initial Connection Handshake
        yield f"event: system.connected\ndata: {json.dumps({'status': 'connected', 'user_id': user_id_int, 'time': time.time()})}\n\n"

        # 2. Live events straight from the user's Redis Stream, which is where producers write
        # (utils.event_bus.publish_pipeline_event). The old loop subscribed to a pub/sub channel
        # nothing published to, so no live event ever arrived. Each SSE id is the stream entry id:
        # on reconnect the browser sends it back as Last-Event-ID and reading resumes right after
        # it, so missed events are replayed without a separate code path.
        #
        # Uses the dedicated long-lived connection pool (utils.redis_utils.get_pubsub_client):
        # sharing the request-path pool would let SSE viewers starve every other Redis request.
        from utils.redis_utils import get_pubsub_client
        from utils.event_bus import read_user_stream, valid_stream_id
        client = get_pubsub_client()
        if not client:
            yield f"event: system.warning\ndata: {json.dumps({'message': 'Redis unavailable for live stream'})}\n\n"
            return

        cursor = last_event_id if valid_stream_id(last_event_id) else '$'
        last_ping = time.time()
        consecutive_errors = 0
        stream_started = time.time()
        MAX_STREAM_SECONDS = 30 * 60  # force periodic reconnect so one connection can't hold its
        # pool slot indefinitely; EventSource reconnects (with Last-Event-ID) on close.

        while time.time() - stream_started <= MAX_STREAM_SECONDS:
            try:
                entries = read_user_stream(client, user_id_int, cursor, block_ms=5000)
                consecutive_errors = 0
            except Exception as loop_err:
                consecutive_errors += 1
                if consecutive_errors > 10:
                    logger.error(f"sse_loop_fatal_errors: {loop_err}", extra={"user_id": user_id_int})
                    return
                time.sleep(1)
                continue

            for stream_id, evt in entries:
                cursor = stream_id
                yield f"id: {stream_id}\nevent: {evt.get('type', 'message')}\ndata: {json.dumps(evt)}\n\n"

            if time.time() - last_ping > 15:
                yield f": heartbeat {int(time.time())}\n\n"
                last_ping = time.time()

        yield f"event: system.reconnect\ndata: {json.dumps({'message': 'stream_ttl_reached'})}\n\n"

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
