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

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from dataclasses import asdict
from extensions import limiter
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

from uow.unit_of_work import UnitOfWork

# Create blueprint
recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

def get_rec_service(uow):
    return RecommendationService(uow)

def get_content_service(uow):
    return ContentService(uow)

# ============================================================================
# API ROUTES - Using Unified Orchestrator
# ============================================================================



# ============================================================================
# DEPRECATED ENDPOINTS - Removed from frontend, kept for backward compatibility
# ============================================================================

# @recommendations_bp.route('/ensemble', methods=['POST'])
# @jwt_required()
# def get_ensemble_recommendations():
#     """DEPRECATED: Get ensemble recommendations - Use /unified-orchestrator instead"""
#     return jsonify({'error': 'This endpoint is deprecated. Use /unified-orchestrator instead.'}), 410

# @recommendations_bp.route('/ensemble/quality', methods=['POST'])
# @jwt_required()
# def get_quality_ensemble_recommendations():
#     """DEPRECATED: Get quality ensemble recommendations - Use /unified-orchestrator instead"""
#     return jsonify({'error': 'This endpoint is deprecated. Use /unified-orchestrator instead.'}), 410

@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
def get_unified_orchestrator_recommendations():
    """Get recommendations using PRODUCTION-OPTIMIZED Unified Orchestrator"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        with UnitOfWork() as uow:
            rec_service = get_rec_service(uow)
            response = rec_service.get_recommendations(user_id, data)
            logger.info("recommendation_unified_orchestrator_success", user_id=user_id)
            return jsonify(response)
            
    except Exception as e:
        logger.error("recommendation_unified_orchestrator_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/generate-context', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
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
        
        # Import modular classes
        from ml.recommendation.schemas import (
            UnifiedRecommendationRequest, 
            UnifiedRecommendationResult
        )
        from ml.orchestrator import get_orchestrator as get_unified_orchestrator
        
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
        
    except Exception as e:
        logger.error("recommendation_personalized_context_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API ROUTES - Using Standalone Engines (Legacy)
# ============================================================================

@recommendations_bp.route('/unified', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
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
        logger.info("recommendation_unified_legacy_success", user_id=user_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error("recommendation_unified_legacy_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/unified-project/<int:project_id>', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
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
        # NOTE: Project-level recommendations do NOT include subtasks - only project info
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
        logger.info("recommendation_unified_project_success", project_id=project_id, user_id=user_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error("recommendation_unified_project_failed", project_id=project_id, error=str(e), user_id=user_id)
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
        # NOTE: Project-level recommendations do NOT include subtasks - only project info
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
        
        logger.info("recommendation_project_legacy_success", project_id=project_id, user_id=user_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error("recommendation_project_legacy_failed", project_id=project_id, error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

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
        except:
            pass
        
        enhanced_description = f"Task: {task.title}"
        if task_description:
            enhanced_description += f" - {task_description}"
        
        # Add incomplete subtasks to context
        if incomplete_subtasks:
            subtask_titles = [st.title for st in incomplete_subtasks]
            enhanced_description += f" Subtasks to complete: {', '.join(subtask_titles)}"
        
        # Use modular orchestrator
        from ml.orchestrator import get_orchestrator as get_unified_orchestrator
        from ml.recommendation.schemas import UnifiedRecommendationRequest
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
                # Get subtask embeddings and boost scores based on similarity
                subtask_embeddings = [st.embedding for st in incomplete_subtasks if st.embedding is not None]
                
                if subtask_embeddings:
                    enhanced_recommendations = []
                    for rec in recommendations:
                        content_id = rec.get('id') if isinstance(rec, dict) else getattr(rec, 'id', None)
                        if content_id:
                            content = SavedContent.query.get(content_id)
                            if content and content.embedding is not None:
                                # Calculate max similarity across all incomplete subtask embeddings
                                max_similarity = max([
                                    calculate_cosine_similarity(
                                        np.array(subtask_emb),
                                        np.array(content.embedding)
                                    ) for subtask_emb in subtask_embeddings
                                ])
                                # Boost score by embedding similarity (weight: 15% for tasks with multiple subtasks)
                                if isinstance(rec, dict):
                                    original_score = rec.get('match_score', rec.get('score', 0))
                                    embedding_boost = max_similarity * 0.15  # 15% weight
                                    rec['match_score'] = min(100, original_score + (embedding_boost * 100))
                                    rec['subtask_embedding_similarity'] = float(max_similarity)
                                else:
                                    original_score = getattr(rec, 'match_score', getattr(rec, 'score', 0))
                                    embedding_boost = max_similarity * 0.15
                                    rec.match_score = min(100, original_score + (embedding_boost * 100))
                                    rec.subtask_embedding_similarity = float(max_similarity)
                        enhanced_recommendations.append(rec)
                    
                    # Re-sort by enhanced score
                    if enhanced_recommendations:
                        enhanced_recommendations.sort(
                            key=lambda x: x.get('match_score', getattr(x, 'match_score', 0)) if isinstance(x, dict) else getattr(x, 'match_score', 0),
                            reverse=True
                        )
                        recommendations = enhanced_recommendations[:data.get('max_recommendations', 10)]
                        logger.info("recommendation_task_subtask_boost_success", count=len(recommendations), subtask_count=len(subtask_embeddings))
            except Exception as e:
                logger.warning("recommendation_task_subtask_boost_failed", error=str(e))
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
        logger.error("recommendation_task_failed", task_id=task_id, error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

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
        except:
            pass
        
        enhanced_description = f"Subtask: {subtask.title}"
        if subtask.description:
            enhanced_description += f" - {subtask.description}"
        enhanced_description += f" (Part of task: {task.title})"
        if task_description:
            enhanced_description += f" Task context: {task_description}"
        
        # Use modular orchestrator
        from ml.orchestrator import get_orchestrator as get_unified_orchestrator
        from ml.recommendation.schemas import UnifiedRecommendationRequest
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
                # Get content embeddings and boost scores based on subtask embedding similarity
                enhanced_recommendations = []
                for rec in recommendations:
                    content_id = rec.get('id') if isinstance(rec, dict) else getattr(rec, 'id', None)
                    if content_id:
                        content = SavedContent.query.get(content_id)
                        if content and content.embedding is not None:
                            # Calculate similarity between subtask embedding and content embedding
                            similarity = calculate_cosine_similarity(
                                np.array(subtask.embedding),
                                np.array(content.embedding)
                            )
                            # Boost score by embedding similarity (weight: 20%)
                            if isinstance(rec, dict):
                                original_score = rec.get('match_score', rec.get('score', 0))
                                embedding_boost = similarity * 0.2  # 20% weight for embedding similarity
                                rec['match_score'] = min(100, original_score + (embedding_boost * 100))
                                rec['subtask_embedding_similarity'] = float(similarity)
                            else:
                                # If it's a dataclass object
                                original_score = getattr(rec, 'match_score', getattr(rec, 'score', 0))
                                embedding_boost = similarity * 0.2
                                rec.match_score = min(100, original_score + (embedding_boost * 100))
                                rec.subtask_embedding_similarity = float(similarity)
                    enhanced_recommendations.append(rec)
                
                # Re-sort by enhanced score
                if enhanced_recommendations:
                    enhanced_recommendations.sort(
                        key=lambda x: x.get('match_score', getattr(x, 'match_score', 0)) if isinstance(x, dict) else getattr(x, 'match_score', 0),
                        reverse=True
                    )
                    recommendations = enhanced_recommendations[:data.get('max_recommendations', 10)]
                    logger.info("recommendation_subtask_boost_success", count=len(recommendations))
            except Exception as e:
                logger.warning("recommendation_subtask_boost_failed", error=str(e))
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
        logger.error("recommendation_subtask_failed", subtask_id=subtask_id, error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500



@recommendations_bp.route('/smart-recommendations', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
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
        logger.error("recommendation_smart_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_enhanced_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_enhanced_project_failed", project_id=project_id, error=str(e), user_id=user_id)
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
            'embedding_model_available': get_embedding_model() is not None
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error("recommendation_enhanced_status_failed", error=str(e))
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/phase3/recommendations', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
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
        logger.error("recommendation_phase3_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_phase3_feedback_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_phase3_insights_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_phase3_health_failed", error=str(e))
        return jsonify({'error': str(e)}), 500

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
            'unified_engine_available': UNIFIED_ENGINE_AVAILABLE,
            'smart_engine_available': SMART_ENGINE_AVAILABLE,
            'enhanced_engine_available': ENHANCED_ENGINE_AVAILABLE,
            'phase3_engine_available': PHASE3_ENGINE_AVAILABLE,
            'fast_gemini_available': FAST_GEMINI_AVAILABLE,
            'enhanced_modules_available': ENHANCED_MODULES_AVAILABLE,
            'embedding_model_available': get_embedding_model() is not None,
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
        logger.error("recommendation_status_failed", error=str(e))
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
                logger.error("recommendation_metrics_orchestrator_failed", error=str(e))
                metrics['unified_orchestrator'] = {'error': str(e)}
        

        
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
        logger.error("recommendation_performance_metrics_route_failed", error=str(e))
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
        logger.error("recommendation_cache_clear_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

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
            logger.warning("recommendation_cache_context_redis_failed", error=str(cache_error), user_id=user_id)

        return jsonify({
            'message': 'Context cache cleared successfully',
            'user_id': user_id
        })

    except Exception as e:
        logger.error("recommendation_cache_context_clear_route_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

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
        logger.error("recommendation_cache_clear_all_failed", error=str(e), user_id=user_id)
        return jsonify({
            'error': str(e),
            'note': 'Some caches may not have been cleared'
        }), 500

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
        logger.error("recommendation_analysis_stats_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_phase_status_failed", error=str(e))
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
        logger.error("recommendation_learning_path_legacy_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_project_type_legacy_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_contextual_legacy_failed", error=str(e), user_id=user_id)
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
            from services.background_analysis_service import analyze_content
            result = analyze_content(content_id, user_id=int(user_id))
            return jsonify({'message': 'Content analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
                        
    except Exception as e:
        logger.error("recommendation_analysis_immediate_failed", content_id=content_id, error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

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
        logger.error("recommendation_analysis_background_failed", error=str(e), user_id=user_id)
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
            from services.background_analysis_service import batch_analyze_content as batch_analyze
            result = batch_analyze(content_ids, user_id=int(user_id))
            return jsonify({'message': 'Batch analysis started', 'result': result})
        except ImportError:
            return jsonify({'error': 'Background analysis service not available'}), 500
        
    except Exception as e:
        logger.error("recommendation_analysis_batch_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# FEEDBACK AND LEARNING ENDPOINTS
# ============================================================================

@recommendations_bp.route('/feedback', methods=['POST'])
@jwt_required()
def record_recommendation_feedback():
    """Record feedback for recommendations delegating to RecommendationService"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        recommendation_id = data.get('recommendation_id')
        feedback_type = data.get('feedback_type')
        feedback_data = data.get('feedback_data', {})
        
        if not recommendation_id or not feedback_type:
            return jsonify({'error': 'Missing recommendation_id or feedback_type'}), 400
            
        with UnitOfWork() as uow:
            rec_service = get_rec_service(uow)
            feedback = rec_service.record_feedback(
                user_id=user_id,
                content_id=recommendation_id, # Simplified Mapping
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                feedback_data=feedback_data
            )
            return jsonify({'message': 'Feedback recorded successfully', 'feedback_id': feedback.id})
            
    except Exception as e:
        logger.error("recommendation_feedback_failed", recommendation_id=recommendation_id, error=str(e), user_id=user_id)
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
        logger.error("recommendation_user_preferences_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_insights_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SEARCH AND DISCOVERY ENDPOINTS
# ============================================================================

@recommendations_bp.route('/discover', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
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
                'discovery_mode': True
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
                    max_recommendations=15
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
        logger.error("recommendation_discovery_failed", error=str(e), user_id=user_id)
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
        logger.error("recommendation_similar_failed", content_id=content_id, error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

# ============================================================================
# GEMINI-ENHANCED ENDPOINTS
# ============================================================================

@recommendations_bp.route('/ultra-fast', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
def get_ultra_fast_recommendations():
    """Get ultra-fast recommendations using vector similarity search"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        try:
            from ultra_fast_recommendation_engine import get_ultra_fast_engine
            engine = get_ultra_fast_engine()
            result = engine.get_ultra_fast_recommendations(user_id, user_input)
            return jsonify(result)
        except ImportError:
            return jsonify({'error': 'Ultra-fast engine not available'}), 500
        except Exception as e:
            logger.error("recommendation_ultra_fast_engine_failed", error=str(e), user_id=user_id)
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        logger.error("recommendation_ultra_fast_failed", error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/ultra-fast-project/<int:project_id>', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute", key_func=lambda: get_jwt_identity())
def get_ultra_fast_project_recommendations(project_id):
    """Get ultra-fast project recommendations"""
    try:
        user_id = get_jwt_identity()
        user_input = request.get_json() or {}
        
        try:
            from ultra_fast_recommendation_engine import get_ultra_fast_engine
            engine = get_ultra_fast_engine()
            result = engine.get_project_recommendations(user_id, project_id)
            return jsonify(result)
        except ImportError:
            return jsonify({'error': 'Ultra-fast engine not available'}), 500
        except Exception as e:
            logger.error("recommendation_ultra_fast_project_engine_failed", project_id=project_id, error=str(e), user_id=user_id)
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        logger.error("recommendation_ultra_fast_project_failed", project_id=project_id, error=str(e), user_id=user_id)
        return jsonify({'error': str(e)}), 500

@recommendations_bp.route('/gemini-status', methods=['GET'])
@jwt_required()
def get_gemini_status():
    """Check if Gemini is available and working"""
    try:
        status_info = {
            'gemini_available': FAST_GEMINI_AVAILABLE,
            'status': 'available' if FAST_GEMINI_AVAILABLE else 'unavailable',
            'details': {
                'fast_gemini_available': FAST_GEMINI_AVAILABLE,
                'api_key_set': bool(os.environ.get('GEMINI_API_KEY')),
                'test_result': None,
                'error_message': None
            }
        }
        
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error("recommendation_gemini_status_failed", error=str(e))
        return jsonify({
            'gemini_available': False,
            'status': 'error',
            'details': {
                'error_message': str(e)
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
                    except:
                        continue
        except:
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
        logger.error("recommendation_suggested_contexts_failed", error=str(e))
        return jsonify({'success': False, 'error': str(e), 'contexts': []}), 500

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
        except:
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
        logger.error("recommendation_recent_contexts_failed", error=str(e))
        return jsonify({'success': False, 'error': str(e), 'recent': []}), 500

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
    """Initialize the recommendations blueprint (Legacy hook kept for compatibility)"""
    logger.info("recommendation_blueprint_initialized")
    return recommendations_bp
    
    return recommendations_bp

# Initialize the blueprint when this module is imported
init_recommendations_blueprint()

