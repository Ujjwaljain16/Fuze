from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Feedback
from sqlalchemy import func

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

@feedback_bp.route('', methods=['POST'])
@jwt_required()
def submit_feedback():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    project_id = data.get('project_id')
    content_id = data.get('content_id')
    feedback_type = data.get('feedback_type')
    if not content_id or feedback_type not in ['relevant', 'not_relevant']:
        return jsonify({"message": "content_id and valid feedback_type are required ('relevant' or 'not_relevant')"}), 400
    feedback = Feedback.query.filter_by(user_id=user_id, project_id=project_id, content_id=content_id).first()
    if feedback:
        feedback.feedback_type = feedback_type
        feedback.timestamp = func.now()
    else:
        feedback = Feedback(user_id=user_id, project_id=project_id, content_id=content_id, feedback_type=feedback_type)
        db.session.add(feedback)
    try:
        db.session.commit()
        return jsonify({"message": "Feedback recorded"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error saving feedback: {str(e)}"}), 500 