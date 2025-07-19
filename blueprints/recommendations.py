from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, Task, User, SavedContent, Feedback
from sqlalchemy import func
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
from supabase import create_client
import os
from embedding_utils import get_embedding
from ai_recommendation_engine import SmartRecommendationEngine

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xyzcompany.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "your-supabase-service-role-key")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")  # Use saved_content table
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize the smart recommendation engine
smart_engine = SmartRecommendationEngine()

@recommendations_bp.route('/general', methods=['GET'])
@jwt_required()
def general_recommendations():
    """Get robust recommendations using semantic embeddings and feedback"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Get all user's saved content
    user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    if not user_bookmarks:
        return jsonify({"recommendations": []}), 200

    # Build user profile vector (average of all their bookmark embeddings)
    user_embs = [np.array(sc.embedding) for sc in user_bookmarks if sc.embedding is not None]
    if not user_embs:
        return jsonify({"recommendations": []}), 200
    user_profile = np.mean(user_embs, axis=0)

    # Get all content except user's own bookmarks
    all_content = SavedContent.query.filter(SavedContent.user_id != user_id).all()
    if not all_content:
        return jsonify({"recommendations": []}), 200

    # Compute similarity to user profile
    content_embs = [np.array(c.embedding) for c in all_content if c.embedding is not None]
    content_ids = [c.id for c in all_content if c.embedding is not None]
    if not content_embs:
        return jsonify({"recommendations": []}), 200
    content_embs = np.stack(content_embs)
    user_profile_norm = np.linalg.norm(user_profile)
    content_norms = np.linalg.norm(content_embs, axis=1)
    similarities = np.dot(content_embs, user_profile) / (content_norms * user_profile_norm + 1e-8)

    # Feedback boosting/demotion
    feedbacks = Feedback.query.filter(Feedback.user_id==user_id, Feedback.content_id.in_(content_ids)).all()
    feedback_map = {(f.content_id, f.feedback_type): f for f in feedbacks}
    for i, cid in enumerate(content_ids):
        if (cid, 'relevant') in feedback_map:
            similarities[i] += 0.15  # Boost relevant
        if (cid, 'not_relevant') in feedback_map:
            similarities[i] -= 0.15  # Demote not relevant

    # Add relevance threshold - only show recommendations above 0.25 (25%)
    RELEVANCE_THRESHOLD = 0.25
    relevant_indices = [i for i, sim in enumerate(similarities) if sim >= RELEVANCE_THRESHOLD]
    
    if not relevant_indices:
        return jsonify({"recommendations": []}), 200

    # Sort and diversify (top N, avoid near-duplicates)
    N = 10
    sorted_indices = np.argsort(similarities)[::-1]
    seen_urls = set()
    recommendations = []
    for idx in sorted_indices:
        if idx not in relevant_indices:  # Skip irrelevant ones
            continue
        c = all_content[idx]
        if c.url in seen_urls:
            continue
        seen_urls.add(c.url)
        recommendations.append({
            "id": c.id,
            "title": c.title,
            "url": c.url,
            "description": c.notes or c.extracted_text or "",
            "score": float(similarities[idx]),
            "reason": "Similar to your saved content about {}".format(c.category or 'technology')
        })
        if len(recommendations) >= N:
            break

    return jsonify({"recommendations": recommendations}), 200

@recommendations_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def recommend_for_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""
    
    # Get all user's bookmarks with embeddings
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    bookmarks_with_emb = [b for b in bookmarks if b.embedding is not None]
    
    if not bookmarks_with_emb:
        return jsonify({"message": "No bookmarks with embeddings found."}), 200
    
    # Prepare project context for AI analysis
    project_context = {
        'title': project.title,
        'description': project.description or '',
        'technologies': project.technologies or '',
        'user_interests': user_interests
    }
    
    # Convert bookmarks to dict format for AI engine
    bookmark_dicts = []
    for bookmark in bookmarks_with_emb:
        bookmark_dicts.append({
            'id': bookmark.id,
            'title': bookmark.title,
            'url': bookmark.url,
            'notes': bookmark.notes or '',
            'category': bookmark.category or '',
            'extracted_text': bookmark.extracted_text or '',
            'embedding': bookmark.embedding
        })
    
    # Get smart recommendations using AI engine
    smart_recommendations = smart_engine.get_smart_recommendations(
        bookmark_dicts, 
        project_context, 
        max_recommendations=5
    )
    
    # Format recommendations for frontend
    recommendations = []
    for rec in smart_recommendations:
        recommendations.append({
            "id": rec['id'],
            "title": rec['title'],
            "url": rec['url'],
            "notes": rec['notes'],
            "category": rec['category'],
            "score": rec['score_data']['total_score'],
            "reason": rec['score_data']['reason'],
            "analysis": {
                "tech_score": rec['score_data']['tech_score'],
                "content_score": rec['score_data']['content_score'],
                "difficulty_score": rec['score_data']['difficulty_score'],
                "intent_score": rec['score_data']['intent_score'],
                "semantic_score": rec['score_data']['semantic_score'],
                "technologies": rec['score_data']['bookmark_analysis']['technologies'],
                "content_type": rec['score_data']['bookmark_analysis']['content_type'],
                "difficulty": rec['score_data']['bookmark_analysis']['difficulty'],
                "intent": rec['score_data']['bookmark_analysis']['intent']
            }
        })
    
    if not recommendations:
        return jsonify({"message": "No relevant recommendations found. Try adding more bookmarks related to your project."}), 200
    
    # Add weekend exploration (optional)
    today = datetime.now().weekday()  # 5=Saturday, 6=Sunday
    if today in [5, 6] and len(recommendations) < 5:
        # Add 1-2 explore links if we have space
        explore_candidates = sorted(bookmarks_with_emb, key=lambda b: b.saved_at or datetime.min)
        explore_ids = set(r["id"] for r in recommendations)
        explore = [
            {
                "id": b.id,
                "title": b.title,
                "url": b.url,
                "notes": b.notes,
                "category": b.category,
                "score": None,
                "reason": "Weekend Explore: You haven't visited this in a while",
                "analysis": None
            }
            for b in explore_candidates if b.id not in explore_ids
        ][:2]
        recommendations.extend(explore)
    
    return jsonify(recommendations), 200

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
    bookmarks = SavedContent.query.filter_by(user_id=project.user_id if project else None).all()
    bookmarks_with_emb = [b for b in bookmarks if b.embedding is not None]
    if not bookmarks_with_emb:
        return jsonify({"message": "No bookmarks with embeddings found."}), 200
    embs = np.stack([np.array(b.embedding) for b in bookmarks_with_emb])
    norms = np.linalg.norm(embs, axis=1)
    query_norm = np.linalg.norm(query_embedding)
    similarities = np.dot(embs, query_embedding) / (norms * query_norm + 1e-8)
    N = 8
    sorted_indices = np.argsort(similarities)[::-1]
    recommendations = [
        {
            "id": bookmarks_with_emb[idx].id,
            "title": bookmarks_with_emb[idx].title,
            "url": bookmarks_with_emb[idx].url,
            "notes": bookmarks_with_emb[idx].notes,
            "category": bookmarks_with_emb[idx].category,
            "score": float(similarities[idx]),
            "reason": "Similar to your task context"
        }
        for idx in sorted_indices[:N]
    ]
    today = datetime.now().weekday()
    if today in [5, 6]:
        explore_candidates = sorted(bookmarks_with_emb, key=lambda b: b.saved_at or datetime.min)
        explore_ids = set(r["id"] for r in recommendations)
        explore = [
            {
                "id": b.id,
                "title": b.title,
                "url": b.url,
                "notes": b.notes,
                "category": b.category,
                "score": None,
                "reason": "Explore: You haven't visited this in a while"
            }
            for b in explore_candidates if b.id not in explore_ids
        ][:2]
        recommendations.extend(explore)
    return jsonify(recommendations), 200

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

@recommendations_bp.route('/supabase-semantic', methods=['POST'])
@jwt_required()
def supabase_semantic_recommendations():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    context = data.get('context', '').strip()
    limit = data.get('limit', 10)
    if not context:
        return jsonify({'message': 'Context is required'}), 400
    query_emb = get_embedding(context)
    query_emb_list = query_emb.tolist() if hasattr(query_emb, 'tolist') else list(query_emb)
    # Updated SQL for saved_content table
    sql = f"""
        SELECT id, user_id, url, title, extracted_text as content_snippet, 
               embedding <=> ARRAY{query_emb_list} AS distance
        FROM {SUPABASE_TABLE}
        WHERE user_id = {user_id}
        ORDER BY distance ASC
        LIMIT {limit};
    """
    resp = supabase_client.rpc('execute_sql', {"sql": sql}).execute()
    if resp.status_code == 200:
        results = resp.data
        return jsonify({
            'context': context,
            'recommendations': results,
            'total': len(results)
        }), 200
    else:
        return jsonify({'message': f'Semantic recommendations failed: {resp.status_code} {resp.data}'}), 500 