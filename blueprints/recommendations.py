#!/usr/bin/env python3
"""
Complete Recommendations Blueprint
Combines all features from both versions with proper circular import handling
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint FIRST to avoid circular imports
recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

# Initialize global flags for engine availability
UNIFIED_ORCHESTRATOR_AVAILABLE = False
UNIFIED_ENGINE_AVAILABLE = False
SMART_ENGINE_AVAILABLE = False
ENHANCED_ENGINE_AVAILABLE = False
PHASE3_ENGINE_AVAILABLE = False
FAST_GEMINI_AVAILABLE = False
ENHANCED_MODULES_AVAILABLE = False

# Global engine instances (will be initialized lazily)
unified_engine_instance = None
embedding_model = None
gemini_analyzer = None
rate_limiter = None

def init_models():
    """Initialize models with error handling"""
    global embedding_model, gemini_analyzer, rate_limiter
    
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        # Initialize model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Fix meta tensor issue by using to_empty() instead of to()
        if hasattr(torch, 'meta') and torch.meta.is_available():
            # Use to_empty() for meta tensors
            embedding_model = embedding_model.to_empty(device='cpu')
        else:
            # Fallback to CPU
            embedding_model = embedding_model.to('cpu')
        
        logger.info("Embedding model initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing embedding model: {e}")
        embedding_model = None
    
    try:
        from gemini_utils import GeminiAnalyzer
        from rate_limit_handler import GeminiRateLimiter
        gemini_analyzer = GeminiAnalyzer()
        rate_limiter = GeminiRateLimiter()
        logger.info("Gemini components initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Gemini components: {e}")
        gemini_analyzer = None
        rate_limiter = None

def init_engines():
    """Initialize recommendation engines with lazy loading"""
    global UNIFIED_ORCHESTRATOR_AVAILABLE, UNIFIED_ENGINE_AVAILABLE, SMART_ENGINE_AVAILABLE, ENHANCED_ENGINE_AVAILABLE
    global PHASE3_ENGINE_AVAILABLE, FAST_GEMINI_AVAILABLE, ENHANCED_MODULES_AVAILABLE
    global unified_engine_instance
    
    # Import unified orchestrator
    try:
        from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
        from gemini_integration_layer import get_gemini_integration
        UNIFIED_ORCHESTRATOR_AVAILABLE = True
        logger.info("Unified orchestrator initialized successfully")
    except ImportError as e:
        logger.warning(f"Unified orchestrator not available: {e}")
        UNIFIED_ORCHESTRATOR_AVAILABLE = False

    # Import enhanced modules
    try:
        from advanced_tech_detection import advanced_tech_detector
        from adaptive_scoring_engine import adaptive_scoring_engine
        ENHANCED_MODULES_AVAILABLE = True
        logger.info("Enhanced modules initialized successfully")
    except ImportError as e:
        logger.warning(f"Enhanced modules not available: {e}")
        ENHANCED_MODULES_AVAILABLE = False

    # Import standalone engines with error handling
    try:
        from unified_recommendation_engine import UnifiedRecommendationEngine
        unified_engine_instance = UnifiedRecommendationEngine()
        UNIFIED_ENGINE_AVAILABLE = True
        logger.info("Unified recommendation engine initialized")
    except ImportError as e:
        logger.warning(f"Unified recommendation engine not available: {e}")
        UNIFIED_ENGINE_AVAILABLE = False

    try:
        from enhanced_recommendation_engine import get_enhanced_recommendations, unified_engine
        ENHANCED_ENGINE_AVAILABLE = True
        logger.info("Enhanced recommendation engine initialized")
    except ImportError as e:
        logger.warning(f"Enhanced recommendation engine not available: {e}")
        ENHANCED_ENGINE_AVAILABLE = False

    try:
        from phase3_enhanced_engine import (
            get_enhanced_recommendations_phase3,
            record_user_feedback_phase3,
            get_user_learning_insights,
            get_system_health_phase3
        )
        PHASE3_ENGINE_AVAILABLE = True
        logger.info("Phase 3 enhanced engine initialized")
    except ImportError as e:
        logger.warning(f"Phase 3 enhanced engine not available: {e}")
        PHASE3_ENGINE_AVAILABLE = False

    # Check if SmartRecommendationEngine can be imported (but don't instantiate)
    try:
        from smart_recommendation_engine import SmartRecommendationEngine
        SMART_ENGINE_AVAILABLE = True
        logger.info("Smart recommendation engine import successful")
    except ImportError as e:
        logger.warning(f"Smart recommendation engine not available: {e}")
        SMART_ENGINE_AVAILABLE = False

    # Check if FastGeminiEngine can be imported (but don't instantiate)
    try:
        # Try the correct class name first
        from fast_gemini_engine import AdvancedGeminiEngine as FastGeminiEngine
        FAST_GEMINI_AVAILABLE = True
        logger.info("Fast Gemini engine import successful (AdvancedGeminiEngine)")
    except ImportError:
        try:
            # Fallback to old name if it exists
            from fast_gemini_engine import FastGeminiEngine
            FAST_GEMINI_AVAILABLE = True
            logger.info("Fast Gemini engine import successful (FastGeminiEngine)")
        except ImportError as e:
            logger.warning(f"Fast Gemini engine not available: {e}")
            FAST_GEMINI_AVAILABLE = False

# Lazy initialization functions
def get_unified_engine():
    """Get unified engine instance with lazy initialization"""
    global unified_engine_instance, UNIFIED_ENGINE_AVAILABLE
    if not UNIFIED_ENGINE_AVAILABLE:
        try:
            from unified_recommendation_engine import UnifiedRecommendationEngine
            unified_engine_instance = UnifiedRecommendationEngine()
            UNIFIED_ENGINE_AVAILABLE = True
            logger.info("Unified engine initialized lazily")
        except Exception as e:
            logger.error(f"Failed to initialize unified engine: {e}")
            return None
    return unified_engine_instance

def get_smart_engine(user_id):
    """Get smart engine instance with lazy initialization"""
    try:
        from smart_recommendation_engine import SmartRecommendationEngine
        return SmartRecommendationEngine(user_id)
    except Exception as e:
        logger.error(f"Failed to initialize smart engine: {e}")
        return None

def get_fast_gemini_engine(user_id):
    """Get fast Gemini engine instance with lazy initialization"""
    try:
        from fast_gemini_engine import AdvancedGeminiEngine
        return AdvancedGeminiEngine()
    except Exception as e:
        logger.error(f"Failed to initialize fast Gemini engine: {e}")
        return None

# Cache management functions
def get_cached_recommendations(cache_key):
    """Get cached recommendations"""
    try:
        from redis_utils import redis_cache
        return redis_cache.get_cache(cache_key)
    except Exception as e:
        logger.error(f"Error getting cached recommendations: {e}")
        return None

def cache_recommendations(cache_key, data, ttl=3600):
    """Cache recommendations"""
    try:
        from redis_utils import redis_cache
        return redis_cache.set_cache(cache_key, data, ttl)
    except Exception as e:
        logger.error(f"Error caching recommendations: {e}")
        return False

def invalidate_user_recommendations(user_id):
    """Invalidate all cached recommendations for a user"""
    try:
        from cache_invalidation_service import cache_invalidator
        return cache_invalidator.invalidate_recommendation_cache(user_id)
    except Exception as e:
        logger.error(f"Error invalidating user recommendations: {e}")
        return False

# ============================================================================
# API ROUTES - Using Unified Orchestrator
# ============================================================================

@recommendations_bp.route('/gemini', methods=['POST'])
@jwt_required()
def get_gemini_recommendations():
    """Get Gemini AI-powered recommendations"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Import Gemini integration
        try:
            from gemini_integration_layer import get_gemini_enhanced_recommendations
        except ImportError as e:
            logger.error(f"Gemini integration not available: {e}")
            return jsonify({'error': 'Gemini integration not available'}), 500
        
        # Get Gemini recommendations
        results = get_gemini_enhanced_recommendations(user_id, data)
        
        response = {
            'recommendations': results,
            'total_recommendations': len(results),
            'engine_used': 'Gemini AI',
            'performance_metrics': {
                'ai_enhanced': True,
                'total_recommendations': len(results)
            },
            'request_processed': {
                'title': data.get('title', ''),
                'technologies': data.get('technologies', ''),
                'ai_enhanced': True
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in Gemini recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/ensemble', methods=['POST'])
@jwt_required()
def get_ensemble_recommendations():
    """Get ensemble recommendations using optimized ensemble engine"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Use optimized ensemble engine
        try:
            from ensemble_engine import get_ensemble_recommendations as get_ensemble
            results = get_ensemble(user_id, data)
            
            response = {
                'recommendations': results,
                'total_recommendations': len(results),
                'engine_used': 'ReliableEnsemble',
                'performance_metrics': {
                    'cached': False,
                    'engines_used': data.get('engines', ['unified']),
                    'optimization_level': 'reliable_unified_only'
                }
            }
            
            return jsonify(response)
            
        except ImportError:
            # Fallback to original ensemble engine
            logger.warning("Optimized ensemble engine not available, using fallback")
            return jsonify({'error': 'Ensemble engine not available'}), 500
        
    except Exception as e:
        logger.error(f"Error in ensemble recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/ensemble/quality', methods=['POST'])
@jwt_required()
def get_quality_ensemble_recommendations():
    """Get high relevance recommendations using High Relevance Engine directly"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Use High Relevance Engine directly
        try:
            from high_relevance_engine import high_relevance_engine
            from models import SavedContent, db
            from flask import Flask
            from dotenv import load_dotenv
            import os
            
            # Load environment variables
            load_dotenv()
            
            # Create temporary Flask app for database context
            temp_app = Flask(__name__)
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
            temp_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            
            # Initialize SQLAlchemy with the temporary app
            db.init_app(temp_app)
            
            with temp_app.app_context():
                with db.session.begin():
                    # Get user's technologies for filtering
                    user_technologies = [tech.strip().lower() for tech in data.get('technologies', '').split(',') if tech.strip()]
                    
                    # Build base query for high-quality content
                    base_query = SavedContent.query.filter(
                        SavedContent.quality_score >= 5,
                        SavedContent.extracted_text.isnot(None),
                        SavedContent.extracted_text != ''
                    )
                    
                    # Try to find content with matching technologies first
                    if user_technologies:
                        # Look for content with matching technologies in analysis
                        from models import ContentAnalysis
                        
                        # First, try to find content with PRIMARY technology matches (exact matches)
                        primary_tech_conditions = []
                        for tech in user_technologies:
                            primary_tech_conditions.append(
                                SavedContent.analyses.any(
                                    ContentAnalysis.technology_tags.ilike(f'%{tech}%')
                                )
                            )
                        
                        # Get content with primary technology matches
                        primary_matched_content = base_query.filter(
                            db.or_(*primary_tech_conditions)
                        ).order_by(
                            SavedContent.quality_score.desc(),
                            SavedContent.saved_at.desc()
                        ).limit(15).all()
                        
                        # Filter to prioritize content with more relevant technologies
                        tech_matched_content = []
                        for content in primary_matched_content:
                            # Get technologies for this content
                            content_technologies = []
                            if content.analyses:
                                for analysis in content.analyses:
                                    if analysis.technology_tags:
                                        content_technologies.extend([tech.strip().lower() for tech in analysis.technology_tags.split(',')])
                            
                            # Calculate relevance score
                            relevant_tech_count = sum(1 for user_tech in user_technologies if user_tech in content_technologies)
                            
                            # Only include if it has good relevance (at least 30% of user techs or primary tech match)
                            if relevant_tech_count >= 1 and (relevant_tech_count / max(len(user_technologies), 1)) >= 0.3:
                                tech_matched_content.append(content)
                            
                            # Limit to top 10 most relevant
                            if len(tech_matched_content) >= 10:
                                break
                        
                        # If we have enough tech-matched content, use it
                        if len(tech_matched_content) >= 3:
                            all_content = tech_matched_content
                            logger.info(f"Found {len(all_content)} content items with matching technologies: {user_technologies}")
                        else:
                            # Otherwise get general high-quality content
                            all_content = base_query.order_by(
                                SavedContent.quality_score.desc(),
                                SavedContent.saved_at.desc()
                            ).limit(15).all()
                            logger.info(f"Not enough tech-matched content, using {len(all_content)} general high-quality items")
                    else:
                        # No specific technologies, get general content
                        all_content = base_query.order_by(
                            SavedContent.quality_score.desc(),
                            SavedContent.saved_at.desc()
                        ).limit(15).all()
                        logger.info(f"Using {len(all_content)} general high-quality content items")
                
                # Convert to format expected by high relevance engine
                bookmarks_data = []
                for content in all_content:
                    # Get technologies from ContentAnalysis if available
                    technologies = []
                    if content.analyses:
                        for analysis in content.analyses:
                            if analysis.technology_tags:
                                technologies.extend([tech.strip() for tech in analysis.technology_tags.split(',')])
                    
                    bookmarks_data.append({
                        'id': content.id,
                        'title': content.title,
                        'url': content.url,
                        'extracted_text': content.extracted_text or '',
                        'tags': content.tags or '',
                        'notes': content.notes or '',
                        'quality_score': content.quality_score or 5.0,
                        'created_at': content.saved_at,
                        'technologies': technologies
                    })
            
            # Prepare user input for high relevance engine
            user_input = {
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'technologies': data.get('technologies', ''),
                'project_id': data.get('project_id')
            }
            
            # Get high relevance recommendations
            results = high_relevance_engine.get_high_relevance_recommendations(
                bookmarks=bookmarks_data[:10],  # Only process top 10 bookmarks for speed
                user_input=user_input,
                max_recommendations=data.get('max_recommendations', 5)
            )
            
            response = {
                'recommendations': results,
                'total_recommendations': len(results),
                'engine_used': 'HighRelevanceEngine',
                'performance_metrics': {
                    'cached': False,
                    'engines_used': ['high_relevance'],
                    'optimization_level': 'direct_high_relevance',
                    'technology_filtering': 'enabled',
                    'quality_threshold': 5
                }
            }
            
            return jsonify(response)
            
        except Exception as e:
            logger.error(f"Error in high relevance engine: {e}")
            return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        logger.error(f"Error in quality ensemble recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
@jwt_required()
def get_unified_orchestrator_recommendations():
    """Get recommendations using the unified orchestrator (Primary endpoint)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not UNIFIED_ORCHESTRATOR_AVAILABLE:
            return jsonify({'error': 'Unified orchestrator not available'}), 500
        
        # Import required classes
        from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
        
        # Create unified request
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            technologies=data.get('technologies', ''),
            user_interests=data.get('user_interests', ''),
            project_id=data.get('project_id'),
            max_recommendations=data.get('max_recommendations', 10),
            engine_preference=data.get('engine_preference', 'auto'),
            diversity_weight=data.get('diversity_weight', 0.3),
            quality_threshold=data.get('quality_threshold', 6),
            include_global_content=data.get('include_global_content', True)
        )
        
        # Get orchestrator (already imported above)
        orchestrator = get_unified_orchestrator()
        
        # Get base recommendations
        recommendations = orchestrator.get_recommendations(unified_request)
        
        # Enhance with Gemini if requested
        if data.get('enhance_with_gemini', False):
            try:
                from gemini_integration_layer import enhance_recommendations_with_gemini
                recommendations = enhance_recommendations_with_gemini(recommendations, unified_request, user_id)
            except Exception as e:
                logger.warning(f"Gemini enhancement failed: {e}")
        
        # Convert to dictionary format
        result = []
        for rec in recommendations:
            result.append({
                'id': rec.id,
                'title': rec.title,
                'url': rec.url,
                'score': rec.score,
                'reason': rec.reason,
                'content_type': rec.content_type,
                'difficulty': rec.difficulty,
                'technologies': rec.technologies,
                'key_concepts': rec.key_concepts,
                'quality_score': rec.quality_score,
                'engine_used': rec.engine_used,
                'confidence': rec.confidence,
                'metadata': rec.metadata,
                'cached': rec.cached
            })
        
        # Get performance metrics
        performance_metrics = orchestrator.get_performance_metrics()
        
        response = {
            'recommendations': result,
            'total_recommendations': len(result),
            'engine_used': 'UnifiedOrchestrator',
            'performance_metrics': performance_metrics,
            'request_processed': {
                'title': unified_request.title,
                'technologies': unified_request.technologies,
                'engine_preference': unified_request.engine_preference,
                'quality_threshold': unified_request.quality_threshold
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in unified orchestrator recommendations: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API ROUTES - Using Standalone Engines (Legacy)
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
        
        engine = get_unified_engine()
        if not engine:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Import models here to avoid circular imports
        from models import SavedContent
        
        # Extract context from request data
        title = data.get('title', '')
        description = data.get('description', '')
        technologies = data.get('technologies', '')
        user_interests = data.get('user_interests', '')
        max_recommendations = data.get('max_recommendations', 10)
        
        # Create cache key based on request parameters
        cache_key = f"unified_recommendations:{user_id}:{hash(f'{title}{description}{technologies}{user_interests}{max_recommendations}')}"
        
        # Check cache first
        cached_result = get_cached_recommendations(cache_key)
        if cached_result:
            cached_result['cached'] = True
            return jsonify(cached_result)
        
        # Get high-quality content from all users with proper ordering
        all_content = SavedContent.query.filter(
            SavedContent.quality_score >= 7,
            SavedContent.extracted_text.isnot(None),
            SavedContent.extracted_text != ''
        ).order_by(
            SavedContent.quality_score.desc(),
            SavedContent.saved_at.desc()
        ).limit(500).all()
        
        # Convert to the format expected by UnifiedRecommendationEngine
        bookmarks_data = []
        for bookmark in all_content:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'extracted_text': bookmark.extracted_text or '',
                'tags': bookmark.tags or '',
                'notes': bookmark.notes or '',
                'quality_score': bookmark.quality_score or 7.0,
                'created_at': bookmark.saved_at
            })
        
        # Extract context using the enhanced context extraction
        context = engine.extract_context_from_input(
            title=title,
            description=description,
            technologies=technologies,
            user_interests=user_interests
        )
        
        # Get recommendations using the unified engine
        recommendations = engine.get_recommendations(
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
            'enhanced_features_available': ENHANCED_MODULES_AVAILABLE,
            'cached': False
        }
        
        # Cache the result for 30 minutes
        cache_recommendations(cache_key, result, ttl=1800)
        
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
        
        # Import models here to avoid circular imports
        from models import Project, SavedContent
        
        # Get project details
        project = Project.query.filter_by(id=project_id, user_id=user_id).first()
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        engine = get_unified_engine()
        if not engine:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Create cache key based on project and user
        cache_key = f"unified_project_recommendations:{user_id}:{project_id}:{hash(f'{project.title}{project.description}{project.technologies}')}"
        
        # Check cache first
        cached_result = get_cached_recommendations(cache_key)
        if cached_result:
            cached_result['cached'] = True
            return jsonify(cached_result)
        
        # Get high-quality content from all users with proper ordering
        all_content = SavedContent.query.filter(
            SavedContent.quality_score >= 7,
            SavedContent.extracted_text.isnot(None),
            SavedContent.extracted_text != ''
        ).order_by(
            SavedContent.quality_score.desc(),
            SavedContent.saved_at.desc()
        ).limit(500).all()
        
        # Convert to the format expected by UnifiedRecommendationEngine
        bookmarks_data = []
        for bookmark in all_content:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'extracted_text': bookmark.extracted_text or '',
                'tags': bookmark.tags or '',
                'notes': bookmark.notes or '',
                'quality_score': bookmark.quality_score or 7.0,
                'created_at': bookmark.saved_at
            })
        
        # Extract context using the enhanced context extraction
        context = engine.extract_context_from_input(
            title=project.title,
            description=project.description or '',
            technologies=project.technologies or '',
            user_interests=''
        )
        
        # Get recommendations using the unified engine
        max_recommendations = data.get('max_recommendations', 10)
        recommendations = engine.get_recommendations(
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
            'enhanced_features_available': ENHANCED_MODULES_AVAILABLE,
            'cached': False
        }
        
        # Cache the result for 30 minutes
        cache_recommendations(cache_key, result, ttl=1800)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in unified project recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project_recommendations(project_id):
    """Get project-specific recommendations using UnifiedRecommendationEngine"""
    try:
        user_id = get_jwt_identity()
        
        engine = get_unified_engine()
        if not engine:
            return jsonify({'error': 'Unified recommendation engine not available'}), 500
        
        # Import models here to avoid circular imports
        from models import Project, SavedContent
        
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
                'created_at': bookmark.saved_at
            })
        
        # Extract context from project
        context = engine.extract_context_from_input(
            title=project.title,
            description=project.description or '',
            technologies=project.technologies or '',
            user_interests=''
        )
        
        # Get recommendations
        recommendations = engine.get_recommendations(
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
        engine = get_smart_engine(user_id)
        if not engine:
            return jsonify({'error': 'Smart recommendation engine not available'}), 500
        from models import Task
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        result = engine.get_task_recommendations(user_id, task_id)
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
        engine = get_fast_gemini_engine(user_id)
        if not engine:
            return jsonify({'error': 'Fast Gemini engine not available'}), 500
        user_input['user_id'] = user_id
        from models import SavedContent
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        bookmarks_data = []
        for bookmark in user_bookmarks:
            bookmarks_data.append({
                'id': bookmark.id,
                'title': bookmark.title,
                'url': bookmark.url,
                'content': bookmark.extracted_text or bookmark.title,
                'quality_score': bookmark.quality_score or 7.0,
                'similarity_score': 0.5
            })
        if hasattr(engine, 'get_fast_gemini_recommendations'):
            result = engine.get_fast_gemini_recommendations(bookmarks_data, user_input)
        elif hasattr(engine, 'get_gemini_enhanced_recommendations'):
            result = engine.get_gemini_enhanced_recommendations(user_id, user_input)
        else:
            return jsonify({'error': 'No suitable Gemini method available'}), 500
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
        engine = get_fast_gemini_engine(user_id)
        if not engine:
            return jsonify({'error': 'Fast Gemini engine not available'}), 500
        if hasattr(engine, 'get_gemini_enhanced_project_recommendations'):
            result = engine.get_gemini_enhanced_project_recommendations(user_id, project_id)
        else:
            from models import Project
            project = Project.query.filter_by(id=project_id, user_id=user_id).first()
            if not project:
                return jsonify({'error': 'Project not found'}), 404
            user_input.update({
                'project_id': project_id,
                'project_title': project.title,
                'project_description': project.description or '',
                'project_technologies': project.technologies or ''
            })
            result = engine.get_gemini_enhanced_recommendations(user_id, user_input)
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
        engine = get_smart_engine(user_id)
        if not engine:
            return jsonify({'error': 'Smart recommendation engine not available'}), 500
        result = engine.get_recommendations(user_id, user_input)
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
        
        # Import here to avoid circular imports
        from enhanced_recommendation_engine import get_enhanced_recommendations
        
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
        
        # Import here to avoid circular imports
        from enhanced_recommendation_engine import get_enhanced_recommendations
        
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
        
        # Import here to avoid circular imports
        from phase3_enhanced_engine import get_enhanced_recommendations_phase3
        
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
        
        # Import here to avoid circular imports
        from phase3_enhanced_engine import record_user_feedback_phase3
        
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
        
        # Import here to avoid circular imports
        from phase3_enhanced_engine import get_user_learning_insights
        
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
        
        # Import here to avoid circular imports
        from phase3_enhanced_engine import get_system_health_phase3
        
        # Use Phase 3 enhanced engine
        result = get_system_health_phase3()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 health: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@recommendations_bp.route('/status', methods=['GET'])
def get_engine_status():
    """Get status of all recommendation engines"""
    try:
        # Check Gemini integration availability
        gemini_integration_available = False
        try:
            from gemini_integration_layer import get_gemini_integration
            gemini_layer = get_gemini_integration()
            gemini_integration_available = gemini_layer is not None
        except Exception as e:
            logger.warning(f"Gemini integration not available: {e}")
            gemini_integration_available = False
        
        status = {
            'unified_orchestrator_available': UNIFIED_ORCHESTRATOR_AVAILABLE,
            'unified_engine_available': UNIFIED_ENGINE_AVAILABLE,
            'smart_engine_available': SMART_ENGINE_AVAILABLE,
            'enhanced_engine_available': ENHANCED_ENGINE_AVAILABLE,
            'phase3_engine_available': PHASE3_ENGINE_AVAILABLE,
            'fast_gemini_available': FAST_GEMINI_AVAILABLE,
            'enhanced_modules_available': ENHANCED_MODULES_AVAILABLE,
            'gemini_analyzer_available': gemini_analyzer is not None,
            'gemini_integration_available': gemini_integration_available,
            'embedding_model_available': embedding_model is not None,
            'total_engines_available': sum([
                UNIFIED_ORCHESTRATOR_AVAILABLE,
                UNIFIED_ENGINE_AVAILABLE,
                SMART_ENGINE_AVAILABLE,
                ENHANCED_ENGINE_AVAILABLE,
                PHASE3_ENGINE_AVAILABLE,
                FAST_GEMINI_AVAILABLE
            ]),
            'recommended_engine': 'unified_orchestrator' if UNIFIED_ORCHESTRATOR_AVAILABLE else 'unified_engine'
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """Get detailed performance metrics for all engines"""
    try:
        metrics = {}
        
        # Get unified orchestrator metrics
        if UNIFIED_ORCHESTRATOR_AVAILABLE:
            try:
                orchestrator = get_unified_orchestrator()
                metrics['unified_orchestrator'] = orchestrator.get_performance_metrics()
            except Exception as e:
                logger.error(f"Error getting orchestrator metrics: {e}")
                metrics['unified_orchestrator'] = {'error': str(e)}
        
        # Get Gemini integration metrics
        try:
            from gemini_integration_layer import get_gemini_integration
            gemini_layer = get_gemini_integration()
            metrics['gemini_integration'] = gemini_layer.get_performance_metrics()
        except Exception as e:
            logger.error(f"Error getting Gemini metrics: {e}")
            metrics['gemini_integration'] = {'error': str(e)}
        
        # Get Redis cache stats
        try:
            from redis_utils import redis_cache
            metrics['redis_cache'] = redis_cache.get_cache_stats()
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {e}")
            metrics['redis_cache'] = {'error': str(e)}
        
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
            metrics['database'] = {'error': str(e)}
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': str(e)}), 500

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
        
        # Import models here to avoid circular imports
        from models import SavedContent, ContentAnalysis
        
        # Get user-specific analysis stats
        total_user_content = SavedContent.query.filter_by(user_id=user_id).count()
        analyzed_user_content = ContentAnalysis.query.join(SavedContent).filter(
            SavedContent.user_id == user_id
        ).count()
        
        # Calculate pending analysis for this user
        pending_analysis = total_user_content - analyzed_user_content
        
        # Only show batch processing if user has content that needs analysis
        if pending_analysis > 0 and total_user_content > 0:
            # Calculate coverage percentage for this user
            coverage_percentage = round((analyzed_user_content / total_user_content) * 100, 1)
            
            stats = {
                'total_content': total_user_content,
                'analyzed_content': analyzed_user_content,
                'pending_analysis': pending_analysis,
                'coverage_percentage': coverage_percentage,
                'analysis_percentage': coverage_percentage,  # Keep for backward compatibility
                'batch_processing_active': True,
                'batch_message': f"Processing {pending_analysis} items ({coverage_percentage}% complete)"
            }
        else:
            # No batch processing needed for this user
            stats = {
                'total_content': total_user_content,
                'analyzed_content': analyzed_user_content,
                'pending_analysis': 0,
                'coverage_percentage': 100.0 if total_user_content > 0 else 0.0,
                'analysis_percentage': 100.0 if total_user_content > 0 else 0.0,  # Keep for backward compatibility
                'batch_processing_active': False,
                'batch_message': None
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
            from background_analysis_service import batch_analyze_content as batch_analyze
            result = batch_analyze(content_ids)
            return jsonify({'message': 'Batch analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FEEDBACK AND LEARNING ENDPOINTS
# ============================================================================

@recommendations_bp.route('/feedback', methods=['POST'])
@jwt_required()
def record_recommendation_feedback():
    """Record feedback for recommendations"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        recommendation_id = data.get('recommendation_id')
        feedback_type = data.get('feedback_type')  # 'positive', 'negative', 'neutral'
        feedback_data = data.get('feedback_data', {})
        
        if not recommendation_id or not feedback_type:
            return jsonify({'error': 'Missing recommendation_id or feedback_type'}), 400
        
        # Import models here to avoid circular imports
        from models import db, Feedback
        
        # Create feedback record
        feedback = Feedback(
            user_id=user_id,
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            feedback_data=json.dumps(feedback_data),
            created_at=datetime.utcnow()
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # If Phase 3 engine is available, also record there
        if PHASE3_ENGINE_AVAILABLE:
            try:
                from phase3_enhanced_engine import record_user_feedback_phase3
                record_user_feedback_phase3(user_id, recommendation_id, feedback_type, feedback_data)
            except Exception as e:
                logger.warning(f"Failed to record Phase 3 feedback: {e}")
        
        return jsonify({'message': 'Feedback recorded successfully'})
        
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/user-preferences', methods=['GET'])
@jwt_required()
def get_user_preferences():
    """Get user preferences and learning patterns"""
    try:
        user_id = get_jwt_identity()
        
        # Import models here to avoid circular imports
        from models import User, Feedback, SavedContent
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's feedback patterns
        feedback_stats = db.session.query(
            Feedback.feedback_type,
            db.func.count(Feedback.id).label('count')
        ).filter_by(user_id=user_id).group_by(Feedback.feedback_type).all()
        
        # Get user's content statistics
        content_stats = {
            'total_bookmarks': SavedContent.query.filter_by(user_id=user_id).count(),
            'avg_quality_score': db.session.query(
                db.func.avg(SavedContent.quality_score)
            ).filter_by(user_id=user_id).scalar() or 0
        }
        
        # Get top technologies from tags
        top_technologies = db.session.query(
            SavedContent.tags,
            db.func.count(SavedContent.id).label('count')
        ).filter(
            SavedContent.user_id == user_id,
            SavedContent.tags.isnot(None)
        ).group_by(SavedContent.tags).order_by(
            db.func.count(SavedContent.id).desc()
        ).limit(10).all()
        
        preferences = {
            'user_id': user_id,
            'feedback_patterns': {stat.feedback_type: stat.count for stat in feedback_stats},
            'content_statistics': content_stats,
            'top_technologies': [{'technology': tag, 'count': count} for tag, count in top_technologies if tag],
            'learning_style': 'adaptive'  # Could be enhanced with ML
        }
        
        return jsonify(preferences)
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/learning-insights', methods=['GET'])
@jwt_required()
def get_learning_insights():
    """Get learning insights for user"""
    try:
        user_id = get_jwt_identity()
        
        # If Phase 3 engine is available, use it
        if PHASE3_ENGINE_AVAILABLE:
            try:
                from phase3_enhanced_engine import get_user_learning_insights
                result = get_user_learning_insights(user_id)
                return jsonify(result)
            except Exception as e:
                logger.warning(f"Phase 3 insights failed, using fallback: {e}")
        
        # Fallback to basic insights
        from models import SavedContent, Feedback
        
        # Basic learning patterns
        recent_bookmarks = SavedContent.query.filter_by(user_id=user_id).order_by(
            SavedContent.created_at.desc()
        ).limit(20).all()
        
        # Analyze recent patterns
        technologies = []
        for bookmark in recent_bookmarks:
            if bookmark.tags:
                technologies.extend(bookmark.tags.split(','))
        
        tech_frequency = defaultdict(int)
        for tech in technologies:
            tech_frequency[tech.strip().lower()] += 1
        
        insights = {
            'user_id': user_id,
            'learning_trends': {
                'recent_technologies': dict(list(tech_frequency.items())[:10]),
                'learning_velocity': len(recent_bookmarks),
                'engagement_score': 7.5  # Basic score
            },
            'recommendations': [
                'Continue exploring your current technology stack',
                'Consider diversifying into related technologies',
                'Regular review sessions would be beneficial'
            ],
            'engine_used': 'basic_insights'
        }
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Error getting learning insights: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SEARCH AND DISCOVERY ENDPOINTS
# ============================================================================

@recommendations_bp.route('/discover', methods=['POST'])
@jwt_required()
def discover_recommendations():
    """Discover new recommendations based on exploration"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        # Use the best available engine for discovery
        if PHASE3_ENGINE_AVAILABLE:
            from phase3_enhanced_engine import get_enhanced_recommendations_phase3
            result = get_enhanced_recommendations_phase3(user_id, {
                **data,
                'discovery_mode': True,
                'diversity_weight': 0.7
            })
        elif ENHANCED_ENGINE_AVAILABLE:
            from enhanced_recommendation_engine import get_enhanced_recommendations
            result = get_enhanced_recommendations(user_id, {
                **data,
                'discovery_mode': True
            })
        elif UNIFIED_ENGINE_AVAILABLE:
            engine = get_unified_engine()
            if engine:
                from models import SavedContent
                user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
                bookmarks_data = [{
                    'id': b.id, 'title': b.title, 'url': b.url,
                    'extracted_text': b.extracted_text or '', 'tags': b.tags or '',
                    'quality_score': b.quality_score or 7.0, 'created_at': b.created_at
                } for b in user_bookmarks]
                
                context = engine.extract_context_from_input(
                    title=data.get('title', ''),
                    description=data.get('description', ''),
                    technologies=data.get('technologies', ''),
                    user_interests=data.get('user_interests', '')
                )
                
                recommendations = engine.get_recommendations(
                    bookmarks=bookmarks_data,
                    context=context,
                    max_recommendations=15,
                    diversity_weight=0.7
                )
                
                result = {
                    'recommendations': recommendations,
                    'discovery_mode': True,
                    'engine_used': 'UnifiedRecommendationEngine'
                }
            else:
                return jsonify({'error': 'No recommendation engine available'}), 500
        else:
            return jsonify({'error': 'No discovery engine available'}), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in discovery recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/similar/<int:content_id>', methods=['GET'])
@jwt_required()
def get_similar_content(content_id):
    """Get content similar to a specific bookmark"""
    try:
        user_id = get_jwt_identity()
        
        # Import models here to avoid circular imports
        from models import SavedContent
        
        # Get the target content
        target_content = SavedContent.query.filter_by(id=content_id, user_id=user_id).first()
        if not target_content:
            return jsonify({'error': 'Content not found'}), 404
        
        # Use unified engine for similarity
        engine = get_unified_engine()
        if not engine:
            return jsonify({'error': 'Unified engine not available'}), 500
        
        # Get all user content
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        bookmarks_data = []
        for bookmark in user_bookmarks:
            if bookmark.id != content_id:  # Exclude the target content
                bookmarks_data.append({
                    'id': bookmark.id,
                    'title': bookmark.title,
                    'url': bookmark.url,
                    'extracted_text': bookmark.extracted_text or '',
                    'tags': bookmark.tags or '',
                    'notes': bookmark.notes or '',
                    'quality_score': bookmark.quality_score or 7.0,
                    'created_at': bookmark.saved_at
                })
        
        # Create context from target content
        context = engine.extract_context_from_input(
            title=target_content.title,
            description=target_content.extracted_text or '',
            technologies=target_content.tags or '',
            user_interests=''
        )
        
        # Get similar recommendations
        recommendations = engine.get_recommendations(
            bookmarks=bookmarks_data,
            context=context,
            max_recommendations=10
        )
        
        result = {
            'target_content': {
                'id': target_content.id,
                'title': target_content.title,
                'url': target_content.url
            },
            'similar_content': recommendations,
            'context_used': context,
            'engine_used': 'UnifiedRecommendationEngine'
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting similar content: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# INITIALIZATION
# ============================================================================

def init_recommendations_blueprint():
    """Initialize the recommendations blueprint"""
    logger.info("Initializing complete recommendations blueprint...")
    
    # Initialize models first
    init_models()
    
    # Initialize engines with error handling
    try:
        init_engines()
    except Exception as e:
        logger.error(f"Error initializing engines: {e}")
    
    # Log engine availability
    logger.info(f"Unified Engine: {'✅ Available' if UNIFIED_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Smart Engine: {'✅ Available' if SMART_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Enhanced Engine: {'✅ Available' if ENHANCED_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Phase 3 Engine: {'✅ Available' if PHASE3_ENGINE_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Fast Gemini Engine: {'✅ Available' if FAST_GEMINI_AVAILABLE else '❌ Not Available'}")
    logger.info(f"Enhanced Modules: {'✅ Available' if ENHANCED_MODULES_AVAILABLE else '❌ Not Available'}")
    
    logger.info(f"Total engines available: {sum([UNIFIED_ENGINE_AVAILABLE, SMART_ENGINE_AVAILABLE, ENHANCED_ENGINE_AVAILABLE, PHASE3_ENGINE_AVAILABLE, FAST_GEMINI_AVAILABLE])}")
    
    return recommendations_bp

# Initialize the blueprint when this module is imported
init_recommendations_blueprint()

