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
from core.http_errors import error_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from middleware.rate_limiting import limiter
from dataclasses import asdict
from core.logging_config import get_logger
from uow.unit_of_work import UnitOfWork

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
    
    # Flag name kept: the frontend reads `unified_orchestrator_available` from /status.
    try:
        from ml.intent_engine.engine import recommend  # noqa: F401
        UNIFIED_ORCHESTRATOR_AVAILABLE = True
        logger.info("intent_engine_available")
    except ImportError as e:
        logger.error(f"Intent engine not available: {e}")
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
            return error_response('missing_body', 'No data provided', 400)
        
        # Input validation
        title = data.get('title', '')
        description = data.get('description', '')
        technologies = data.get('technologies', '')
        
        if title and len(title) > 500:
            return error_response('title_too_long', 'Title exceeds maximum length of 500 characters', 400)
        if description and len(description) > 5000:
            return error_response('description_too_long', 'Description exceeds maximum length of 5000 characters', 400)
        if technologies and len(technologies) > 1000:
            return error_response('technologies_too_long', 'Technologies exceeds maximum length of 1000 characters', 400)
        
        def _optional_int(key):
            value = data.get(key)
            try:
                return int(value) if value not in (None, '') else None
            except (TypeError, ValueError):
                return None

        project_id = _optional_int('project_id')
        task_id = _optional_int('task_id')
        subtask_id = _optional_int('subtask_id')
        try:
            limit = int(data.get('max_recommendations', 10))
        except (TypeError, ValueError):
            limit = 10

        # With a project/task, the stored context is the intent; the request's echo of it is not
        # repeated. Without one, the request text itself is what the user is looking for.
        if project_id or task_id:
            query = data.get('user_interests', '') or ''
        else:
            query = ". ".join(str(p).strip() for p in (title, description, technologies, data.get('user_interests', ''))
                              if p and str(p).strip())

        import time as _time
        from ml.intent_engine.engine import recommend
        started = _time.perf_counter()
        with UnitOfWork() as uow:
            outcome = recommend(uow.session, int(user_id), query=query, project_id=project_id,
                                task_id=task_id, subtask_id=subtask_id, limit=limit)

        return jsonify({
            'recommendations': outcome['results'],
            'total_recommendations': len(outcome['results']),
            'engine_used': 'intent_engine',
            'intent': outcome['intent'],
            'cached': outcome['cached'],
            'performance_metrics': {'response_time_ms': round((_time.perf_counter() - started) * 1000, 1)},
            'request_processed': {'project_id': project_id, 'task_id': task_id, 'subtask_id': subtask_id},
        })

    except Exception:
        logger.exception("unified_orchestrator_recommendations_failed")
        return error_response('internal_error', 'Internal server error', 500)

@recommendations_bp.route('/generate-context', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def generate_personalized_context():
    """Gemini explanation of how one of the user's items helps with their current context."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        recommendation = data.get('recommendation') or {}
        context = data.get('context') or {}
        content_id = data.get('recommendation_id') or recommendation.get('id')
        try:
            content_id = int(content_id)
        except (TypeError, ValueError):
            return error_response('missing_fields', 'Missing recommendation id', 400)

        def _opt_int(value):
            try:
                return int(value) if value not in (None, '') else None
            except (TypeError, ValueError):
                return None

        project_id, task_id, subtask_id = (_opt_int(context.get(k)) for k in ('project_id', 'task_id', 'subtask_id'))
        query = '' if (project_id or task_id) else ". ".join(
            str(context.get(k)).strip() for k in ('title', 'description', 'technologies', 'user_interests')
            if context.get(k) and str(context.get(k)).strip())

        from services.multi_user_api_manager import get_user_api_key
        user_api_key = get_user_api_key(user_id)
        if not user_api_key:
            return error_response('api_key_required', 'User API key not found. Please add your Gemini API key in settings.', 400)

        from ml.intent_engine.explain import build_explain_prompt, generate_explanation
        with UnitOfWork() as uow:
            prompt = build_explain_prompt(uow.session, user_id, content_id, query=query, project_id=project_id,
                                          task_id=task_id, subtask_id=subtask_id)
        # Gemini runs after the session is closed: a transaction held for the call pins a pooled
        # connection for seconds, and a few slow calls exhaust the pool for every other request.
        summary = generate_explanation(prompt, content_id, api_key=user_api_key) if prompt else None
        if summary is None:
            return error_response('explanation_unavailable', 'Could not generate an explanation for this item', 404)

        return jsonify({'success': True, 'context_summary': summary})

    except Exception:
        logger.exception("generate_personalized_context_failed")
        return error_response('internal_error', 'Internal server error', 500)

def _context_recommendations(user_id: int, task_id: int, subtask_id=None, limit=10):
    from ml.intent_engine.engine import recommend
    from models import Project, Subtask, Task
    with UnitOfWork() as uow:
        task = (uow.session.query(Task).join(Project, Task.project_id == Project.id)
                .filter(Task.id == task_id, Project.user_id == user_id).first())
        if not task:
            return None, None, None
        subtask = None
        if subtask_id is not None:
            subtask = uow.session.query(Subtask).filter_by(id=subtask_id, task_id=task.id).first()
            if not subtask:
                return task, None, None
        outcome = recommend(uow.session, user_id, project_id=task.project_id, task_id=task.id,
                            subtask_id=subtask.id if subtask else None, limit=limit)
        return {"id": task.id, "title": task.title}, ({"id": subtask.id, "title": subtask.title} if subtask else None), outcome


def _limit_from_request():
    try:
        return int((request.get_json(silent=True) or {}).get('max_recommendations', 10))
    except (TypeError, ValueError):
        return 10


@recommendations_bp.route('/task/<int:task_id>', methods=['POST'])
@jwt_required()
def get_task_recommendations(task_id):
    """Recommendations for a task the user owns (task + its project as the intent)."""
    try:
        user_id = int(get_jwt_identity())
        task, _, outcome = _context_recommendations(user_id, task_id, limit=_limit_from_request())
        if task is None:
            return error_response('task_not_found', 'Task not found', 404)
        return jsonify({
            'recommendations': outcome['results'],
            'total_recommendations': len(outcome['results']),
            'task_id': task['id'],
            'task_title': task['title'],
            'intent': outcome['intent'],
            'engine_used': 'intent_engine',
        })
    except Exception:
        logger.exception("task_recommendations_failed")
        return error_response('internal_error', 'Internal server error', 500)


@recommendations_bp.route('/subtask/<int:subtask_id>', methods=['POST'])
@jwt_required()
def get_subtask_recommendations(subtask_id):
    """Recommendations for a subtask the user owns (subtask + task + project as the intent)."""
    try:
        user_id = int(get_jwt_identity())
        from models import Project, Subtask, Task
        with UnitOfWork() as uow:
            row = (uow.session.query(Subtask.task_id).join(Task, Subtask.task_id == Task.id)
                   .join(Project, Task.project_id == Project.id)
                   .filter(Subtask.id == subtask_id, Project.user_id == user_id).first())
        if not row:
            return error_response('subtask_not_found', 'Subtask not found', 404)
        task, subtask, outcome = _context_recommendations(user_id, row[0], subtask_id, limit=_limit_from_request())
        if subtask is None:
            return error_response('subtask_not_found', 'Subtask not found', 404)
        return jsonify({
            'recommendations': outcome['results'],
            'total_recommendations': len(outcome['results']),
            'subtask_id': subtask['id'],
            'subtask_title': subtask['title'],
            'task_id': task['id'],
            'task_title': task['title'],
            'intent': outcome['intent'],
            'engine_used': 'intent_engine',
        })
    except Exception:
        logger.exception("subtask_recommendations_failed")
        return error_response('internal_error', 'Internal server error', 500)


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
        return error_response('internal_error', 'Internal server error', 500)

@recommendations_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """Get detailed performance metrics for all engines"""
    try:
        metrics = {}
        
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
        return error_response('internal_error', 'Internal server error', 500)

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
            return error_response('internal_error', 'Failed to clear cache', 500)

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return error_response('internal_error', 'Internal server error', 500)

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
        return error_response('internal_error', 'Internal server error', 500)

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
        return error_response('internal_error', 'Internal server error. Some caches may not have been cleared.', 500)

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
        return error_response('internal_error', 'Internal server error', 500)

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
            return error_response('content_not_found', 'Content not found', 404)
        
        # Import background analysis service
        try:
            from services.background_analysis_service import analyze_content
            result = analyze_content(content_id, user_id=int(user_id))
            return jsonify({'message': 'Content analysis started', 'result': result})
        except ImportError:
            return error_response('analysis_unavailable', 'Background analysis service not available', 500)
                        
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        return error_response('internal_error', 'Internal server error', 500)

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
        return error_response('missing_body', 'JSON body required', 400)

    recommendation_id = data.get('recommendation_id')
    feedback_type = data.get('feedback_type')  # 'positive', 'negative', 'neutral'
    feedback_data = data.get('feedback_data', {})

    if not recommendation_id or not feedback_type:
        return error_response('missing_fields', 'Missing recommendation_id or feedback_type', 400)

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
        return error_response('internal_error', 'Internal server error', 500)

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
        return error_response('internal_error', 'Internal server error', 500)

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
        return error_response('internal_error', 'Internal server error', 500)

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
        return error_response('internal_error', 'Could not check Gemini status', 500, gemini_available=False)

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
            return error_response('models_unavailable', 'Models not available', 500)

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
                            project = Project.query.filter_by(id=project_id, user_id=user_id).first()
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
        return error_response('internal_error', 'Internal server error', 500)

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
            return error_response('models_unavailable', 'Models not available', 500)

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
        return error_response('internal_error', 'Internal server error', 500)

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

