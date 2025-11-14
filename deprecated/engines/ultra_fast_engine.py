#!/usr/bin/env python3
"""
Ultra Fast Recommendation Engine
Fastest possible recommendations without AI enhancement
"""
import time
from typing import List, Dict
from redis_utils import redis_cache
from sqlalchemy import text

class UltraFastEngine:
    """Ultra-fast recommendation engine for maximum speed"""
    
    def __init__(self):
        self.max_recommendations = 5
        self.cache_duration = 300  # 5 minutes
    
    def get_ultra_fast_recommendations(self, user_id, use_cache=True):
        """Get ultra-fast recommendations"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"ultra_fast_recommendations:{user_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        from app import app, db
        from models import SavedContent
        
        with app.app_context():
            # Ultra-fast query - get diverse high-quality content by category
            all_content = db.session.execute(text("""
                WITH content_categories AS (
                    SELECT 
                        id,
                        extracted_text,
                        quality_score,
                        user_id,
                        CASE 
                            WHEN LOWER(title) LIKE '%tutorial%' OR LOWER(title) LIKE '%guide%' OR LOWER(title) LIKE '%learn%' THEN 'tutorials'
                            WHEN LOWER(title) LIKE '%docs%' OR LOWER(title) LIKE '%documentation%' OR LOWER(title) LIKE '%api%' THEN 'documentation'
                            WHEN LOWER(title) LIKE '%project%' OR LOWER(title) LIKE '%github%' OR LOWER(title) LIKE '%repo%' THEN 'projects'
                            WHEN LOWER(title) LIKE '%leetcode%' THEN 'leetcode'
                            WHEN LOWER(title) LIKE '%interview%' OR LOWER(title) LIKE '%question%' THEN 'interviews'
                            ELSE 'other'
                        END as category
                    FROM saved_content 
                    WHERE quality_score >= 7
                    AND title NOT LIKE '%Test Bookmark%'
                    AND title NOT LIKE '%test bookmark%'
                ),
                ranked_content AS (
                    SELECT 
                        *,
                        ROW_NUMBER() OVER (PARTITION BY category ORDER BY quality_score DESC, RANDOM()) as rank_in_category
                    FROM content_categories
                )
                SELECT id, extracted_text, quality_score, user_id
                FROM ranked_content 
                WHERE rank_in_category <= 2
                ORDER BY RANDOM()
                LIMIT 15
            """), {'user_id': user_id}).fetchall()
            
            if not all_content:
                return {
                    'recommendations': [],
                    'cached': False,
                    'computation_time_ms': 0,
                    'message': 'No high-quality content available'
                }
            
            # Minimal processing - just format the results
            recommendations = []
            for content in all_content:
                # Get the actual title from the database
                content_obj = SavedContent.query.get(content[0])
                title = content_obj.title if content_obj else "No title available"
                
                recommendations.append({
                    'id': content[0],
                    'title': title,
                    'content': content[1],
                    'similarity_score': content[2] / 10.0,  # Normalize quality score
                    'quality_score': content[2],
                    'user_id': content[3],
                    'reason': 'High-quality content from your saved bookmarks'
                })
            
            # Take top 5 for speed
            recommendations = recommendations[:self.max_recommendations]
            
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': recommendations,
                'cached': False,
                'computation_time_ms': computation_time,
                'total_candidates': len(all_content),
                'context_analysis': {
                    'input_analysis': {
                        'title': 'Ultra-Fast Recommendations',
                        'technologies': [],
                        'content_type': 'ultra_fast',
                        'difficulty': 'adaptive',
                        'intent': 'learning'
                    },
                    'processing_stats': {
                        'total_bookmarks_analyzed': len(recommendations),
                        'relevant_bookmarks_found': len(recommendations),
                        'total_recommendations': len(recommendations),
                        'gemini_enhanced': False,
                        'engine': 'ultra_fast',
                        'response_type': 'optimized',
                        'total_time': (time.time() - start_time)
                    }
                }
            }
            
            # Cache the result
            if use_cache:
                cache_key = f"ultra_fast_recommendations:{user_id}"
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result
    
    def get_ultra_fast_project_recommendations(self, user_id, project_id, use_cache=True):
        """Get ultra-fast project recommendations"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"ultra_fast_project_recommendations:{user_id}:{project_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result is not None:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        from app import app, db
        from models import SavedContent
        
        with app.app_context():
            # Same ultra-fast query as general recommendations
            all_content = db.session.execute(text("""
                WITH content_categories AS (
                    SELECT 
                        id,
                        extracted_text,
                        quality_score,
                        user_id,
                        CASE 
                            WHEN LOWER(title) LIKE '%tutorial%' OR LOWER(title) LIKE '%guide%' OR LOWER(title) LIKE '%learn%' THEN 'tutorials'
                            WHEN LOWER(title) LIKE '%docs%' OR LOWER(title) LIKE '%documentation%' OR LOWER(title) LIKE '%api%' THEN 'documentation'
                            WHEN LOWER(title) LIKE '%project%' OR LOWER(title) LIKE '%github%' OR LOWER(title) LIKE '%repo%' THEN 'projects'
                            WHEN LOWER(title) LIKE '%leetcode%' THEN 'leetcode'
                            WHEN LOWER(title) LIKE '%interview%' OR LOWER(title) LIKE '%question%' THEN 'interviews'
                            ELSE 'other'
                        END as category
                    FROM saved_content 
                    WHERE quality_score >= 7
                    AND title NOT LIKE '%Test Bookmark%'
                    AND title NOT LIKE '%test bookmark%'
                ),
                ranked_content AS (
                    SELECT 
                        *,
                        ROW_NUMBER() OVER (PARTITION BY category ORDER BY quality_score DESC, RANDOM()) as rank_in_category
                    FROM content_categories
                )
                SELECT id, extracted_text, quality_score, user_id
                FROM ranked_content 
                WHERE rank_in_category <= 2
                ORDER BY RANDOM()
                LIMIT 15
            """), {'user_id': user_id}).fetchall()
            
            if not all_content:
                return {
                    'recommendations': [],
                    'cached': False,
                    'computation_time_ms': 0,
                    'message': 'No high-quality content available'
                }
            
            # Minimal processing
            recommendations = []
            for content in all_content:
                # Get the actual title from the database
                content_obj = SavedContent.query.get(content[0])
                title = content_obj.title if content_obj else "No title available"
                
                recommendations.append({
                    'id': content[0],
                    'title': title,
                    'content': content[1],
                    'similarity_score': content[2] / 10.0,
                    'quality_score': content[2],
                    'user_id': content[3],
                    'reason': 'High-quality content from your saved bookmarks'
                })
            
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
                cache_key = f"ultra_fast_project_recommendations:{user_id}:{project_id}"
                redis_cache.set_cache(cache_key, result, self.cache_duration)
            
            return result

# Global instance
ultra_fast_engine = UltraFastEngine()

def get_ultra_fast_recommendations(user_id, use_cache=True):
    """Get ultra-fast recommendations"""
    return ultra_fast_engine.get_ultra_fast_recommendations(user_id, use_cache)

def get_ultra_fast_project_recommendations(user_id, project_id, use_cache=True):
    """Get ultra-fast project recommendations"""
    return ultra_fast_engine.get_ultra_fast_project_recommendations(user_id, project_id, use_cache) 