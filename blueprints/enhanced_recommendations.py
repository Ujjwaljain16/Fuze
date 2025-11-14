"""
Enhanced Recommendation Endpoints
==================================
API endpoints for:
- User feedback tracking
- Explainability
- Skill gap analysis
- Personalized recommendations
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

logger = logging.getLogger(__name__)

# Create blueprint
enhanced_bp = Blueprint('enhanced_recommendations', __name__, url_prefix='/api/enhanced')

# ============================================================================
# FEEDBACK TRACKING ENDPOINTS
# ============================================================================

@enhanced_bp.route('/feedback', methods=['POST'])
@jwt_required()
def track_feedback():
    """
    Track user feedback on a recommendation
    
    Body:
        {
            "content_id": 123,
            "feedback_type": "clicked",  # or "saved", "dismissed", "not_relevant", "helpful", "completed"
            "recommendation_id": 456,  # Optional
            "context": {              # Optional
                "query": "learn python",
                "project_id": 789
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'content_id' not in data or 'feedback_type' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Record feedback
        from user_feedback_system import get_feedback_learner
        learner = get_feedback_learner()
        
        success = learner.record_feedback(
            user_id=user_id,
            content_id=data['content_id'],
            recommendation_id=data.get('recommendation_id'),
            feedback_type=data['feedback_type'],
            context=data.get('context')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Feedback recorded successfully'
            })
        else:
            return jsonify({'error': 'Failed to record feedback'}), 500
            
    except Exception as e:
        logger.error(f"Error tracking feedback: {e}")
        return jsonify({'error': str(e)}), 500


@enhanced_bp.route('/user-preferences', methods=['GET'])
@jwt_required()
def get_user_preferences():
    """Get user's learned preferences"""
    try:
        user_id = get_jwt_identity()
        
        from user_feedback_system import get_feedback_learner
        learner = get_feedback_learner()
        
        preferences = learner.get_user_preferences(user_id)
        
        return jsonify({
            'user_id': user_id,
            'preferences': preferences
        })
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return jsonify({'error': str(e)}), 500


@enhanced_bp.route('/user-insights', methods=['GET'])
@jwt_required()
def get_user_insights():
    """Get insights about user's learning patterns"""
    try:
        user_id = get_jwt_identity()
        
        from user_feedback_system import get_feedback_learner
        learner = get_feedback_learner()
        
        insights = learner.get_user_insights(user_id)
        
        return jsonify({
            'user_id': user_id,
            'insights': insights
        })
        
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SKILL GAP ANALYSIS ENDPOINTS
# ============================================================================

@enhanced_bp.route('/skill-analysis', methods=['GET'])
@jwt_required()
def analyze_skills():
    """Analyze user's current skills"""
    try:
        user_id = get_jwt_identity()
        
        from skill_gap_analyzer import get_skill_analyzer
        analyzer = get_skill_analyzer()
        
        skills = analyzer.analyze_user_skills(user_id)
        
        return jsonify({
            'user_id': user_id,
            'skills': skills
        })
        
    except Exception as e:
        logger.error(f"Error analyzing skills: {e}")
        return jsonify({'error': str(e)}), 500


@enhanced_bp.route('/skill-gaps', methods=['POST'])
@jwt_required()
def identify_skill_gaps():
    """
    Identify skill gaps and get learning path
    
    Body:
        {
            "target_goal": "Build a full-stack app",  # Optional
            "target_technologies": ["react", "node", "postgresql"]  # Optional
        }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        from skill_gap_analyzer import get_skill_analyzer
        analyzer = get_skill_analyzer()
        
        gaps = analyzer.identify_skill_gaps(
            user_id=user_id,
            target_goal=data.get('target_goal'),
            target_technologies=data.get('target_technologies')
        )
        
        return jsonify({
            'user_id': user_id,
            'gaps': gaps,
            'target_goal': data.get('target_goal'),
            'target_technologies': data.get('target_technologies')
        })
        
    except Exception as e:
        logger.error(f"Error identifying skill gaps: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PERSONALIZED RECOMMENDATIONS
# ============================================================================

@enhanced_bp.route('/personalized-recommendations', methods=['POST'])
@jwt_required()
def get_personalized_recommendations():
    """
    Get personalized recommendations using ALL enhancements:
    - User feedback learning
    - Explainability
    - Skill gap analysis
    
    Body:
        {
            "title": "Learn React",
            "technologies": "react, javascript",
            "max_recommendations": 10,
            "include_explanations": true,
            "include_skill_gaps": true
        }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get base recommendations from orchestrator
        from unified_recommendation_orchestrator import (
            UnifiedRecommendationRequest, 
            get_unified_orchestrator
        )
        from dataclasses import asdict
        
        request_obj = UnifiedRecommendationRequest(
            user_id=user_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            technologies=data.get('technologies', ''),
            user_interests=data.get('user_interests', ''),
            project_id=data.get('project_id'),
            max_recommendations=data.get('max_recommendations', 10),
            engine_preference=data.get('engine_preference', 'context')
        )
        
        orchestrator = get_unified_orchestrator()
        recommendations = orchestrator.get_recommendations(request_obj)
        
        # Convert to dicts
        rec_dicts = [asdict(rec) for rec in recommendations]
        
        # Apply personalization from feedback learning
        from user_feedback_system import get_feedback_learner
        learner = get_feedback_learner()
        user_preferences = learner.get_user_preferences(user_id)
        
        if user_preferences['interaction_count'] >= 5:
            rec_dicts = learner.apply_personalization(rec_dicts, user_preferences)
            personalized = True
        else:
            personalized = False
        
        # Apply skill gap boosting
        skill_gap_boosted = False
        if data.get('include_skill_gaps', True):
            from skill_gap_analyzer import get_skill_analyzer
            analyzer = get_skill_analyzer()
            
            # Get skill gaps
            gaps = analyzer.identify_skill_gaps(
                user_id=user_id,
                target_technologies=data.get('technologies', '').split(',')
            )
            
            # Boost recommendations
            rec_dicts = analyzer.boost_recommendations_by_gaps(rec_dicts, gaps)
            skill_gap_boosted = True
        else:
            gaps = None
        
        # Add explanations
        explanations = []
        if data.get('include_explanations', True):
            from explainability_engine import get_explainer
            explainer = get_explainer()
            
            query_context = {
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'technologies': data.get('technologies', '')
            }
            
            for rec in rec_dicts:
                explanation = explainer.explain_recommendation(rec, query_context)
                explanations.append(explanation)
        
        # Build response
        response = {
            'recommendations': rec_dicts,
            'total_recommendations': len(rec_dicts),
            'enhancements_applied': {
                'personalized': personalized,
                'skill_gap_analysis': skill_gap_boosted,
                'explanations': len(explanations) > 0
            },
            'user_preferences': user_preferences if personalized else None,
            'skill_gaps': gaps if skill_gap_boosted else None,
            'explanations': explanations if explanations else None,
            'engine_used': 'Enhanced_Unified_Orchestrator_v3'
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@enhanced_bp.route('/explain-recommendation/<int:content_id>', methods=['POST'])
@jwt_required()
def explain_single_recommendation(content_id):
    """
    Get detailed explanation for why content was recommended
    
    Body:
        {
            "query_context": {
                "title": "Learn React",
                "technologies": "react, javascript"
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Get content details
        from models import SavedContent, ContentAnalysis, db
        
        content = db.session.query(SavedContent).get(content_id)
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        analysis = db.session.query(ContentAnalysis).filter_by(
            content_id=content_id
        ).first()
        
        # Build recommendation dict
        technologies = []
        if analysis and analysis.technology_tags:
            technologies = [t.strip() for t in analysis.technology_tags.split(',')]
        
        recommendation = {
            'id': content.id,
            'title': content.title,
            'url': content.url,
            'content_type': analysis.content_type if analysis else 'article',
            'difficulty': analysis.difficulty_level if analysis else 'intermediate',
            'technologies': technologies,
            'quality_score': content.quality_score or 6,
            'score': 0.75  # Placeholder
        }
        
        # Generate explanation
        from explainability_engine import get_explainer
        explainer = get_explainer()
        
        query_context = data.get('query_context', {})
        explanation = explainer.explain_recommendation(recommendation, query_context)
        
        return jsonify({
            'content_id': content_id,
            'explanation': explanation
        })
        
    except Exception as e:
        logger.error(f"Error explaining recommendation: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STATISTICS & METRICS
# ============================================================================

@enhanced_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """Get comprehensive user statistics"""
    try:
        user_id = get_jwt_identity()
        
        from user_feedback_system import get_feedback_learner
        from skill_gap_analyzer import get_skill_analyzer
        
        learner = get_feedback_learner()
        analyzer = get_skill_analyzer()
        
        # Get all stats
        insights = learner.get_user_insights(user_id)
        skills = analyzer.analyze_user_skills(user_id)
        
        stats = {
            'user_id': user_id,
            'learning_insights': insights,
            'skill_analysis': skills,
            'generated_at': str(datetime.utcnow())
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': str(e)}), 500


# Helper for datetime
from datetime import datetime


