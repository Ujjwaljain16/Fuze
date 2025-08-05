#!/usr/bin/env python3
"""
Clean Recommendations Blueprint
Uses standalone engines directly to eliminate duplication while preserving all functionality
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sentence_transformers import SentenceTransformer
import numpy as np

# Import models and utilities
from models import db, SavedContent, ContentAnalysis, User, Project, Task, Feedback
from redis_utils import redis_cache
from gemini_utils import GeminiAnalyzer
from rate_limit_handler import GeminiRateLimiter
from cache_invalidation_service import cache_invalidator

# Import enhanced modules
try:
    from advanced_tech_detection import advanced_tech_detector
    from adaptive_scoring_engine import adaptive_scoring_engine
    ENHANCED_MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced modules not available: {e}")
    ENHANCED_MODULES_AVAILABLE = False

# Import standalone engines
try:
    from unified_recommendation_engine import UnifiedRecommendationEngine
    UNIFIED_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Unified recommendation engine not available: {e}")
    UNIFIED_ENGINE_AVAILABLE = False

try:
    from enhanced_recommendation_engine import get_enhanced_recommendations, unified_engine
    ENHANCED_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced recommendation engine not available: {e}")
    ENHANCED_ENGINE_AVAILABLE = False

try:
    from phase3_enhanced_engine import (
        get_enhanced_recommendations_phase3,
        record_user_feedback_phase3,
        get_user_learning_insights,
        get_system_health_phase3
    )
    PHASE3_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Phase 3 enhanced engine not available: {e}")
    PHASE3_ENGINE_AVAILABLE = False

try:
    from smart_recommendation_engine import SmartRecommendationEngine
    SMART_ENGINE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Smart recommendation engine not available: {e}")
    SMART_ENGINE_AVAILABLE = False

try:
    from fast_gemini_engine import FastGeminiEngine
    FAST_GEMINI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Fast Gemini engine not available: {e}")
    FAST_GEMINI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

# Initialize models
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    gemini_analyzer = GeminiAnalyzer()
    rate_limiter = GeminiRateLimiter()
    logger.info("Models initialized successfully")
except Exception as e:
    logger.error(f"Error initializing models: {e}")
    embedding_model = None
    gemini_analyzer = None
    rate_limiter = None

# Initialize engine instances
unified_engine_instance = None
smart_engine_instance = None
fast_gemini_instance = None

if UNIFIED_ENGINE_AVAILABLE:
    unified_engine_instance = UnifiedRecommendationEngine()
    logger.info("Unified recommendation engine initialized")

if SMART_ENGINE_AVAILABLE:
    smart_engine_instance = SmartRecommendationEngine()
    logger.info("Smart recommendation engine initialized")

if FAST_GEMINI_AVAILABLE:
    fast_gemini_instance = FastGeminiEngine()
    logger.info("Fast Gemini engine initialized")

# Cache management functions
def get_cached_recommendations(cache_key):
    """Get cached recommendations"""
    return redis_cache.get_cache(cache_key)

def cache_recommendations(cache_key, data, ttl=3600):
    """Cache recommendations"""
    return redis_cache.set_cache(cache_key, data, ttl)

def invalidate_user_recommendations(user_id):
    """Invalidate all cached recommendations for a user"""
    try:
        return cache_invalidator.invalidate_recommendation_cache(user_id)
    except Exception as e:
        logger.error(f"Error invalidating user recommendations: {e}")
        return False

# ============================================================================
# API ROUTES - Using Standalone Engines
# ============================================================================

@recommendations_bp.route('/unified', methods=['POST'])
@jwt_required()
def get_unified_recommendations():
    """Get unified recommendations using UnifiedRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not UNIFIED_ENGINE_AVAILABLE:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Extract context from request data
        title = data.get('title', '')
        description = data.get('description', '')
        technologies = data.get('technologies', '')
        user_interests = data.get('user_interests', '')
        max_recommendations = data.get('max_recommendations', 10)
        
        # Get user's saved content
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        
        # Convert to format expected by UnifiedRecommendationEngine
        bookmarks_data = []
        for bookmark in user_bookmarks:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'extracted_text': bookmark.extracted_text or '',
                'tags': bookmark.tags or '',
                'notes': bookmark.notes or '',
                'quality_score': bookmark.quality_score or 7.0,
                'created_at': bookmark.created_at
            })
        
        # Extract context from user input
        context = unified_engine_instance.extract_context_from_input(
            title=user_input.get('title', ''),
            description=user_input.get('description', ''),
            technologies=user_input.get('technologies', ''),
            user_interests=user_input.get('user_interests', '')
        )
        
        # Get recommendations
        recommendations = unified_engine_instance.get_recommendations(
            bookmarks=bookmarks_data,
            context=context,
            max_recommendations=10
        )
        
        result = {
            'recommendations': recommendations,
            'context_used': context,
            'total_candidates': len(bookmarks_data),
            'engine_used': 'UnifiedRecommendationEngine',
            'enhanced_features_available': ENHANCED_MODULES_AVAILABLE
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in general recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project_recommendations(project_id):
    """Get project-specific recommendations using UnifiedRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        
        if not UNIFIED_ENGINE_AVAILABLE:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Get project details
        project = Project.query.filter_by(id=project_id, user_id=user_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get user's saved content
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        
        # Convert to format expected by UnifiedRecommendationEngine
        bookmarks_data = []
        for bookmark in user_bookmarks:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'extracted_text': bookmark.extracted_text or '',
                'tags': bookmark.tags or '',
                'notes': bookmark.notes or '',
                'quality_score': bookmark.quality_score or 7.0,
                'created_at': bookmark.created_at
            })
        
        # Extract context from project
        context = unified_engine_instance.extract_context_from_input(
            title=project.title,
            description=project.description or '',
            technologies=project.technologies or '',
            user_interests=''
        )
        
        # Get recommendations
        recommendations = unified_engine_instance.get_recommendations(
            bookmarks=bookmarks_data,
            context=context,
            max_recommendations=10
        )
        
        result = {
            'recommendations': recommendations,
            'context_used': context,
            'project_id': project_id,
            'project_title': project.title,
            'total_candidates': len(bookmarks_data),
            'engine_used': 'UnifiedRecommendationEngine',
            'enhanced_features_available': ENHANCED_MODULES_AVAILABLE
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/task/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_recommendations(task_id):
    """Get task-specific recommendations using SmartRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        
        if not SMART_ENGINE_AVAILABLE:
            return jsonify({'error': 'Smart recommendation engine not available'}), 500
        
        # Get task details
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # Use smart engine for task recommendations
        result = smart_engine_instance.get_task_recommendations(user_id, task_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in task recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-enhanced', methods=['POST'])
@jwt_required()
def get_gemini_enhanced_recommendations():
    """Get Gemini-enhanced recommendations using FastGeminiEngine"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        if not FAST_GEMINI_AVAILABLE:
            return jsonify({'error': 'Fast Gemini engine not available'}), 500
        
        # Use fast Gemini engine
        result = fast_gemini_instance.get_gemini_enhanced_recommendations(user_id, user_input)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in Gemini-enhanced recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-enhanced-project/<int:project_id>', methods=['POST'])
@jwt_required()
def get_gemini_enhanced_project_recommendations(project_id):
    """Get Gemini-enhanced project recommendations using FastGeminiEngine"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        if not FAST_GEMINI_AVAILABLE:
            return jsonify({'error': 'Fast Gemini engine not available'}), 500
        
        # Use fast Gemini engine for project recommendations
        result = fast_gemini_instance.get_gemini_enhanced_project_recommendations(user_id, project_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in Gemini-enhanced project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-status', methods=['GET'])
@jwt_required()
def get_gemini_status():
    """Get Gemini API status"""
    try:
        if not gemini_analyzer:
            return jsonify({
                'status': 'unavailable',
                'message': 'Gemini analyzer not initialized'
            })
        
        # Test Gemini availability
        try:
            test_response = gemini_analyzer.analyze_text("Test message")
            return jsonify({
                'status': 'available',
                'message': 'Gemini API is working',
                'test_response': test_response[:100] + '...' if len(str(test_response)) > 100 else test_response
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Gemini API error: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"Error checking Gemini status: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/smart-recommendations', methods=['POST'])
@jwt_required()
def get_smart_recommendations():
    """Get smart recommendations using SmartRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        if not SMART_ENGINE_AVAILABLE:
            return jsonify({'error': 'Smart recommendation engine not available'}), 500
        
        # Use smart engine
        result = smart_engine_instance.get_recommendations(user_id, user_input)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in smart recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/enhanced', methods=['POST'])
@jwt_required()
def get_enhanced_recommendations_route():
    """Get enhanced recommendations using enhanced_recommendation_engine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not ENHANCED_ENGINE_AVAILABLE:
            return jsonify({'error': 'Enhanced recommendation engine not available'}), 500
        
        # Use enhanced recommendation engine
        result = get_enhanced_recommendations(user_id, data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in enhanced recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/enhanced-project/<int:project_id>', methods=['POST'])
@jwt_required()
def get_enhanced_project_recommendations_route(project_id):
    """Get enhanced project recommendations using enhanced_recommendation_engine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        data['project_id'] = project_id
        
        if not ENHANCED_ENGINE_AVAILABLE:
            return jsonify({'error': 'Enhanced recommendation engine not available'}), 500
        
        # Use enhanced recommendation engine
        result = get_enhanced_recommendations(user_id, data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in enhanced project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/enhanced-status', methods=['GET'])
@jwt_required()
def get_enhanced_engine_status():
    """Get enhanced engine status"""
    try:
        status = {
            'enhanced_engine_available': ENHANCED_ENGINE_AVAILABLE,
            'phase3_engine_available': PHASE3_ENGINE_AVAILABLE,
            'unified_engine_available': UNIFIED_ENGINE_AVAILABLE,
            'smart_engine_available': SMART_ENGINE_AVAILABLE,
            'fast_gemini_available': FAST_GEMINI_AVAILABLE,
            'enhanced_modules_available': ENHANCED_MODULES_AVAILABLE,
            'gemini_analyzer_available': gemini_analyzer is not None,
            'embedding_model_available': embedding_model is not None
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting enhanced engine status: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase3/recommendations', methods=['POST'])
@jwt_required()
def get_phase3_recommendations():
    """Get Phase 3 recommendations using phase3_enhanced_engine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not PHASE3_ENGINE_AVAILABLE:
            return jsonify({'error': 'Phase 3 enhanced engine not available'}), 500
        
        # Use Phase 3 enhanced engine
        result = get_enhanced_recommendations_phase3(user_id, data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in Phase 3 recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase3/feedback', methods=['POST'])
@jwt_required()
def record_phase3_feedback():
    """Record Phase 3 feedback using phase3_enhanced_engine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        recommendation_id = data.get('recommendation_id')
        feedback_type = data.get('feedback_type')
        feedback_data = data.get('feedback_data', {})
        
        if not recommendation_id or not feedback_type:
            return jsonify({'error': 'Missing recommendation_id or feedback_type'}), 400
        
        if not PHASE3_ENGINE_AVAILABLE:
            return jsonify({'error': 'Phase 3 enhanced engine not available'}), 500
        
        # Use Phase 3 enhanced engine
        record_user_feedback_phase3(user_id, recommendation_id, feedback_type, feedback_data)
        
        return jsonify({'message': 'Feedback recorded successfully'})
        
    except Exception as e:
        logger.error(f"Error recording Phase 3 feedback: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase3/insights', methods=['GET'])
@jwt_required()
def get_phase3_insights():
    """Get Phase 3 insights using phase3_enhanced_engine"""
    try:
        user_id = get_jwt_identity()
        
        if not PHASE3_ENGINE_AVAILABLE:
            return jsonify({'error': 'Phase 3 enhanced engine not available'}), 500
        
        # Use Phase 3 enhanced engine
        result = get_user_learning_insights(user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 insights: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase3/health', methods=['GET'])
@jwt_required()
def get_phase3_health():
    """Get Phase 3 system health using phase3_enhanced_engine"""
    try:
        if not PHASE3_ENGINE_AVAILABLE:
            return jsonify({'error': 'Phase 3 enhanced engine not available'}), 500
        
        # Use Phase 3 enhanced engine
        result = get_system_health_phase3()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 health: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/unified', methods=['POST'])
@jwt_required()
def get_unified_recommendations():
    """Get unified recommendations using UnifiedRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not UNIFIED_ENGINE_AVAILABLE:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Extract context from request data
        title = data.get('title', '')
        description = data.get('description', '')
        technologies = data.get('technologies', '')
        user_interests = data.get('user_interests', '')
        max_recommendations = data.get('max_recommendations', 10)
        
        # Get user's saved content
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        
        # Convert to the format expected by UnifiedRecommendationEngine
        bookmarks_data = []
        for bookmark in user_bookmarks:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'extracted_text': bookmark.extracted_text or '',
                'tags': bookmark.tags or '',
                'notes': bookmark.notes or '',
                'quality_score': bookmark.quality_score or 7.0,
                'created_at': bookmark.created_at
            })
        
        # Extract context using the enhanced context extraction
        context = unified_engine_instance.extract_context_from_input(
            title=title,
            description=description,
            technologies=technologies,
            user_interests=user_interests
        )
        
        # Get recommendations using the unified engine
        recommendations = unified_engine_instance.get_recommendations(
            bookmarks=bookmarks_data,
            context=context,
            max_recommendations=max_recommendations
        )
        
        # Format response
        result = {
            'recommendations': recommendations,
            'context_used': context,
            'total_candidates': len(bookmarks_data),
            'engine_used': 'UnifiedRecommendationEngine',
            'enhanced_features_available': ENHANCED_MODULES_AVAILABLE
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in unified recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/unified-project/<int:project_id>', methods=['POST'])
@jwt_required()
def get_unified_project_recommendations(project_id):
    """Get unified project recommendations using UnifiedRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Get project details
        project = Project.query.filter_by(id=project_id, user_id=user_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if not UNIFIED_ENGINE_AVAILABLE:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Get user's saved content
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        
        # Convert to the format expected by UnifiedRecommendationEngine
        bookmarks_data = []
        for bookmark in user_bookmarks:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'extracted_text': bookmark.extracted_text or '',
                'tags': bookmark.tags or '',
                'notes': bookmark.notes or '',
                'quality_score': bookmark.quality_score or 7.0,
                'created_at': bookmark.created_at
            })
        
        # Extract context using the enhanced context extraction
        context = unified_engine_instance.extract_context_from_input(
            title=project.title,
            description=project.description or '',
            technologies=project.technologies or '',
            user_interests=''
        )
        
        # Get recommendations using the unified engine
        max_recommendations = data.get('max_recommendations', 10)
        recommendations = unified_engine_instance.get_recommendations(
            bookmarks=bookmarks_data,
            context=context,
            max_recommendations=max_recommendations
        )
        
        # Format response
        result = {
            'recommendations': recommendations,
            'context_used': context,
            'project_id': project_id,
            'project_title': project.title,
            'total_candidates': len(bookmarks_data),
            'engine_used': 'UnifiedRecommendationEngine',
            'enhanced_features_available': ENHANCED_MODULES_AVAILABLE
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in unified project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@recommendations_bp.route('/cache/clear', methods=['POST'])
@jwt_required()
def clear_recommendation_cache():
    """Clear recommendation cache"""
    try:
        user_id = get_jwt_identity()
        success = invalidate_user_recommendations(user_id)
        
        if success:
            return jsonify({'message': 'Cache cleared successfully'})
        else:
            return jsonify({'error': 'Failed to clear cache'}), 500
            
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/analysis/stats', methods=['GET'])
@jwt_required()
def get_analysis_stats():
    """Get content analysis statistics"""
    try:
        user_id = get_jwt_identity()
        
        # Get analysis stats
        total_content = SavedContent.query.filter_by(user_id=user_id).count()
        analyzed_content = ContentAnalysis.query.join(SavedContent).filter(
            SavedContent.user_id == user_id
        ).count()
        
        stats = {
            'total_content': total_content,
            'analyzed_content': analyzed_content,
            'analysis_percentage': round((analyzed_content / max(total_content, 1)) * 100, 2)
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting analysis stats: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase-status', methods=['GET'])
def get_phase_status():
    """Get status of all recommendation phases"""
    try:
        status = {
            'phase1_smart_engine': SMART_ENGINE_AVAILABLE,
            'phase2_enhanced_engine': ENHANCED_ENGINE_AVAILABLE,
            'phase3_advanced_engine': PHASE3_ENGINE_AVAILABLE,
            'unified_engine': UNIFIED_ENGINE_AVAILABLE,
            'fast_gemini_engine': FAST_GEMINI_AVAILABLE,
            'enhanced_modules': ENHANCED_MODULES_AVAILABLE,
            'total_engines_available': sum([
                SMART_ENGINE_AVAILABLE,
                ENHANCED_ENGINE_AVAILABLE,
                PHASE3_ENGINE_AVAILABLE,
                UNIFIED_ENGINE_AVAILABLE,
                FAST_GEMINI_AVAILABLE
            ])
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting phase status: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """Get performance metrics for all engines"""
    try:
        metrics = {
            'engines_available': {
                'unified_engine': UNIFIED_ENGINE_AVAILABLE,
                'smart_engine': SMART_ENGINE_AVAILABLE,
                'enhanced_engine': ENHANCED_ENGINE_AVAILABLE,
                'phase3_engine': PHASE3_ENGINE_AVAILABLE,
                'fast_gemini_engine': FAST_GEMINI_AVAILABLE
            },
            'enhanced_features': {
                'context_extraction': ENHANCED_MODULES_AVAILABLE,
                'content_analysis': ENHANCED_MODULES_AVAILABLE,
                'diversity_engine': ENHANCED_MODULES_AVAILABLE,
                'tech_detection': ENHANCED_MODULES_AVAILABLE,
                'adaptive_scoring': ENHANCED_MODULES_AVAILABLE
            },
            'system_components': {
                'gemini_analyzer': gemini_analyzer is not None,
                'embedding_model': embedding_model is not None,
                'redis_cache': redis_cache is not None
            }
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# LEGACY ENDPOINTS (for backward compatibility)
# ============================================================================

@recommendations_bp.route('/learning-path-recommendations', methods=['POST'])
@jwt_required()
def get_learning_path_recommendations():
    """Legacy endpoint - redirects to unified recommendations"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Redirect to unified recommendations
        return get_unified_recommendations()
        
    except Exception as e:
        logger.error(f"Error in learning path recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/project-recommendations', methods=['POST'])
@jwt_required()
def get_project_type_recommendations():
    """Legacy endpoint - redirects to unified project recommendations"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        project_id = data.get('project_id')
        if not project_id:
            return jsonify({'error': 'Project ID required'}), 400
        
        # Redirect to unified project recommendations
        return get_unified_project_recommendations(project_id)
        
    except Exception as e:
        logger.error(f"Error in project type recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase3/contextual', methods=['POST'])
@jwt_required()
def get_contextual_recommendations():
    """Legacy endpoint - redirects to Phase 3 recommendations"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Redirect to Phase 3 recommendations
        return get_phase3_recommendations()
        
    except Exception as e:
        logger.error(f"Error in contextual recommendations: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ANALYSIS ENDPOINTS (if needed)
# ============================================================================

@recommendations_bp.route('/analysis/analyze-content/<int:content_id>', methods=['POST'])
@jwt_required()
def analyze_content_immediately(content_id):
    """Analyze content immediately"""
    try:
        user_id = get_jwt_identity()
        
        # Check if content belongs to user
        content = SavedContent.query.filter_by(id=content_id, user_id=user_id).first()
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Import background analysis service
        try:
            from background_analysis_service import analyze_content
            result = analyze_content(content_id)
            return jsonify({'message': 'Content analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
        
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/analysis/start-background', methods=['POST'])
@jwt_required()
def start_background_analysis():
    """Start background analysis for user's content"""
    try:
        user_id = get_jwt_identity()
        
        # Import background analysis service
        try:
            from background_analysis_service import start_background_analysis_for_user
            result = start_background_analysis_for_user(user_id)
            return jsonify({'message': 'Background analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
        
    except Exception as e:
        logger.error(f"Error starting background analysis: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# INITIALIZATION
# ============================================================================

def init_recommendations_blueprint():
    """Initialize the recommendations blueprint"""
    logger.info("Initializing clean recommendations blueprint...")
    
    # Log engine availability
    logger.info(f"Unified Engine: {'✅ Available' if UNIFIED_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Smart Engine: {'✅ Available' if SMART_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Enhanced Engine: {'✅ Available' if ENHANCED_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Phase 3 Engine: {'✅ Available' if PHASE3_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Fast Gemini Engine: {'✅ Available' if FAST_GEMINI_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Enhanced Modules: {'✅ Available' if ENHANCED_MODULES_AVAILABLE else '❌ Not Available'}")
    
    return recommendations_bp

# Initialize the blueprint
init_recommendations_blueprint() 