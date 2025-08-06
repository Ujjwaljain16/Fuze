#!/usr/bin/env python3
"""
Fast Recommendation Engine for Fuze
Uses existing logic with better caching for speed
"""

import time
import logging
from models import SavedContent, User, Feedback
from redis_utils import redis_cache
from sqlalchemy import text, func

logger = logging.getLogger(__name__)

class FastRecommendationEngine:
    """Fast recommendation engine using existing logic with better caching"""
    
    def __init__(self):
        self.cache_duration = 3600  # 1 hour
        self.max_recommendations = 10
        
    def get_fast_recommendations(self, user_id, use_cache=True):
        """Get fast recommendations using existing logic with better caching"""
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cache_key = f"fast_recommendations:{user_id}"
                cached_result = redis_cache.get_cache(cache_key)
                if cached_result is not None:
                    cached_result['cached'] = True
                    cached_result['computation_time_ms'] = 0
                    return cached_result
            
            from app import app, db
            
            with app.app_context():
                # Use the same logic as original but with better query
                user = User.query.get(user_id)
                if not user:
                    logger.warning(f"User {user_id} not found")
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': 'User not found'
                    }
                
                # Get user's bookmarks (same as original)
                user_bookmarks = SavedContent.query.filter_by(
                    user_id=user_id
                ).filter(SavedContent.embedding.isnot(None)).all()
                
                if not user_bookmarks:
                    logger.info(f"No bookmarks found for user {user_id}")
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': 'No bookmarks available'
                    }
                
                # Get all content with embeddings (optimized query)
                try:
                    all_content = db.session.execute(text("""
                        SELECT id, title, url, extracted_text, embedding, quality_score, user_id
                        FROM saved_content 
                        WHERE embedding IS NOT NULL 
                        AND user_id != :user_id
                        AND quality_score >= 5
                        AND title NOT LIKE '%Test Bookmark%'
                        AND title NOT LIKE '%test bookmark%'
                        AND title NOT LIKE '%Dictionary%'
                        AND title NOT LIKE '%dictionary%'
                        AND url NOT LIKE '%dbooks.org%'
                        AND url NOT LIKE '%pdfdrive.com%'
                        ORDER BY quality_score DESC
                        LIMIT 50
                    """), {'user_id': user_id}).fetchall()
                except Exception as e:
                    logger.error(f"Database query error: {e}")
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': f'Database error: {str(e)}'
                    }
                
                if not all_content:
                    logger.info(f"No content available for user {user_id}")
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': 'No content available'
                    }
                
                # Simple recommendation logic (no complex similarity calculations)
                recommendations = []
                for content in all_content:
                    # Simple scoring based on quality and user preferences
                    score = content[5]  # quality_score
                    
                    # Add some basic filtering
                    if score >= 6:  # Lowered threshold for more results
                        recommendations.append({
                            'id': content[0],
                            'title': content[1] or 'Untitled',
                            'url': content[2] or '',
                            'content': content[3] or '',
                            'similarity_score': score / 10.0,  # Normalize to 0-1
                            'quality_score': content[5],
                            'user_id': content[6]
                        })
                
                # Sort by quality score
                recommendations.sort(key=lambda x: x['quality_score'], reverse=True)
                recommendations = recommendations[:self.max_recommendations]
                
                computation_time = (time.time() - start_time) * 1000
                
                result = {
                    'recommendations': recommendations,
                    'cached': False,
                    'computation_time_ms': computation_time,
                    'total_candidates': len(all_content)
                }
                
                # Cache the result
                if use_cache:
                    cache_key = f"fast_recommendations:{user_id}"
                    redis_cache.set_cache(cache_key, result, self.cache_duration)
                
                logger.info(f"Fast recommendations generated: {len(recommendations)} results in {computation_time:.2f}ms")
                return result
                
        except Exception as e:
            logger.error(f"Error in fast recommendations: {e}")
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': f'Error: {str(e)}'
            }
    
    def get_fast_project_recommendations(self, user_id, project_id, use_cache=True):
        """Get fast project recommendations"""
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cache_key = f"fast_project_recommendations:{user_id}:{project_id}"
                cached_result = redis_cache.get_cache(cache_key)
                if cached_result is not None:
                    cached_result['cached'] = True
                    cached_result['computation_time_ms'] = 0
                    return cached_result
            
            from app import app, db
            
            with app.app_context():
                # Get project content (user's content since no project_id column)
                try:
                    project_content = db.session.execute(text("""
                        SELECT id, title, url, extracted_text, embedding, quality_score
                        FROM saved_content 
                        WHERE user_id = :user_id 
                        AND embedding IS NOT NULL
                        ORDER BY quality_score DESC
                        LIMIT 10
                    """), {'user_id': user_id}).fetchall()
                except Exception as e:
                    logger.error(f"Project content query error: {e}")
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': f'Database error: {str(e)}'
                    }
                
                if not project_content:
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': 'No project content available'
                    }
                
                # Get all content (same as general recommendations)
                try:
                    all_content = db.session.execute(text("""
                        SELECT id, title, url, extracted_text, embedding, quality_score, user_id
                        FROM saved_content 
                        WHERE embedding IS NOT NULL 
                        AND user_id != :user_id
                        AND quality_score >= 5
                        AND title NOT LIKE '%Test Bookmark%'
                        AND title NOT LIKE '%test bookmark%'
                        AND title NOT LIKE '%Dictionary%'
                        AND title NOT LIKE '%dictionary%'
                        AND url NOT LIKE '%dbooks.org%'
                        AND url NOT LIKE '%pdfdrive.com%'
                        ORDER BY quality_score DESC
                        LIMIT 50
                    """), {'user_id': user_id}).fetchall()
                except Exception as e:
                    logger.error(f"All content query error: {e}")
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': f'Database error: {str(e)}'
                    }
                
                if not all_content:
                    return {
                        'recommendations': [],
                        'cached': False,
                        'computation_time_ms': 0,
                        'message': 'No content available'
                    }
                
                # Simple recommendations based on quality
                recommendations = []
                for content in all_content:
                    score = content[5]  # quality_score
                    
                    if score >= 6:
                        recommendations.append({
                            'id': content[0],
                            'title': content[1] or 'Untitled',
                            'url': content[2] or '',
                            'content': content[3] or '',
                            'similarity_score': score / 10.0,
                            'quality_score': content[5],
                            'user_id': content[6]
                        })
                
                recommendations.sort(key=lambda x: x['quality_score'], reverse=True)
                recommendations = recommendations[:self.max_recommendations]
                
                computation_time = (time.time() - start_time) * 1000
                
                result = {
                    'recommendations': recommendations,
                    'cached': False,
                    'computation_time_ms': computation_time,
                    'project_id': project_id,
                    'total_candidates': len(all_content)
                }
                
                # Cache the result
                if use_cache:
                    cache_key = f"fast_project_recommendations:{user_id}:{project_id}"
                    redis_cache.set_cache(cache_key, result, self.cache_duration)
                
                logger.info(f"Fast project recommendations generated: {len(recommendations)} results in {computation_time:.2f}ms")
                return result
                
        except Exception as e:
            logger.error(f"Error in fast project recommendations: {e}")
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': f'Error: {str(e)}'
            }

# Global instance
fast_engine = FastRecommendationEngine()

def get_fast_recommendations(user_id, use_cache=True):
    """Get fast recommendations"""
    return fast_engine.get_fast_recommendations(user_id, use_cache)

def get_fast_project_recommendations(user_id, project_id, use_cache=True):
    """Get fast project recommendations"""
    return fast_engine.get_fast_project_recommendations(user_id, project_id, use_cache) 