"""
Feedback API Blueprint
Handles user feedback submissions for content items and recommendations.
"""

from flask import Blueprint, request, jsonify
from core.http_errors import error_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from models import db, Feedback, SavedContent
from core.logging_config import get_logger

logger = get_logger(__name__)

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

VALID_FEEDBACK_TYPES = {'relevant', 'not_relevant'}

@feedback_bp.route('', methods=['POST'])
@jwt_required()
def submit_feedback():
    """
    Submit or update feedback for a content item owned by the logged-in user.
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        content_id = data.get('content_id')
        feedback_type = data.get('feedback_type')

        if not content_id:
            return error_response('content_id_required', 'content_id is required', 400)

        try:
            content_id = int(content_id)
        except (ValueError, TypeError):
            return error_response('invalid_content_id', 'content_id must be an integer', 400)

        if feedback_type not in VALID_FEEDBACK_TYPES:
            return error_response('invalid_feedback_type', f"Invalid feedback_type. Must be one of {sorted(list(VALID_FEEDBACK_TYPES))}", 400)

        # Ownership & existence verification
        content = db.session.query(SavedContent).filter_by(
            id=content_id,
            user_id=user_id
        ).first()

        if not content:
            return error_response('content_not_found', 'Content not found', 404)

        # A bookmark is not tied to one project, so this endpoint records a rating without one. Ratings that
        # belong to a project go through POST /api/recommendations/feedback, which verifies the project.
        feedback = db.session.query(Feedback).filter_by(
            user_id=user_id,
            content_id=content_id
        ).first()

        if feedback:
            feedback.feedback_type = feedback_type
        else:
            feedback = Feedback(
                user_id=user_id,
                content_id=content_id,
                feedback_type=feedback_type
            )
            db.session.add(feedback)

        db.session.commit()
        logger.info("feedback_saved", user_id=user_id, content_id=content_id, feedback_type=feedback_type)
        return jsonify({'message': 'Feedback recorded'}), 200

    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("feedback_save_db_failed", user_id=user_id if 'user_id' in locals() else None)
        return error_response('internal_error', 'Failed to save feedback', 500)
    except Exception:
        logger.exception("feedback_save_unexpected_failed")
        return error_response('internal_error', 'Failed to save feedback', 500)