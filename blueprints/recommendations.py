from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, Task, User, SavedContent, Feedback
from sqlalchemy import func
import numpy as np
from datetime import datetime

# Import the embedding function from the main app context
try:
    from app_old import get_embedding
except ImportError:
    def get_embedding(text):
        return np.zeros(384)

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

@recommendations_bp.route('/general', methods=['GET'])
@jwt_required()
def general_recommendations():
    """Get general recommendations based on user's interests and saved content"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Get user's interests and recent saved content
    user_interests = user.technology_interests or ""
    recent_content = SavedContent.query.filter_by(user_id=user_id).order_by(SavedContent.saved_at.desc()).limit(5).all()
    
    # Create context from user interests and recent content
    context_parts = [user_interests]
    for content in recent_content:
        context_parts.append(f"{content.title} {content.notes or ''}")
    
    query_context = " ".join(context_parts)
    
    # Generate embedding for the context
    query_embedding = get_embedding(query_context)
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        # Fallback to mock recommendations if embedding fails
        return jsonify({
            "recommendations": [
                {
                    "id": 1,
                    "title": "Getting Started with React Development",
                    "url": "https://react.dev/learn",
                    "description": "Learn the fundamentals of React development with this comprehensive guide.",
                    "score": 95,
                    "reason": "Based on your interest in web development"
                },
                {
                    "id": 2,
                    "title": "Python Best Practices for 2024",
                    "url": "https://realpython.com/python-best-practices/",
                    "description": "Discover the latest Python best practices and coding standards.",
                    "score": 88,
                    "reason": "Matches your technology interests"
                },
                {
                    "id": 3,
                    "title": "Modern JavaScript ES6+ Features",
                    "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
                    "description": "Explore modern JavaScript features and how to use them effectively.",
                    "score": 82,
                    "reason": "Related to your recent bookmarks"
                }
            ]
        }), 200
    
    # Get recommendations from saved content
    recommendations = db.session.query(SavedContent).filter_by(user_id=user_id).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all()
    
    if not recommendations:
        # Return mock recommendations if no saved content
        return jsonify({
            "recommendations": [
                {
                    "id": 1,
                    "title": "Welcome to Fuze - Your Smart Bookmark Manager",
                    "url": "https://github.com/your-repo/fuze",
                    "description": "Learn how to make the most of your intelligent bookmark manager.",
                    "score": 100,
                    "reason": "Perfect for new users"
                },
                {
                    "id": 2,
                    "title": "Productivity Tips for Developers",
                    "url": "https://dev.to/productivity-tips",
                    "description": "Boost your development workflow with these proven productivity techniques.",
                    "score": 90,
                    "reason": "Based on your profile"
                }
            ]
        }), 200
    
    # Convert to response format
    recommendations_data = []
    for i, content in enumerate(recommendations):
        score = max(60, 100 - (i * 5))  # Score based on position
        recommendations_data.append({
            "id": content.id,
            "title": content.title,
            "url": content.url,
            "description": content.notes or "",
            "score": score,
            "reason": f"Similar to your saved content about {content.category or 'technology'}"
        })
    
    return jsonify({"recommendations": recommendations_data}), 200

@recommendations_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def recommend_for_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""
    if (not project.description or not project.description.strip()) and (not project.technologies or not project.technologies.strip()):
        query_context = user_interests or project.title or ""
    else:
        query_context = (
            f"Project Title: {project.title}. "
            f"Project Description: {project.description}. "
            f"Project Technologies: {project.technologies}. "
            f"User Interests: {user_interests}"
        )
    query_embedding = get_embedding(query_context)
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        return jsonify({"message": "Failed to generate query embedding or empty embedding."}), 500
    recommendations = db.session.query(SavedContent).filter_by(user_id=user_id).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all()
    if not recommendations:
        return jsonify({"message": "No recommendations found for this project."}), 200
    # Feedback boosting/demoting
    rec_ids = [c.id for c in recommendations]
    feedbacks = Feedback.query.filter(Feedback.user_id==user_id, Feedback.project_id==project_id, Feedback.content_id.in_(rec_ids)).all()
    feedback_map = {(f.content_id, f.feedback_type): f for f in feedbacks}
    def feedback_score(content):
        if (content.id, 'relevant') in feedback_map:
            return -1  # Boost relevant
        if (content.id, 'not_relevant') in feedback_map:
            return 1   # Demote not relevant
        return 0
    recommendations.sort(key=feedback_score)
    recommendations_data = [{
        "id": content.id,
        "title": content.title,
        "url": content.url,
        "source": content.source,
        "notes": content.notes,
        "saved_at": content.saved_at.isoformat(),
    } for content in recommendations]
    return jsonify(recommendations_data), 200

@recommendations_bp.route('/task/<int:task_id>', methods=['GET'])
@jwt_required()
def recommend_for_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    project = Project.query.get(task.project_id)
    user = User.query.get(project.user_id) if project else None
    user_interests = user.technology_interests if user else ""
    if (not task.description or not task.description.strip()):
        context = f"{task.title}. {project.title if project else ''}. {project.description if project else ''}. {project.technologies if project else ''}. {user_interests}"
    else:
        context = f"Task: {task.title}. {task.description}. Project: {project.title if project else ''}. {project.description if project else ''}. {project.technologies if project else ''}. {user_interests}"
    query_embedding = get_embedding(context)
    if query_embedding is None or (isinstance(query_embedding, list) and all(v == 0 for v in query_embedding)):
        return jsonify({"message": "Failed to generate query embedding or empty embedding."}), 500
    results = db.session.query(SavedContent).filter_by(user_id=project.user_id if project else None).order_by(
        SavedContent.embedding.op('<=>')(query_embedding)
    ).limit(10).all()
    rec_ids = [c.id for c in results]
    feedbacks = Feedback.query.filter(Feedback.user_id==project.user_id if project else None, Feedback.project_id==project.id if project else None, Feedback.content_id.in_(rec_ids)).all()
    feedback_map = {(f.content_id, f.feedback_type): f for f in feedbacks}
    def feedback_score(content):
        if (content.id, 'relevant') in feedback_map:
            return -1
        if (content.id, 'not_relevant') in feedback_map:
            return 1
        return 0
    results.sort(key=feedback_score)
    output = [{
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "tags": c.tags,
        "category": c.category,
        "notes": c.notes,
        "saved_at": c.saved_at.isoformat()
    } for c in results]
    return jsonify(output), 200 

@recommendations_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Submit feedback on recommendations to improve future suggestions"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'content_id' not in data or 'feedback_type' not in data:
        return jsonify({"message": "Missing required fields"}), 400
    
    content_id = data['content_id']
    feedback_type = data['feedback_type']
    project_id = data.get('project_id')  # Optional
    
    # Validate feedback type
    if feedback_type not in ['relevant', 'not_relevant']:
        return jsonify({"message": "Invalid feedback type"}), 400
    
    # Check if feedback already exists
    existing_feedback = Feedback.query.filter_by(
        user_id=user_id,
        content_id=content_id,
        project_id=project_id
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.feedback_type = feedback_type
        existing_feedback.updated_at = datetime.utcnow()
    else:
        # Create new feedback
        new_feedback = Feedback(
            user_id=user_id,
            content_id=content_id,
            project_id=project_id,
            feedback_type=feedback_type
        )
        db.session.add(new_feedback)
    
    try:
        db.session.commit()
        return jsonify({"message": "Feedback submitted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error submitting feedback"}), 500 