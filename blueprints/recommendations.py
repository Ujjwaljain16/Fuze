from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, Task, User, SavedContent, Feedback
from sqlalchemy import func
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer
import os
import json
from embedding_utils import get_embedding
from ai_recommendation_engine import SmartRecommendationEngine
from smart_task_recommendations import SmartTaskRecommendationEngine
import re
from difflib import SequenceMatcher
from collections import Counter
from unified_recommendation_engine import UnifiedRecommendationEngine
from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
from redis_utils import redis_cache

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "saved_content")

# Only create Supabase client if credentials are provided
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected successfully in recommendations")
    except Exception as e:
        print(f"⚠️ Supabase connection failed in recommendations: {e}")
        supabase_client = None
else:
    print("⚠️ Supabase credentials not provided - Supabase features disabled in recommendations")

# Initialize the recommendation engines
smart_engine = SmartRecommendationEngine()
precision_engine = SmartTaskRecommendationEngine()
unified_engine = UnifiedRecommendationEngine()

# Initialize Gemini-enhanced engine
try:
    gemini_enhanced_engine = GeminiEnhancedRecommendationEngine()
    gemini_available = True
except Exception as e:
    print(f"Warning: Gemini-enhanced engine not available: {e}")
    gemini_enhanced_engine = None
    gemini_available = False

# Redis caching functions for recommendations
def get_cached_recommendations(user_id, cache_key, cache_duration=3600):
    """Get cached recommendations from Redis"""
    if not redis_cache.connected:
        return None
    
    try:
        cache_key = f"recommendations:{user_id}:{cache_key}"
        cached_data = redis_cache.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except Exception as e:
        print(f"Redis cache get error: {e}")
    return None

def cache_recommendations(user_id, cache_key, recommendations, cache_duration=3600):
    """Cache recommendations in Redis"""
    if not redis_cache.connected:
        return
    
    try:
        cache_key = f"recommendations:{user_id}:{cache_key}"
        redis_cache.redis_client.setex(
            cache_key, 
            cache_duration, 
            json.dumps(recommendations, default=str)
        )
        print(f"✅ Cached recommendations for user {user_id}, key: {cache_key}")
    except Exception as e:
        print(f"Redis cache set error: {e}")

def invalidate_user_recommendations(user_id):
    """Invalidate all cached recommendations for a user"""
    if not redis_cache.connected:
        return
    
    try:
        pattern = f"recommendations:{user_id}:*"
        keys = redis_cache.redis_client.keys(pattern)
        if keys:
            redis_cache.redis_client.delete(*keys)
            print(f"🗑️ Invalidated {len(keys)} recommendation caches for user {user_id}")
    except Exception as e:
        print(f"Redis cache invalidation error: {e}")

def calculate_text_similarity(text1, text2):
    """Calculate similarity between two text strings using multiple methods with improved precision"""
    if not text1 or not text2:
        return 0.0
    
    # Method 1: Sequence matcher (good for overall similarity)
    sequence_similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    # Method 2: Word overlap with better word extraction
    words1 = set(re.findall(r'\b\w+\b', text1.lower()))
    words2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    if not words1 or not words2:
        word_overlap = 0.0
    else:
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        word_overlap = len(intersection) / len(union) if union else 0.0
    
    # Method 3: Technology keyword matching (improved precision)
    tech_keywords = {
        'java': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy'],
        'javascript': ['javascript', 'js', 'es6', 'es7', 'node', 'nodejs', 'node.js'],
        'react': ['react', 'reactjs', 'react.js', 'react native', 'rn'],
        'python': ['python', 'django', 'flask', 'fastapi'],
        'mobile': ['mobile', 'ios', 'android', 'app'],
        'web': ['web', 'html', 'css', 'frontend', 'backend'],
        'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql'],
        'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch'],
        'dsa': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching'],
        'instrumentation': ['instrumentation', 'byte buddy', 'asm', 'bytecode']
    }
    
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    tech_matches = 0
    total_techs_found = 0
    
    for tech_category, keywords in tech_keywords.items():
        # Check if this technology appears in both texts
        tech_in_text1 = any(re.search(r'\b' + re.escape(kw) + r'\b', text1_lower) for kw in keywords)
        tech_in_text2 = any(re.search(r'\b' + re.escape(kw) + r'\b', text2_lower) for kw in keywords)
        
        if tech_in_text1 or tech_in_text2:
            total_techs_found += 1
            if tech_in_text1 and tech_in_text2:
                tech_matches += 1
    
    # Calculate technology similarity
    tech_score = tech_matches / max(1, total_techs_found) if total_techs_found > 0 else 0.0
    
    # Combine all methods (weighted average)
    final_similarity = (sequence_similarity * 0.3 + word_overlap * 0.3 + tech_score * 0.4)
    
    return final_similarity

def extract_technologies_from_text(text):
    """Extract technology keywords from text with improved precision"""
    if not text:
        return []
    
    tech_keywords = {
        'java': ['java', 'jvm', 'spring', 'maven', 'gradle', 'bytecode', 'asm', 'byte buddy'],
        'javascript': ['javascript', 'js', 'es6', 'es7', 'node', 'nodejs', 'node.js', 'react', 'reactjs', 'react.js', 'vue', 'vuejs', 'angular'],
        'python': ['python', 'django', 'flask', 'fastapi', 'pandas', 'numpy', 'scipy'],
        'react': ['react', 'reactjs', 'react.js', 'react native', 'rn', 'jsx'],
        'react_native': ['react native', 'rn', 'expo', 'metro'],
        'mobile': ['mobile', 'ios', 'android', 'app', 'application', 'native', 'hybrid'],
        'web': ['web', 'html', 'css', 'frontend', 'backend', 'api', 'rest', 'graphql'],
        'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis'],
        'ai_ml': ['ai', 'machine learning', 'ml', 'tensorflow', 'pytorch', 'neural', 'model'],
        'devops': ['devops', 'docker', 'kubernetes', 'ci/cd', 'deployment', 'aws', 'cloud'],
        'blockchain': ['blockchain', 'crypto', 'ethereum', 'bitcoin', 'smart contract', 'web3'],
        'payment': ['payment', 'stripe', 'paypal', 'upi', 'gateway', 'transaction'],
        'authentication': ['auth', 'authentication', 'oauth', 'jwt', 'login', 'signup'],
        'instrumentation': ['instrumentation', 'byte buddy', 'asm', 'bytecode', 'jvm'],
        'dsa': ['data structure', 'algorithm', 'dsa', 'sorting', 'searching', 'tree', 'graph']
    }
    
    text_lower = text.lower()
    found_techs = []
    
    # First pass: look for exact matches (longer keywords first)
    for tech_category, keywords in tech_keywords.items():
        # Sort keywords by length (longest first) to avoid partial matches
        sorted_keywords = sorted(keywords, key=len, reverse=True)
        
        for keyword in sorted_keywords:
            # Use word boundaries to avoid partial matches
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                found_techs.append(tech_category)
                break  # Only add each category once
    
    return list(set(found_techs))

@recommendations_bp.route('/simple-project/<int:project_id>', methods=['GET'])
@jwt_required()
def simple_project_recommendations(project_id):
    """
    Simple text-based recommendations using bookmark title + extracted_text 
    compared with project title + description + technologies
    """
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    user_id = project.user_id
    
    # Get all user's bookmarks (no quality score filter for now)
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get project-specific recommendations.",
            "recommendations": []
        }), 200
    
    # Prepare project text for comparison
    project_text = f"{project.title} {project.description or ''} {project.technologies or ''}"
    project_technologies = extract_technologies_from_text(project_text)
    
    # Calculate similarity scores for each bookmark
    scored_bookmarks = []
    
    for bookmark in bookmarks:
        # Prepare bookmark text for comparison
        bookmark_text = f"{bookmark.title} {bookmark.extracted_text or ''}"
        
        # Calculate text similarity
        text_similarity = calculate_text_similarity(bookmark_text, project_text)
        
        # Extract technologies from bookmark
        bookmark_technologies = extract_technologies_from_text(bookmark_text)
        
        # Calculate technology overlap
        tech_overlap = 0
        if project_technologies and bookmark_technologies:
            overlap = set(project_technologies).intersection(set(bookmark_technologies))
            tech_overlap = len(overlap) / len(project_technologies) if project_technologies else 0
        
        # Calculate final score (text similarity + tech bonus)
        final_score = text_similarity + (tech_overlap * 0.3)  # Tech overlap gives bonus
        
        # Generate reason
        reasons = []
        if text_similarity > 0.3:
            reasons.append("High text similarity")
        if tech_overlap > 0:
            reasons.append(f"Matches {len(set(project_technologies).intersection(set(bookmark_technologies)))} technologies")
        if bookmark_technologies:
            reasons.append(f"Contains: {', '.join(bookmark_technologies[:3])}")
        
        reason = " | ".join(reasons) if reasons else "Some relevance to your project"
        
        scored_bookmarks.append({
            "id": bookmark.id,
            "title": bookmark.title,
            "url": bookmark.url,
            "notes": bookmark.notes or '',
            "category": bookmark.category or '',
            "score": round(final_score * 100, 1),  # Convert to percentage
            "reason": reason,
            "analysis": {
                "text_similarity": round(text_similarity * 100, 1),
                "tech_overlap": round(tech_overlap * 100, 1),
                "bookmark_technologies": bookmark_technologies,
                "project_technologies": project_technologies
            }
        })
    
    # Sort by score (descending) and filter relevant ones
    scored_bookmarks.sort(key=lambda x: x['score'], reverse=True)
    
    # Filter recommendations with minimum relevance (20% similarity)
    relevant_recommendations = [b for b in scored_bookmarks if b['score'] >= 20]
    
    # Return top 10 recommendations
    top_recommendations = relevant_recommendations[:10]
    
    if not top_recommendations:
        return jsonify({
            "message": f"No relevant recommendations found for project '{project.title}'. Try adding bookmarks related to: {', '.join(project_technologies) if project_technologies else 'your project technologies'}",
            "recommendations": [],
            "project_analysis": {
                "title": project.title,
                "technologies": project_technologies
            }
        }), 200
    
    return jsonify({
        "recommendations": top_recommendations,
        "project_analysis": {
            "title": project.title,
            "technologies": project_technologies,
            "total_bookmarks_analyzed": len(bookmarks),
            "relevant_bookmarks_found": len(relevant_recommendations)
        }
    }), 200

@recommendations_bp.route('/simple-general', methods=['GET'])
@jwt_required()
def simple_general_recommendations():
    """
    Simple text-based general recommendations using bookmark similarity
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Get all user's bookmarks
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    if not bookmarks:
        return jsonify({"recommendations": [], "message": "No bookmarks found. Add some bookmarks to get personalized recommendations."}), 200

    # Get user's technology interests
    user_interests = user.technology_interests or ""
    
    # Calculate similarity scores for each bookmark
    scored_bookmarks = []
    
    for bookmark in bookmarks:
        # Prepare bookmark text
        bookmark_text = f"{bookmark.title} {bookmark.extracted_text or ''}"
        
        # Extract technologies from bookmark
        bookmark_technologies = extract_technologies_from_text(bookmark_text)
        
        # Calculate similarity with user interests
        interest_similarity = calculate_text_similarity(bookmark_text, user_interests)
        
        # Calculate similarity with other bookmarks (diversity)
        diversity_score = 0
        for other_bookmark in bookmarks:
            if other_bookmark.id != bookmark.id:
                other_text = f"{other_bookmark.title} {other_bookmark.extracted_text or ''}"
                similarity = calculate_text_similarity(bookmark_text, other_text)
                diversity_score += similarity
        
        # Normalize diversity score
        if len(bookmarks) > 1:
            diversity_score = diversity_score / (len(bookmarks) - 1)
        
        # Calculate final score (interest similarity + diversity bonus)
        final_score = interest_similarity + (diversity_score * 0.2)
        
        # Generate reason
        reasons = []
        if interest_similarity > 0.2:
            reasons.append("Matches your interests")
        if bookmark_technologies:
            reasons.append(f"Contains: {', '.join(bookmark_technologies[:3])}")
        if diversity_score < 0.3:
            reasons.append("Unique content")
        
        reason = " | ".join(reasons) if reasons else "Recommended based on your bookmarks"
        
        scored_bookmarks.append({
            "id": bookmark.id,
            "title": bookmark.title,
            "url": bookmark.url,
            "notes": bookmark.notes or '',
            "category": bookmark.category or '',
            "score": round(final_score * 100, 1),
            "reason": reason,
            "analysis": {
                "interest_similarity": round(interest_similarity * 100, 1),
                "diversity_score": round(diversity_score * 100, 1),
                "technologies": bookmark_technologies
            }
        })
    
    # Sort by score and filter relevant ones
    scored_bookmarks.sort(key=lambda x: x['score'], reverse=True)
    relevant_recommendations = [b for b in scored_bookmarks if b['score'] >= 15]
    
    # Return top 10 recommendations
    top_recommendations = relevant_recommendations[:10]
    
    if not top_recommendations:
        return jsonify({
            "recommendations": [],
            "message": "No relevant recommendations found. Try adding more diverse bookmarks."
        }), 200
    
    return jsonify({
        "recommendations": top_recommendations,
        "analysis": {
            "total_bookmarks": len(bookmarks),
            "relevant_bookmarks": len(relevant_recommendations),
            "user_interests": user_interests
        }
    }), 200

@recommendations_bp.route('/general', methods=['GET'])
@jwt_required()
def general_recommendations():
    """Get robust recommendations using semantic embeddings and feedback."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    # Check Redis cache first
    cache_key = "general_recommendations"
    cached_result = get_cached_recommendations(user_id, cache_key, cache_duration=1800)  # 30 minutes
    if cached_result:
        print(f"🚀 Using cached general recommendations for user {user_id}")
        return jsonify(cached_result), 200

    print(f"🔄 Computing fresh general recommendations for user {user_id}")

    # Get all user's bookmarks with embeddings and high quality
    bookmarks = SavedContent.query.filter_by(user_id=user_id).filter(SavedContent.quality_score >= 5).all()
    if not bookmarks:
        return jsonify({"recommendations": [], "message": "No bookmarks found. Add some bookmarks to get personalized recommendations."}), 200

    # Build user profile vector (average of all their bookmark embeddings)
    user_embs = [np.array(sc.embedding) for sc in bookmarks if sc.embedding is not None]
    if not user_embs:
        return jsonify({"recommendations": [], "message": "No bookmarks with embeddings found. Add some bookmarks to get personalized recommendations."}), 200
    
    user_profile = np.mean(user_embs, axis=0)

    # Get all content except user's own bookmarks
    all_content = SavedContent.query.filter(SavedContent.user_id != user_id, SavedContent.quality_score >= 5).all()
    if not all_content:
        return jsonify({"recommendations": [], "message": "No other content available for recommendations."}), 200

    # Compute similarity to user profile
    content_embs = [np.array(c.embedding) for c in all_content if c.embedding is not None]
    content_ids = [c.id for c in all_content if c.embedding is not None]
    if not content_embs:
        return jsonify({"recommendations": [], "message": "No content with embeddings available for recommendations."}), 200
    
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
        return jsonify({"recommendations": [], "message": "No relevant recommendations found. Try adding more diverse bookmarks."}), 200

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

    result = {"recommendations": recommendations}
    
    # Cache the result
    cache_recommendations(user_id, cache_key, result, cache_duration=1800)
    
    return jsonify(result), 200

@recommendations_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def recommend_for_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""
    
    # Check Redis cache first
    cache_key = f"project_recommendations_{project_id}"
    cached_result = get_cached_recommendations(user_id, cache_key, cache_duration=1800)  # 30 minutes
    if cached_result:
        print(f"🚀 Using cached project recommendations for user {user_id}, project {project_id}")
        return jsonify(cached_result), 200

    print(f"🔄 Computing fresh project recommendations for user {user_id}, project {project_id}")
    
    # Get all user's bookmarks with embeddings
    bookmarks = SavedContent.query.filter_by(user_id=user_id).filter(SavedContent.quality_score >= 5).all()
    
    # CRITICAL: If user has no bookmarks at all, return empty with clear message
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get project-specific recommendations.",
            "recommendations": []
        }), 200
    
    bookmarks_with_emb = [b for b in bookmarks if b.embedding is not None]
    
    # CRITICAL: If user has bookmarks but none have embeddings, return empty
    if not bookmarks_with_emb:
        return jsonify({
            "message": "No bookmarks with embeddings found. Your bookmarks need to be processed for recommendations.",
            "recommendations": []
        }), 200
    
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
        return jsonify({
            "message": "No relevant recommendations found for this project. Try adding more bookmarks related to your project technologies.",
            "recommendations": []
        }), 200
    
    # Add weekend exploration (optional) - only if we have recommendations
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
    
    result = {"recommendations": recommendations}
    
    # Cache the result
    cache_recommendations(user_id, cache_key, result, cache_duration=1800)
    
    return jsonify(result), 200

@recommendations_bp.route('/task/<int:task_id>', methods=['GET'])
@jwt_required()
def recommend_for_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"message": "Task not found"}), 404
    
    project = Project.query.get(task.project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""
    
    # Get all user's bookmarks with embeddings
    bookmarks = SavedContent.query.filter_by(user_id=user_id).filter(SavedContent.quality_score >= 5).all()
    
    # CRITICAL: If user has no bookmarks at all, return empty
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get task-specific recommendations.",
            "recommendations": []
        }), 200
    
    bookmarks_with_emb = [b for b in bookmarks if b.embedding is not None]
    
    # CRITICAL: If user has bookmarks but none have embeddings, return empty
    if not bookmarks_with_emb:
        return jsonify({
            "message": "No bookmarks with embeddings found. Your bookmarks need to be processed for recommendations.",
            "recommendations": []
        }), 200
    
    # Prepare project context for precision analysis
    project_context = {
        'title': project.title,
        'description': project.description or '',
        'technologies': project.technologies or '',
        'user_interests': user_interests
    }
    
    # Extract task context using precision engine
    task_context = precision_engine.extract_task_context(
        task.title,
        task.description or '',
        project_context
    )
    
    # Convert bookmarks to dict format for precision engine
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
    
    # Get precision recommendations using the smart task engine
    precision_recommendations = precision_engine.get_precision_recommendations(
        bookmark_dicts, 
        task_context, 
        max_recommendations=3  # Only top 3 most precise matches
    )
    
    # Format recommendations for frontend
    recommendations = []
    for rec in precision_recommendations:
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
                "task_type_score": rec['score_data']['task_type_score'],
                "requirements_score": rec['score_data']['requirements_score'],
                "semantic_score": rec['score_data']['semantic_score'],
                "technologies": rec['score_data']['bookmark_analysis']['technologies'],
                "content_type": rec['score_data']['bookmark_analysis']['content_type'],
                "complexity": rec['score_data']['bookmark_analysis']['complexity'],
                "requirements": rec['score_data']['bookmark_analysis']['requirements'],
                "task_context": {
                    "technologies": task_context['technologies'],
                    "task_type": task_context['task_type'],
                    "complexity": task_context['complexity'],
                    "requirements": task_context['requirements']
                }
            }
        })
    
    if not recommendations:
        return jsonify({
            "message": f"No high-precision recommendations found for task '{task.title}'. Try adding more bookmarks related to: {', '.join(task_context['technologies'])}",
            "recommendations": [],
            "task_analysis": {
                "technologies": task_context['technologies'],
                "task_type": task_context['task_type'],
                "complexity": task_context['complexity'],
                "requirements": task_context['requirements']
            }
        }), 200
    
    return jsonify({
        "recommendations": recommendations,
        "task_analysis": {
            "technologies": task_context['technologies'],
            "task_type": task_context['task_type'],
            "complexity": task_context['complexity'],
            "requirements": task_context['requirements']
        }
    }), 200

@recommendations_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Submit feedback on recommendations to improve future suggestions."""
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
        
        # Invalidate cached recommendations since feedback affects scoring
        invalidate_user_recommendations(user_id)
        print(f"🗑️ Invalidated recommendations cache for user {user_id} due to feedback")
        
        return jsonify({"message": "Feedback submitted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error submitting feedback"}), 500 

@recommendations_bp.route('/unified', methods=['POST'])
@jwt_required()
def unified_recommendations():
    """
    Unified intelligent recommendations endpoint
    Accepts any type of input (project, task, general) and provides optimal recommendations
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"message": "Request body is required"}), 400
    
    # Extract input data
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    technologies = data.get('technologies', '').strip()
    user_interests = data.get('user_interests', '').strip()
    max_recommendations = data.get('max_recommendations', 10)
    diverse = data.get('diverse', True)
    
    if not title:
        return jsonify({"message": "Title is required"}), 400
    
    # Get user's bookmarks
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get personalized recommendations.",
            "recommendations": [],
            "context_analysis": None
        }), 200
    
    # Extract context from user input
    context = unified_engine.extract_context_from_input(
        title=title,
        description=description,
        technologies=technologies,
        user_interests=user_interests
    )
    
    # Convert bookmarks to dict format
    bookmark_dicts = []
    for bookmark in bookmarks:
        bookmark_dicts.append({
            'id': bookmark.id,
            'title': bookmark.title,
            'url': bookmark.url,
            'notes': bookmark.notes or '',
            'category': bookmark.category or '',
            'extracted_text': bookmark.extracted_text or '',
            'embedding': bookmark.embedding,
            'saved_at': bookmark.saved_at.isoformat() if bookmark.saved_at else None
        })
    
    # Get recommendations
    if diverse:
        recommendations = unified_engine.get_diverse_recommendations(
            bookmark_dicts, context, max_recommendations
        )
    else:
        recommendations = unified_engine.get_recommendations(
            bookmark_dicts, context, max_recommendations
        )
    
    # Format recommendations for frontend
    formatted_recommendations = []
    for rec in recommendations:
        score_data = rec['score_data']
        formatted_recommendations.append({
            "id": rec['id'],
            "title": rec['title'],
            "url": rec['url'],
            "notes": rec['notes'],
            "category": rec['category'],
            "score": round(score_data['total_score'], 1),
            "reason": score_data['reason'],
            "confidence": round(score_data['confidence'] * 100, 1),
            "analysis": {
                "technology_match": round(score_data['scores']['tech_match'], 1),
                "content_relevance": round(score_data['scores']['content_relevance'], 1),
                "difficulty_alignment": round(score_data['scores']['difficulty_alignment'], 1),
                "intent_alignment": round(score_data['scores']['intent_alignment'], 1),
                "semantic_similarity": round(score_data['scores']['semantic_similarity'], 1),
                "bookmark_technologies": [tech['category'] for tech in score_data['bookmark_analysis']['technologies']],
                "content_type": score_data['bookmark_analysis']['content_type'],
                "difficulty": score_data['bookmark_analysis']['difficulty'],
                "intent": score_data['bookmark_analysis']['intent'],
                "key_concepts": score_data['bookmark_analysis']['key_concepts'][:5]
            }
        })
    
    # Prepare context analysis for frontend
    context_analysis = {
        "input_analysis": {
            "title": context['title'],
            "technologies": [tech['category'] for tech in context['technologies']],
            "content_type": context['content_type'],
            "difficulty": context['difficulty'],
            "intent": context['intent'],
            "complexity_score": round(context['complexity_score'] * 100, 1),
            "key_concepts": context['key_concepts'][:10],
            "requirements": context['requirements']
        },
        "processing_stats": {
            "total_bookmarks_analyzed": len(bookmarks),
            "relevant_bookmarks_found": len(recommendations),
            "diverse_recommendations": diverse
        }
    }
    
    if not formatted_recommendations:
        return jsonify({
            "message": f"No relevant recommendations found for '{title}'. Try adding bookmarks related to: {', '.join([tech['category'] for tech in context['technologies']]) if context['technologies'] else 'your interests'}",
            "recommendations": [],
            "context_analysis": context_analysis
        }), 200
    
    return jsonify({
        "recommendations": formatted_recommendations,
        "context_analysis": context_analysis
    }), 200

@recommendations_bp.route('/unified-project/<int:project_id>', methods=['GET'])
@jwt_required()
def unified_project_recommendations(project_id):
    """
    Unified recommendations for a specific project
    """
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""
    
    # Get user's bookmarks
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get project-specific recommendations.",
            "recommendations": [],
            "context_analysis": None
        }), 200
    
    # Extract context from project
    context = unified_engine.extract_context_from_input(
        title=project.title,
        description=project.description or '',
        technologies=project.technologies or '',
        user_interests=user_interests
    )
    
    # Convert bookmarks to dict format
    bookmark_dicts = []
    for bookmark in bookmarks:
        bookmark_dicts.append({
            'id': bookmark.id,
            'title': bookmark.title,
            'url': bookmark.url,
            'notes': bookmark.notes or '',
            'category': bookmark.category or '',
            'extracted_text': bookmark.extracted_text or '',
            'embedding': bookmark.embedding,
            'saved_at': bookmark.saved_at.isoformat() if bookmark.saved_at else None
        })
    
    # Get diverse recommendations
    recommendations = unified_engine.get_diverse_recommendations(
        bookmark_dicts, context, max_recommendations=10
    )
    
    # Format recommendations for frontend
    formatted_recommendations = []
    for rec in recommendations:
        score_data = rec['score_data']
        formatted_recommendations.append({
            "id": rec['id'],
            "title": rec['title'],
            "url": rec['url'],
            "notes": rec['notes'],
            "category": rec['category'],
            "score": round(score_data['total_score'], 1),
            "reason": score_data['reason'],
            "confidence": round(score_data['confidence'] * 100, 1),
            "analysis": {
                "technology_match": round(score_data['scores']['tech_match'], 1),
                "content_relevance": round(score_data['scores']['content_relevance'], 1),
                "difficulty_alignment": round(score_data['scores']['difficulty_alignment'], 1),
                "intent_alignment": round(score_data['scores']['intent_alignment'], 1),
                "semantic_similarity": round(score_data['scores']['semantic_similarity'], 1),
                "bookmark_technologies": [tech['category'] for tech in score_data['bookmark_analysis']['technologies']],
                "content_type": score_data['bookmark_analysis']['content_type'],
                "difficulty": score_data['bookmark_analysis']['difficulty'],
                "intent": score_data['bookmark_analysis']['intent'],
                "key_concepts": score_data['bookmark_analysis']['key_concepts'][:5]
            }
        })
    
    # Prepare context analysis
    context_analysis = {
        "project_analysis": {
            "title": context['title'],
            "technologies": [tech['category'] for tech in context['technologies']],
            "content_type": context['content_type'],
            "difficulty": context['difficulty'],
            "intent": context['intent'],
            "complexity_score": round(context['complexity_score'] * 100, 1),
            "key_concepts": context['key_concepts'][:10],
            "requirements": context['requirements']
        },
        "processing_stats": {
            "total_bookmarks_analyzed": len(bookmarks),
            "relevant_bookmarks_found": len(recommendations)
        }
    }
    
    if not formatted_recommendations:
        return jsonify({
            "message": f"No relevant recommendations found for project '{project.title}'. Try adding bookmarks related to: {', '.join([tech['category'] for tech in context['technologies']]) if context['technologies'] else 'your project technologies'}",
            "recommendations": [],
            "context_analysis": context_analysis
        }), 200
    
    return jsonify({
        "recommendations": formatted_recommendations,
        "context_analysis": context_analysis
    }), 200 

@recommendations_bp.route('/gemini-enhanced', methods=['POST'])
@jwt_required()
def gemini_enhanced_recommendations():
    """
    Gemini AI-enhanced recommendations endpoint
    Provides the most intelligent recommendations using Gemini AI analysis
    """
    if not gemini_available:
        return jsonify({
            "message": "Gemini AI is not available. Please check your GEMINI_API_KEY environment variable.",
            "recommendations": [],
            "context_analysis": None
        }), 503
    
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"message": "Request body is required"}), 400
    
    # Extract input data
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    technologies = data.get('technologies', '').strip()
    user_interests = data.get('user_interests', '').strip()
    max_recommendations = data.get('max_recommendations', 10)
    
    if not title:
        return jsonify({"message": "Title is required"}), 400
    
    # Get user's bookmarks
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get personalized recommendations.",
            "recommendations": [],
            "context_analysis": None
        }), 200
    
    # Convert bookmarks to dict format
    bookmark_dicts = []
    for bookmark in bookmarks:
        bookmark_dicts.append({
            'id': bookmark.id,
            'title': bookmark.title,
            'url': bookmark.url,
            'notes': bookmark.notes or '',
            'category': bookmark.category or '',
            'extracted_text': bookmark.extracted_text or '',
            'embedding': bookmark.embedding,
            'saved_at': bookmark.saved_at.isoformat() if bookmark.saved_at else None
        })
    
    # Get enhanced recommendations
    user_input = {
        'title': title,
        'description': description,
        'technologies': technologies,
        'user_interests': user_interests
    }
    
    result = gemini_enhanced_engine.get_enhanced_recommendations(
        bookmark_dicts, user_input, max_recommendations
    )
    
    if not result.get('recommendations'):
        return jsonify({
            "message": f"No relevant recommendations found for '{title}'. Try adding bookmarks related to your interests.",
            "recommendations": [],
            "context_analysis": result.get('context_analysis', {})
        }), 200
    
    return jsonify(result), 200

@recommendations_bp.route('/gemini-enhanced-project/<int:project_id>', methods=['GET'])
@jwt_required()
def gemini_enhanced_project_recommendations(project_id):
    """
    Gemini AI-enhanced recommendations for a specific project
    """
    if not gemini_available:
        return jsonify({
            "message": "Gemini AI is not available. Please check your GEMINI_API_KEY environment variable.",
            "recommendations": [],
            "context_analysis": None
        }), 503
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    user_id = project.user_id
    user = User.query.get(user_id)
    user_interests = user.technology_interests if user else ""
    
    # Get user's bookmarks
    bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
    
    if not bookmarks:
        return jsonify({
            "message": "No bookmarks found. Add some bookmarks to get project-specific recommendations.",
            "recommendations": [],
            "context_analysis": None
        }), 200
    
    # Convert bookmarks to dict format
    bookmark_dicts = []
    for bookmark in bookmarks:
        bookmark_dicts.append({
            'id': bookmark.id,
            'title': bookmark.title,
            'url': bookmark.url,
            'notes': bookmark.notes or '',
            'category': bookmark.category or '',
            'extracted_text': bookmark.extracted_text or '',
            'embedding': bookmark.embedding,
            'saved_at': bookmark.saved_at.isoformat() if bookmark.saved_at else None
        })
    
    # Get enhanced recommendations
    user_input = {
        'title': project.title,
        'description': project.description or '',
        'technologies': project.technologies or '',
        'user_interests': user_interests
    }
    
    result = gemini_enhanced_engine.get_enhanced_recommendations(
        bookmark_dicts, user_input, max_recommendations=10
    )
    
    if not result.get('recommendations'):
        return jsonify({
            "message": f"No relevant recommendations found for project '{project.title}'. Try adding bookmarks related to your project technologies.",
            "recommendations": [],
            "context_analysis": result.get('context_analysis', {})
        }), 200
    
    return jsonify(result), 200

@recommendations_bp.route('/analyze-bookmark/<int:bookmark_id>', methods=['GET'])
@jwt_required()
def analyze_bookmark_with_gemini(bookmark_id):
    """
    Analyze a specific bookmark with Gemini AI
    """
    if not gemini_available:
        return jsonify({
            "message": "Gemini AI is not available. Please check your GEMINI_API_KEY environment variable."
        }), 503
    
    user_id = get_jwt_identity()
    bookmark = SavedContent.query.filter_by(id=bookmark_id, user_id=user_id).first()
    
    if not bookmark:
        return jsonify({"message": "Bookmark not found"}), 404
    
    try:
        from gemini_utils import GeminiAnalyzer
        analyzer = GeminiAnalyzer()
        
        analysis = analyzer.analyze_bookmark_content(
            title=bookmark.title,
            description=bookmark.notes or '',
            content=bookmark.extracted_text or '',
            url=bookmark.url
        )
        
        return jsonify({
            "bookmark_id": bookmark.id,
            "title": bookmark.title,
            "url": bookmark.url,
            "gemini_analysis": analysis
        }), 200
        
    except Exception as e:
        return jsonify({
            "message": f"Failed to analyze bookmark: {str(e)}"
        }), 500

@recommendations_bp.route('/gemini-status', methods=['GET'])
@jwt_required()
def gemini_status():
    """
    Check Gemini AI availability and status
    """
    return jsonify({
        "gemini_available": gemini_available,
        "status": "ready" if gemini_available else "unavailable",
        "message": "Gemini AI is ready for enhanced recommendations" if gemini_available else "Gemini AI is not available. Check GEMINI_API_KEY environment variable."
    }), 200 



        