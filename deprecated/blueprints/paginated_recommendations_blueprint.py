#!/usr/bin/env python3
"""
Paginated Recommendations Blueprint
Adds pagination support to recommendations with unlimited content processing
"""

import math
import time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

logger = logging.getLogger(__name__)

# Create the blueprint
paginated_recommendations_bp = Blueprint('paginated_recommendations', __name__, url_prefix='/api/recommendations')

@paginated_recommendations_bp.route('/paginated', methods=['POST'])
@jwt_required()
def get_paginated_recommendations():
    """Get paginated recommendations with unlimited content processing"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Import models here to avoid circular imports
        from models import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if this is a project-based request
        project_id = data.get('project_id')
        has_project_context = bool(project_id and (data.get('title') or data.get('description') or data.get('technologies')))
        
        # Only require tech interests for general recommendations (not project-based)
        if not has_project_context and (not user.technology_interests or not user.technology_interests.strip()):
            return jsonify({
                'error': 'No technology interests found',
                'message': 'Please add your technology interests in your profile to get personalized recommendations',
                'requires_interests': True
            }), 400
        
        # Import orchestrator
        from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
        
        # Extract pagination parameters
        page = max(1, data.get('page', 1))
        page_size = min(50, max(1, data.get('page_size', 10)))  # Max 50 items per page
        
        # Create unified request (no max_recommendations limit for internal processing)
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            technologies=data.get('technologies', ''),
            user_interests=data.get('user_interests', ''),
            project_id=data.get('project_id'),
            max_recommendations=1000,  # High limit for internal processing
            engine_preference=data.get('engine_preference', 'unified_ensemble'),  # Default to best engine
            diversity_weight=data.get('diversity_weight', 0.3),
            quality_threshold=data.get('quality_threshold', 5),
            include_global_content=data.get('include_global_content', True)
        )
        
        # Get orchestrator
        orchestrator = get_unified_orchestrator()
        
        start_time = time.time()
        
        # Get ALL recommendations (no limits)
        all_recommendations = orchestrator.get_recommendations(unified_request)
        
        # Convert to dictionary format for pagination
        all_results = []
        for rec in all_recommendations:
            all_results.append({
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
        
        # Apply pagination
        total_recommendations = len(all_results)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        paginated_results = all_results[start_index:end_index]
        
        # Calculate pagination metadata
        total_pages = math.ceil(total_recommendations / page_size) if total_recommendations > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        pagination_info = {
            'current_page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'total_items': total_recommendations,
            'has_next': has_next,
            'has_previous': has_previous,
            'next_page': page + 1 if has_next else None,
            'previous_page': page - 1 if has_previous else None,
            'start_index': start_index + 1 if total_recommendations > 0 else 0,
            'end_index': min(end_index, total_recommendations)
        }
        
        # Get performance metrics
        processing_time = time.time() - start_time
        performance_metrics = {
            'processing_time_ms': round(processing_time * 1000, 2),
            'total_recommendations_generated': total_recommendations,
            'recommendations_returned': len(paginated_results),
            'engine_used': unified_request.engine_preference,
            'unlimited_processing': True,
            'pagination_applied': True
        }
        
        # Enhanced response with pagination
        response = {
            'recommendations': paginated_results,
            'pagination': pagination_info,
            'total_recommendations': total_recommendations,
            'engine_used': unified_request.engine_preference,
            'performance_metrics': performance_metrics,
            'request_processed': {
                'title': unified_request.title,
                'technologies': unified_request.technologies,
                'engine_preference': unified_request.engine_preference,
                'quality_threshold': unified_request.quality_threshold,
                'unlimited_content_processing': True
            }
        }
        
        logger.info(f"✅ Paginated recommendations: Page {page}/{total_pages}, "
                   f"Items {pagination_info['start_index']}-{pagination_info['end_index']} of {total_recommendations}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in paginated recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@paginated_recommendations_bp.route('/unlimited', methods=['POST'])
@jwt_required()
def get_unlimited_recommendations():
    """Get ALL recommendations without any limits (for analysis/debugging)"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Import models here to avoid circular imports
        from models import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Import orchestrator
        from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
        
        # Create unlimited request
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=data.get('title', ''),
            description=data.get('description', ''),
            technologies=data.get('technologies', ''),
            user_interests=data.get('user_interests', ''),
            project_id=data.get('project_id'),
            max_recommendations=10000,  # Very high limit
            engine_preference=data.get('engine_preference', 'unified_ensemble'),
            diversity_weight=data.get('diversity_weight', 0.3),
            quality_threshold=data.get('quality_threshold', 1),  # Very inclusive
            include_global_content=data.get('include_global_content', True)
        )
        
        # Get orchestrator
        orchestrator = get_unified_orchestrator()
        
        start_time = time.time()
        
        # Get ALL recommendations
        all_recommendations = orchestrator.get_recommendations(unified_request)
        
        # Convert to dictionary format
        result = []
        for rec in all_recommendations:
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
        
        # Performance metrics
        processing_time = time.time() - start_time
        performance_metrics = {
            'processing_time_ms': round(processing_time * 1000, 2),
            'total_recommendations': len(result),
            'engine_used': unified_request.engine_preference,
            'unlimited_processing': True,
            'all_content_processed': True
        }
        
        response = {
            'recommendations': result,
            'total_recommendations': len(result),
            'engine_used': unified_request.engine_preference,
            'performance_metrics': performance_metrics,
            'unlimited_processing': True
        }
        
        logger.info(f"✅ Unlimited recommendations: {len(result)} total recommendations generated")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in unlimited recommendations: {e}")
        return jsonify({'error': str(e)}), 500

@paginated_recommendations_bp.route('/engines', methods=['GET'])
@jwt_required()
def get_available_engines():
    """Get information about available recommendation engines"""
    try:
        from unified_recommendation_orchestrator import get_unified_orchestrator
        
        orchestrator = get_unified_orchestrator()
        
        engines_info = {
            'unified_ensemble': {
                'name': 'Unified Ensemble',
                'description': 'Maximum intelligence - combines ALL engines',
                'features': ['Vector similarity', 'Context awareness', 'Content analysis', 'Intent understanding'],
                'best_for': 'Best overall results',
                'default': True
            },
            'fast': {
                'name': 'Fast Semantic Engine', 
                'description': 'Speed-focused semantic similarity only',
                'features': ['Vector similarity', 'Fast processing'],
                'best_for': 'Quick results',
                'default': False
            },
            'context': {
                'name': 'Context-Aware Engine',
                'description': 'Context-aware reasoning only', 
                'features': ['Context awareness', 'Intelligent reasoning'],
                'best_for': 'Contextual understanding',
                'default': False
            },
            'hybrid': {
                'name': 'Hybrid Engine',
                'description': 'Traditional fast+context combination',
                'features': ['Vector similarity', 'Context awareness'],
                'best_for': 'Balanced approach',
                'default': False
            }
        }
        
        # Get performance metrics if available
        try:
            performance_metrics = orchestrator.get_performance_metrics()
            engines_info['performance_metrics'] = performance_metrics
        except:
            pass
        
        return jsonify({
            'engines': engines_info,
            'total_engines': len(engines_info) - (1 if 'performance_metrics' in engines_info else 0),
            'default_engine': 'unified_ensemble',
            'unlimited_content_processing': True
        })
        
    except Exception as e:
        logger.error(f"Error getting engines info: {e}")
        return jsonify({'error': str(e)}), 500
