from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.logging_config import get_logger
from middleware.rate_limiting import limiter
from services.ask_service import AskError, answer_question, clamp_limit, validate_question

logger = get_logger(__name__)

ask_bp = Blueprint('ask', __name__, url_prefix='/api/ask')


@ask_bp.route('', methods=['POST'])
@jwt_required()
# Each question is an embedding plus a Gemini call billed to the user's key (or the shared one).
@limiter.limit("10 per minute;100 per day")
def ask():
    """Answer a question only from the user's own bookmarks, with numbered citations."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        question = validate_question(data.get('question'))
        result = answer_question(user_id, question, clamp_limit(data.get('limit')))
        return jsonify(result), 200
    except AskError as e:
        response = jsonify({'error': e.error, 'message': e.message})
        if e.retry_after:
            response.headers['Retry-After'] = str(e.retry_after)
        return response, e.status
    except Exception:
        logger.exception("ask_failed", extra={"user_id": user_id})
        return jsonify({'error': 'ask_unavailable',
                        'message': 'Asking your bookmarks is temporarily unavailable. Please try again.'}), 503
