#!/usr/bin/env python3
"""
Complete Recommendations Blueprint
Combines all features from both versions with proper circular import handling
"""

import os
import hashlib
import time
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from middleware.rate_limiting import limiter
from dataclasses import asdict
from core.logging_config import get_logger

logger = get_logger(__name__)

# Create blueprint FIRST to avoid circular imports
recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

# Import models for new endpoints
try:
    from models import db, SavedContent, Project, Task, User, UserFeedback
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("Models not available for context endpoints")

# Initialize global flags for engine availability
UNIFIED_ORCHESTRATOR_AVAILABLE = False

def get_embedding_model():
    """Check if embedding model is available without loading it"""
    try:
        from utils.embedding_utils import is_embedding_available
        return is_embedding_available()
    except Exception as e:
        logger.error(f"Error checking embedding model: {e}")
        return False

def init_models():
    """Initialize models with error handling - LAZY: only loads when needed"""
    # Model is now lazy-loaded via embedding_utils
    # This function is kept for compatibility but does nothing at startup
    logger.info("Embedding model will be loaded lazily when needed")
    return True

def init_engines():
    """Initialize recommendation engines with lazy loading"""
    global UNIFIED_ORCHESTRATOR_AVAILABLE
    
    # Import unified orchestrator (PRODUCTION-OPTIMIZED ENGINE)
    try:
        from ml.unified_recommendation_orchestrator import get_unified_orchestrator
        UNIFIED_ORCHESTRATOR_AVAILABLE = True
        logger.info("Unified Recommendation Orchestrator initialized (PRODUCTION-OPTIMIZED)")
    except ImportError as e:
        logger.error(f"Unified orchestrator not available: {e}")
        UNIFIED_ORCHESTRATOR_AVAILABLE = False




def invalidate_user_recommendations(user_id):
    """Invalidate all cached recommendations for a user"""
    try:
        from services.cache_invalidation_service import cache_invalidator
        return cache_invalidator.invalidate_recommendation_cache(user_id)
    except Exception as e:
        logger.error(f"Error invalidating user recommendations: {e}")
        return False

# ============================================================================
# API ROUTES - Using Unified Orchestrator
# ============================================================================



@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
@jwt_required()
@limiter.limit("15 per minute")
def get_unified_orchestrator_recommendations():
    """Get recommendations using PRODUCTION-OPTIMIZED Unified Orchestrator (Primary endpoint)"""
    # NOTE: Rate limiting is configured at the app level via Flask-Limiter.
    # Inline decorator application inside route handlers is unsupported and ineffective.
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Input validation
        title = data.get('title', '')
        description = data.get('description', '')
        technologies = data.get('technologies', '')
        
        if title and len(title) > 500:
            return jsonify({'error': 'Title exceeds maximum length of 500 characters'}), 400
        if description and len(description) > 5000:
            return jsonify({'error': 'Description exceeds maximum length of 5000 characters'}), 400
        if technologies and len(technologies) > 1000:
            return jsonify({'error': 'Technologies exceeds maximum length of 1000 characters'}), 400
        
        if not UNIFIED_ORCHESTRATOR_AVAILABLE:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        # Use production-optimized unified orchestrator
        from ml.unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
        from dataclasses import asdict
        import json
        
        # NOTE: Project-level recommendations do NOT include subtasks
        # Only use the provided description - subtasks are only included in task/subtask-specific endpoints
        description = data.get('description', '')
        project_id = data.get('project_id')
        
        # Create request
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=data.get('title', ''),
            description=description,
            technologies=data.get('technologies', ''),
            user_interests=data.get('user_interests', ''),
            project_id=project_id,
            max_recommendations=data.get('max_recommendations', 10),
            engine_preference=data.get('engine_preference', 'context'),
            quality_threshold=data.get('quality_threshold', 3),
            include_global_content=data.get('include_global_content', True)
        )
        
        # Get orchestrator and recommendations (ML enhancement is AUTOMATIC!)
        orchestrator = get_unified_orchestrator()
        recommendations = orchestrator.get_recommendations(unified_request)

        # NOTE: Context summaries are generated on-demand via /generate-context endpoint
        # This allows recommendations to be shown instantly without waiting for Gemini analysis
        # Users can click "Generate Personalized Context" to get AI-powered explanations later

        # Convert to dictionary format
        result = [asdict(rec) for rec in recommendations]
        
        # Get performance metrics
        performance_metrics = orchestrator.get_performance_metrics()
        
        response = {
            'recommendations': result,
            'total_recommendations': len(result),
            'engine_used': 'UnifiedOrchestrator_v2_Optimized',
            'performance_metrics': performance_metrics,
            'optimizations': ['batch_embeddings', 'auto_ml_enhancement', 'intent_aware', 'smart_caching'],
            'request_processed': {
                'title': unified_request.title,
                'technologies': unified_request.technologies,
                'engine_preference': unified_request.engine_preference
            }
        }
        
        return jsonify(response)
        
    except Exception:
        logger.exception("unified_orchestrator_recommendations_failed")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/generate-context', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def generate_personalized_context():
    """Generate personalized context summary for a specific recommendation"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        recommendation_id = data.get('recommendation_id')
        recommendation_data = data.get('recommendation')
        context_data = data.get('context')
        
        if not recommendation_data or not context_data:
            return jsonify({'error': 'Missing recommendation or context data'}), 400
        
        # Import required classes
        from ml.unified_recommendation_orchestrator import (
            UnifiedRecommendationRequest, 
            UnifiedRecommendationResult,
            get_unified_orchestrator
        )
        
        # Get orchestrator
        orchestrator = get_unified_orchestrator()
        
        if not orchestrator:
            return jsonify({'error': 'Recommendation engine not available'}), 500
        
        # Get user's API key for Gemini
        from services.multi_user_api_manager import get_user_api_key
        user_api_key = get_user_api_key(user_id)
        
        if not user_api_key:
            return jsonify({'error': 'User API key not found. Please add your Gemini API key in settings.'}), 400
        
        # Initialize Gemini analyzer with user's API key
        from utils.gemini_utils import GeminiAnalyzer
        gemini_analyzer = GeminiAnalyzer(api_key=user_api_key)
        
        # Create UnifiedRecommendationRequest from context data
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=context_data.get('title', ''),
            description=context_data.get('description', ''),
            technologies=context_data.get('technologies', ''),
            user_interests=context_data.get('user_interests', ''),
            project_id=context_data.get('project_id'),
            max_recommendations=10
        )
        
        # Create UnifiedRecommendationResult from recommendation data
        # Note: UnifiedRecommendationResult doesn't have 'description' or 'match_score' fields
        # Use 'basic_summary' for description-like content and 'score' for match_score
        recommendation_result = UnifiedRecommendationResult(
            id=recommendation_data.get('id'),
            title=recommendation_data.get('title', ''),
            url=recommendation_data.get('url', ''),
            score=recommendation_data.get('match_score', recommendation_data.get('score', 0)),
            reason=recommendation_data.get('reason', ''),
            technologies=recommendation_data.get('technologies', []),
            content_type=recommendation_data.get('content_type', 'article'),
            difficulty=recommendation_data.get('difficulty', 'intermediate'),
            key_concepts=recommendation_data.get('key_concepts', []),
            quality_score=recommendation_data.get('quality_score', 6),
            engine_used=recommendation_data.get('engine_used', 'unified'),
            confidence=recommendation_data.get('confidence', 0.5),
            metadata=recommendation_data.get('metadata', {}),
            basic_summary=recommendation_data.get('basic_summary', ''),
            context_summary=''
        )
        
        # Generate context summary
        context_summary = orchestrator._generate_context_summary(
            gemini_analyzer=gemini_analyzer,
            recommendation=recommendation_result,
            request=unified_request,
            rank=1  # Assume it's a top recommendation
        )
        
        return jsonify({
            'success': True,
            'context_summary': context_summary
        })
        
    except Exception:
        logger.exception("generate_personalized_context_failed")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/task/<int:task_id>', methods=['POST'])
@jwt_required()
def get_task_recommendations(task_id):
    """Get task-specific recommendations using UnifiedRecommendationOrchestrator"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Import models
        from models import Task, Subtask, Project, SavedContent
        
        # Get task and verify ownership
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get subtasks for this task
        subtasks = Subtask.query.filter_by(task_id=task_id).all()
        incomplete_subtasks = [st for st in subtasks if not st.completed]
        
        # Build enhanced description with task and subtask information
        task_description = task.description or ''
        try:
            task_details = json.loads(task_description) if isinstance(task_description, str) else task_description
            if isinstance(task_details, dict):
                task_description = task_details.get('description', '')
        except Exception:
            pass  # task.description may be plain text, not JSON

        enhanced_description = f"Task: {task.title}"
        if task_description:
            enhanced_description += f" - {task_description}"
        
        # Add incomplete subtasks to context
        if incomplete_subtasks:
            subtask_titles = [st.title for st in incomplete_subtasks]
            enhanced_description += f" Subtasks to complete: {', '.join(subtask_titles)}"
        
        # Use unified orchestrator
        from ml.unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
        from dataclasses import asdict
        import numpy as np
        from utils.embedding_utils import calculate_cosine_similarity
        
        # Get project technologies for context
        technologies = project.technologies or ''
        
        # Create request
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=task.title,
            description=enhanced_description,
            technologies=technologies,
            user_interests='',
            project_id=project.id,
            max_recommendations=data.get('max_recommendations', 10),
            engine_preference=data.get('engine_preference', 'context'),
            quality_threshold=data.get('quality_threshold', 6),
            include_global_content=data.get('include_global_content', True)
        )
        
        # Get orchestrator and recommendations
        orchestrator = get_unified_orchestrator()
        recommendations = orchestrator.get_recommendations(unified_request)
        
        # Enhance recommendations with subtask embeddings if available
        if incomplete_subtasks and len(recommendations) > 0:
            try:
                from models import SavedContent
                # Get subtask embeddings for re-ranking boost
                subtask_embeddings = [st.embedding for st in incomplete_subtasks if st.embedding is not None]

                if subtask_embeddings:
                    # Batch-load all recommendation content IDs to avoid N+1 DB round-trips
                    rec_content_ids = [
                        (rec.get('id') if isinstance(rec, dict) else getattr(rec, 'id', None))
                        for rec in recommendations
                    ]
                    rec_content_ids = [cid for cid in rec_content_ids if cid is not None]
                    content_map = {}
                    if rec_content_ids:
                        content_rows = SavedContent.query.filter(
                            SavedContent.id.in_(rec_content_ids),
                            SavedContent.embedding.isnot(None)
                        ).with_entities(SavedContent.id, SavedContent.embedding).all()
                        content_map = {row.id: row.embedding for row in content_rows}

                    enhanced_recommendations = []
                    for rec in recommendations:
                        content_id = rec.get('id') if isinstance(rec, dict) else getattr(rec, 'id', None)
                        embedding = content_map.get(content_id)
                        if content_id and embedding is not None:
                            max_similarity = max(
                                calculate_cosine_similarity(np.array(subtask_emb), np.array(embedding))
                                for subtask_emb in subtask_embeddings
                            )
                            if isinstance(rec, dict):
                                original_score = rec.get('match_score', rec.get('score', 0))
                                rec['match_score'] = min(100, original_score + (max_similarity * 0.15 * 100))
                                rec['subtask_embedding_similarity'] = float(max_similarity)
                            else:
                                original_score = getattr(rec, 'match_score', getattr(rec, 'score', 0))
                                rec.match_score = min(100, original_score + (max_similarity * 0.15 * 100))
                                rec.subtask_embedding_similarity = float(max_similarity)
                        enhanced_recommendations.append(rec)

                    if enhanced_recommendations:
                        enhanced_recommendations.sort(
                            key=lambda x: x.get('match_score', 0) if isinstance(x, dict) else getattr(x, 'match_score', 0),
                            reverse=True
                        )
                        recommendations = enhanced_recommendations[:data.get('max_recommendations', 10)]
                        logger.info("task_embedding_enhanced", extra={"count": len(recommendations), "subtask_count": len(subtask_embeddings)})
            except Exception as e:
                logger.warning("task_embedding_enhancement_failed", extra={"error": str(e)})
                # Continue with original recommendations
        
        # Convert to dictionary format
        result = []
        for rec in recommendations:
            if isinstance(rec, dict):
                result.append(rec)
            else:
                result.append(asdict(rec))
        
        return jsonify({
            'recommendations': result,
            'total_recommendations': len(result),
            'task_id': task_id,
            'task_title': task.title,
            'subtasks_count': len(incomplete_subtasks),
            'engine_used': 'UnifiedOrchestrator_TaskSpecific'
        })
        
    except Exception as e:
        logger.error(f"Error in task recommendations: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/subtask/<int:subtask_id>', methods=['POST'])
@jwt_required()
def get_subtask_recommendations(subtask_id):
    """Get subtask-specific recommendations using UnifiedRecommendationOrchestrator"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Import models
        from models import Subtask, Task, Project, SavedContent
        
        # Get subtask and verify ownership
        subtask = Subtask.query.get(subtask_id)
        if not subtask:
            return jsonify({'error': 'Subtask not found'}), 404
        
        task = Task.query.get(subtask.task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Build enhanced description with subtask and parent task information
        task_description = task.description or ''
        try:
            task_details = json.loads(task_description) if isinstance(task_description, str) else task_description
            if isinstance(task_details, dict):
                task_description = task_details.get('description', '')
        except Exception:
            pass  # task.description may be plain text, not JSON
        
        enhanced_description = f"Subtask: {subtask.title}"
        if subtask.description:
            enhanced_description += f" - {subtask.description}"
        enhanced_description += f" (Part of task: {task.title})"
        if task_description:
            enhanced_description += f" Task context: {task_description}"
        
        # Use unified orchestrator
        from ml.unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
        from dataclasses import asdict
        import numpy as np
        from utils.embedding_utils import calculate_cosine_similarity
        
        # Get project technologies for context
        technologies = project.technologies or ''
        
        # Create request
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=subtask.title,
            description=enhanced_description,
            technologies=technologies,
            user_interests='',
            project_id=project.id,
            max_recommendations=data.get('max_recommendations', 10),
            engine_preference=data.get('engine_preference', 'context'),
            quality_threshold=data.get('quality_threshold', 6),
            include_global_content=data.get('include_global_content', True)
        )
        
        # Get orchestrator and recommendations
        orchestrator = get_unified_orchestrator()
        recommendations = orchestrator.get_recommendations(unified_request)
        
        # Enhance recommendations with subtask embedding similarity if available
        if subtask.embedding is not None and len(recommendations) > 0:
            try:
                from models import SavedContent
                # Batch-load all recommendation content IDs to avoid N+1 DB round-trips
                rec_content_ids = [
                    (rec.get('id') if isinstance(rec, dict) else getattr(rec, 'id', None))
                    for rec in recommendations
                ]
                rec_content_ids = [cid for cid in rec_content_ids if cid is not None]
                content_map = {}
                if rec_content_ids:
                    content_rows = SavedContent.query.filter(
                        SavedContent.id.in_(rec_content_ids),
                        SavedContent.embedding.isnot(None)
                    ).with_entities(SavedContent.id, SavedContent.embedding).all()
                    content_map = {row.id: row.embedding for row in content_rows}

                enhanced_recommendations = []
                for rec in recommendations:
                    content_id = rec.get('id') if isinstance(rec, dict) else getattr(rec, 'id', None)
                    embedding = content_map.get(content_id)
                    if content_id and embedding is not None:
                        similarity = calculate_cosine_similarity(
                            np.array(subtask.embedding),
                            np.array(embedding)
                        )
                        if isinstance(rec, dict):
                            original_score = rec.get('match_score', rec.get('score', 0))
                            rec['match_score'] = min(100, original_score + (similarity * 0.2 * 100))
                            rec['subtask_embedding_similarity'] = float(similarity)
                        else:
                            original_score = getattr(rec, 'match_score', getattr(rec, 'score', 0))
                            rec.match_score = min(100, original_score + (similarity * 0.2 * 100))
                            rec.subtask_embedding_similarity = float(similarity)
                    enhanced_recommendations.append(rec)

                if enhanced_recommendations:
                    enhanced_recommendations.sort(
                        key=lambda x: x.get('match_score', 0) if isinstance(x, dict) else getattr(x, 'match_score', 0),
                        reverse=True
                    )
                    recommendations = enhanced_recommendations[:data.get('max_recommendations', 10)]
                    logger.info("subtask_embedding_enhanced", extra={"count": len(recommendations)})
            except Exception as e:
                logger.warning("subtask_embedding_enhancement_failed", extra={"error": str(e)})
                # Continue with original recommendations
        
        # Convert to dictionary format
        result = []
        for rec in recommendations:
            if isinstance(rec, dict):
                result.append(rec)
            else:
                result.append(asdict(rec))
        
        return jsonify({
            'recommendations': result,
            'total_recommendations': len(result),
            'subtask_id': subtask_id,
            'subtask_title': subtask.title,
            'task_id': task.id,
            'task_title': task.title,
            'engine_used': 'UnifiedOrchestrator_SubtaskSpecific'
        })
        
    except Exception as e:
        logger.error(f"Error in subtask recommendations: {e}")
        return jsonify({'error': 'Internal server error'}), 500



# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

# Note: OPTIONS requests are automatically handled by flask-cors
# No manual OPTIONS handlers needed - they can cause conflicts

@recommendations_bp.route('/status', methods=['GET', 'OPTIONS'])
def get_engine_status():
    """Get status of all recommendation engines"""
    # Handle OPTIONS preflight requests
    if request.method == 'OPTIONS':
        return '', 200
    try:
        status = {
            'unified_orchestrator_available': UNIFIED_ORCHESTRATOR_AVAILABLE,
            'embedding_model_available': bool(get_embedding_model()),
            'gemini_api_key_configured': bool(os.environ.get('GEMINI_API_KEY')),
            'total_engines_available': int(UNIFIED_ORCHESTRATOR_AVAILABLE),
            'recommended_engine': 'unified_orchestrator',
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """Get detailed performance metrics for all engines"""
    try:
        metrics = {}
        
        # Get unified orchestrator metrics
        if UNIFIED_ORCHESTRATOR_AVAILABLE:
            try:
                from ml.unified_recommendation_orchestrator import get_unified_orchestrator
                orchestrator = get_unified_orchestrator()
                metrics['unified_orchestrator'] = orchestrator.get_performance_metrics()
            except Exception as e:
                logger.error(f"Error getting orchestrator metrics: {e}")
                metrics['unified_orchestrator'] = {'error': 'Internal server error'}
        

        
        # Get Redis cache stats
        try:
            from utils.redis_utils import redis_cache
            metrics['redis_cache'] = redis_cache.get_cache_stats()
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {e}")
            metrics['redis_cache'] = {'error': 'Internal server error'}
        
        # Get database stats
        try:
            from models import SavedContent, ContentAnalysis
            metrics['database'] = {
                'total_content': SavedContent.query.count(),
                'analyzed_content': ContentAnalysis.query.count(),
                'analysis_coverage': round((ContentAnalysis.query.count() / max(SavedContent.query.count(), 1)) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Error getting database metrics: {e}")
            metrics['database'] = {'error': 'Internal server error'}
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': 'Internal server error'}), 500

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
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/cache/clear-context', methods=['POST'])
@jwt_required()
def clear_context_cache():
    """Clear context-related caches (suggested-contexts, recent-contexts)"""
    try:
        user_id = get_jwt_identity()

        # Clear Redis caches for context data
        try:
            from utils.redis_utils import redis_cache
            cache_keys = [
                f"suggested_contexts:{user_id}",
                f"recent_contexts:{user_id}"
            ]
            cleared_count = 0
            for key in cache_keys:
                try:
                    redis_cache.delete_cache(key)
                    cleared_count += 1
                except Exception:
                    pass  # Continue if individual key fails

            logger.info(f"Cleared {cleared_count}/{len(cache_keys)} context cache keys for user {user_id}")
        except Exception as cache_error:
            logger.warning(f"Failed to clear Redis context caches: {cache_error}")

        return jsonify({
            'message': 'Context cache cleared successfully',
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"Error clearing context cache: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/cache/clear-all-recommendations', methods=['POST'])
@jwt_required()
def clear_all_recommendation_caches():
    """Clear ALL recommendation-related caches (both Redis and context data)"""
    try:
        user_id = get_jwt_identity()

        cleared_items = {
            'redis_recommendations': False,
            'redis_context': False,
            'success': True
        }

        # 1. Clear Redis recommendation caches
        try:
            success = invalidate_user_recommendations(user_id)
            cleared_items['redis_recommendations'] = success
            if success:
                logger.info(f"Cleared Redis recommendation caches for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to clear Redis recommendation caches: {e}")

        # 2. Clear Redis context caches
        try:
            from utils.redis_utils import redis_cache
            context_keys = [
                f"suggested_contexts:{user_id}",
                f"recent_contexts:{user_id}"
            ]
            context_cleared = 0
            for key in context_keys:
                try:
                    redis_cache.delete_cache(key)
                    context_cleared += 1
                except Exception:
                    pass

            cleared_items['redis_context'] = context_cleared >= len(context_keys)
            if context_cleared > 0:
                logger.info(f"Cleared {context_cleared}/{len(context_keys)} Redis context cache keys for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to clear Redis context caches: {e}")

        # Note: Client-side cache is cleared via the global window.clearContextCache() function

        return jsonify({
            'message': 'All recommendation caches cleared',
            'user_id': user_id,
            'cleared': cleared_items,
            'note': 'Client-side cache should be cleared via window.clearContextCache()'
        })

    except Exception as e:
        logger.error(f"Error clearing all recommendation caches: {e}")
        return jsonify({
            'error': 'Internal server error',
            'note': 'Some caches may not have been cleared'
        }), 500

@recommendations_bp.route('/analysis/stats', methods=['GET'])
@jwt_required()
def get_analysis_stats():
    """Get content analysis statistics"""
    user_id = int(get_jwt_identity())
    try:
        from uow.unit_of_work import UnitOfWork
        from services.recommendation_service import RecommendationService

        with UnitOfWork() as uow:
            service = RecommendationService(uow)
            stats = service.get_analysis_stats(user_id)

        return jsonify(stats)

    except Exception:
        logger.exception("get_analysis_stats_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@recommendations_bp.route('/analysis/analyze-content/<int:content_id>', methods=['POST'])
@jwt_required()
def analyze_content_immediately(content_id):
    """Analyze content immediately"""
    try:
        user_id = get_jwt_identity()
        
        # Import models here to avoid circular imports
        from models import SavedContent
        
        # Check if content belongs to user
        content = SavedContent.query.filter_by(id=content_id, user_id=user_id).first()
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Import background analysis service
        try:
            from services.background_analysis_service import analyze_content
            result = analyze_content(content_id, user_id=int(user_id))
            return jsonify({'message': 'Content analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
                        
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/analysis/start-background', methods=['POST'])
@jwt_required()
def start_background_analysis():
    """Start background analysis for user's content"""
    try:
        user_id = get_jwt_identity()
        
        # Import background analysis service
        try:
            from services.background_analysis_service import start_background_analysis_for_user
            result = start_background_analysis_for_user(user_id)
            return jsonify({'message': 'Background analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
        
    except Exception as e:
        logger.error(f"Error starting background analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/analysis/batch-analyze', methods=['POST'])
@jwt_required()
def batch_analyze_content():
    """Batch analyze multiple content items"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        content_ids = data.get('content_ids', [])
        
        if not content_ids:
            return jsonify({'error': 'No content IDs provided'}), 400
        
        # Import models here to avoid circular imports
        from models import SavedContent
        
        # Verify all content belongs to user
        user_content = SavedContent.query.filter(
            SavedContent.id.in_(content_ids),
            SavedContent.user_id == user_id
        ).all()
        
        if len(user_content) != len(content_ids):
            return jsonify({'error': 'Some content not found or not owned by user'}), 400
        
        # Import background analysis service
        try:
            from services.background_analysis_service import batch_analyze_content as batch_analyze
            result = batch_analyze(content_ids, user_id=int(user_id))
            return jsonify({'message': 'Batch analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# FEEDBACK AND LEARNING ENDPOINTS
# ============================================================================

@recommendations_bp.route('/feedback', methods=['POST'])
@jwt_required()
def record_recommendation_feedback():
    """Record feedback for recommendations. Routes through RecommendationService for cache invalidation."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    recommendation_id = data.get('recommendation_id')
    feedback_type = data.get('feedback_type')  # 'positive', 'negative', 'neutral'
    feedback_data = data.get('feedback_data', {})

    if not recommendation_id or not feedback_type:
        return jsonify({'error': 'Missing recommendation_id or feedback_type'}), 400

    # Map incoming types to canonical UserFeedback model types
    FEEDBACK_TYPE_MAP = {
        'positive': 'helpful',
        'negative': 'not_relevant',
        'neutral': 'clicked',
    }
    mapped_feedback_type = FEEDBACK_TYPE_MAP.get(feedback_type, feedback_type)

    try:
        from uow.unit_of_work import UnitOfWork
        from services.recommendation_service import RecommendationService
        from models import SavedContent

        # Resolve content_id from recommendation_id (best-effort; may be the same value)
        content_id = recommendation_id
        try:
            content = SavedContent.query.filter_by(id=recommendation_id).first()
            if content:
                content_id = content.id
            else:
                logger.warning("feedback_content_not_found", extra={"recommendation_id": recommendation_id})
        except Exception:
            logger.warning("feedback_content_lookup_failed", extra={"recommendation_id": recommendation_id})

        with UnitOfWork() as uow:
            service = RecommendationService(uow)
            feedback = service.record_feedback(
                user_id=user_id,
                content_id=content_id,
                feedback_type=mapped_feedback_type,
                recommendation_id=recommendation_id,
                feedback_data=feedback_data,
            )
            uow.flush()  # Obtain feedback.id before commit
            feedback_id = feedback.id


        logger.info("recommendation_feedback_recorded", extra={"user_id": user_id, "recommendation_id": recommendation_id, "feedback_type": mapped_feedback_type})
        return jsonify({'message': 'Feedback recorded successfully', 'feedback_id': feedback_id})

    except Exception:
        logger.exception("record_recommendation_feedback_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/user-preferences', methods=['GET'])
@jwt_required()
def get_user_preferences():
    """Get user preferences and learning patterns"""
    user_id = int(get_jwt_identity())
    try:
        from uow.unit_of_work import UnitOfWork
        from services.recommendation_service import RecommendationService

        with UnitOfWork() as uow:
            service = RecommendationService(uow)
            preferences = service.get_user_preferences(user_id)

        return jsonify(preferences)

    except Exception:
        logger.exception("get_user_preferences_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500

@recommendations_bp.route('/learning-insights', methods=['GET'])
@jwt_required()
def get_learning_insights():
    """Get learning insights for user"""
    user_id = int(get_jwt_identity())
    try:
        from uow.unit_of_work import UnitOfWork
        from services.recommendation_service import RecommendationService

        with UnitOfWork() as uow:
            service = RecommendationService(uow)
            insights = service.get_learning_insights(user_id)

        return jsonify(insights)

    except Exception:
        logger.exception("get_learning_insights_failed", extra={"user_id": user_id})
        return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# GEMINI-ENHANCED ENDPOINTS
# ============================================================================

@recommendations_bp.route('/gemini-status', methods=['GET'])
@jwt_required()
def get_gemini_status():
    """Check if Gemini is available and working"""
    try:
        api_key_set = bool(os.environ.get('GEMINI_API_KEY'))
        status_info = {
            'gemini_available': api_key_set,
            'status': 'available' if api_key_set else 'unavailable',
            'details': {
                'api_key_set': api_key_set,
                'test_result': None,
                'error_message': None
            }
        }
        
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Error checking Gemini status: {e}")
        return jsonify({
            'gemini_available': False,
            'status': 'error',
            'details': {
                'error_message': 'Internal server error'
            }
        }), 500

# ============================================================================
# CONTEXT SELECTOR ENDPOINTS
# ============================================================================

@recommendations_bp.route('/suggested-contexts', methods=['GET', 'OPTIONS'])
def get_suggested_contexts():
    """Get smart suggestions based on user activity"""
    # Handle OPTIONS preflight requests - no JWT needed
    if request.method == 'OPTIONS':
        return '', 200

    # For actual requests, require JWT
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())

        if not MODELS_AVAILABLE:
            return jsonify({'success': False, 'error': 'Models not available'}), 500

        # Check Redis cache first (5 minute TTL for context data)
        cache_key = f"suggested_contexts:{user_id}"
        try:
            from utils.redis_utils import redis_cache
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result:
                return jsonify(cached_result)
        except Exception:
            pass  # Continue without cache if Redis fails

        contexts = []
        
        # Get user's most recent activity
        try:
            recent_feedback = UserFeedback.query.filter_by(user_id=user_id)\
                .order_by(UserFeedback.timestamp.desc())\
                .limit(3).all()
            
            for feedback in recent_feedback:
                if feedback.context_data:
                    try:
                        context_info = json.loads(feedback.context_data) if isinstance(feedback.context_data, str) else feedback.context_data
                        project_id = context_info.get('project_id')
                        
                        if project_id:
                            project = Project.query.get(project_id)
                            if project:
                                time_ago = _get_time_ago(feedback.timestamp)
                                contexts.append({
                                    'type': 'project',
                                    'id': project.id,
                                    'title': project.title,
                                    'subtitle': f'From: {project.title}',
                                    'description': project.description or '',
                                    'technologies': project.technologies or '',
                                    'timeAgo': time_ago
                                })
                    except Exception:
                        continue
        except Exception:
            pass
        
        # If no feedback, get most recent project
        if not contexts:
            recent_project = Project.query.filter_by(user_id=user_id)\
                .order_by(Project.created_at.desc())\
                .first()
            
            if recent_project:
                contexts.append({
                    'type': 'project',
                    'id': recent_project.id,
                    'title': recent_project.title,
                    'subtitle': 'Last updated project',
                    'description': recent_project.description or '',
                    'technologies': recent_project.technologies or '',
                    'timeAgo': _get_time_ago(recent_project.created_at)
                })
        
        # Remove duplicates
        seen = set()
        unique_contexts = []
        for ctx in contexts:
            key = f"{ctx['type']}_{ctx['id']}"
            if key not in seen:
                seen.add(key)
                unique_contexts.append(ctx)

        result = {
            'success': True,
            'contexts': unique_contexts[:2]
        }

        # Cache the result for 5 minutes
        try:
            from utils.redis_utils import redis_cache
            redis_cache.set_cache(cache_key, result, ttl=300)  # 5 minutes
        except Exception:
            pass  # Continue without caching if Redis fails

        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting suggested contexts: {e}")
        return jsonify({'success': False, 'error': 'Internal server error', 'contexts': []}), 500

@recommendations_bp.route('/recent-contexts', methods=['GET', 'OPTIONS'])
def get_recent_contexts():
    """Get recent projects and tasks"""
    # Handle OPTIONS preflight requests - no JWT needed
    if request.method == 'OPTIONS':
        return '', 200

    # For actual requests, require JWT
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())

        if not MODELS_AVAILABLE:
            return jsonify({'success': False, 'error': 'Models not available'}), 500

        # Check Redis cache first (5 minute TTL for context data)
        cache_key = f"recent_contexts:{user_id}"
        try:
            from utils.redis_utils import redis_cache
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result:
                return jsonify(cached_result)
        except Exception:
            pass  # Continue without cache if Redis fails

        recent_items = []
        
        # Get recent projects
        try:
            recent_projects = Project.query.filter_by(user_id=user_id)\
                .order_by(Project.created_at.desc())\
                .limit(5).all()
            
            for project in recent_projects:
                recent_items.append({
                    'type': 'project',
                    'id': project.id,
                    'title': project.title,
                    'description': project.description or '',
                    'technologies': project.technologies or '',
                    'timeAgo': _get_time_ago(project.created_at)
                })
        except Exception:
            pass

        result = {
            'success': True,
            'recent': recent_items[:5]
        }

        # Cache the result for 5 minutes
        try:
            from utils.redis_utils import redis_cache
            redis_cache.set_cache(cache_key, result, ttl=300)  # 5 minutes
        except Exception:
            pass  # Continue without caching if Redis fails

        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting recent contexts: {e}")
        return jsonify({'success': False, 'error': 'Internal server error', 'recent': []}), 500

def _get_time_ago(timestamp):
    """Convert timestamp to readable time ago"""
    if not timestamp:
        return 'recently'
    
    now = datetime.utcnow()
    diff = now - timestamp
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        return f'{int(seconds / 60)}m ago'
    elif seconds < 86400:
        return f'{int(seconds / 3600)}h ago'
    elif seconds < 2592000:
        return f'{int(seconds / 86400)}d ago'
    else:
        return f'{int(seconds / 2592000)}mo ago'

# ============================================================================
# INITIALIZATION
# ============================================================================

def init_recommendations_blueprint():
    """Initialize the recommendations blueprint"""
    logger.info("Initializing complete recommendations blueprint...")
    
    # Models are now lazy-loaded - no initialization at startup
    # init_models() is kept for compatibility but does nothing
    init_models()
    
    # Initialize engines with error handling
    # Only Unified Orchestrator is initialized - other engines are deprecated
    try:
        init_engines()
    except Exception as e:
        logger.error(f"Error initializing engines: {e}")
        # Engine initialization failed, but blueprint can still function with fallbacks
    
    return recommendations_bp

# Initialize the blueprint when this module is imported
init_recommendations_blueprint()

