#!/usr/bin/env python3
"""
Ensemble Recommendation Engine - OPTIMIZED Version
Combines results from multiple engines for better recommendations
"""

import time
import logging

from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

# Add project root to path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_utils import redis_cache
from gemini_utils import GeminiAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class EnsembleRequest:
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    project_id: int = None
    max_recommendations: int = 10
    engines: List[str] = None  # ['unified', 'smart', 'enhanced']

@dataclass
class EnsembleResult:
    id: int
    title: str
    url: str
    score: float
    reason: str
    ensemble_score: float
    engine_votes: Dict[str, float]
    technologies: List[str] = None
    content_type: str = "article"
    difficulty: str = "intermediate"

class OptimizedEnsembleEngine:
    """Optimized ensemble engine with caching, parallel processing, and quality preservation"""
    
    def __init__(self):
        self.engine_weights = {
            'smart': 0.6,       # Heavier weight for smart NLP
            'fast_gemini': 0.4  # Weight for Gemini AI
        }
        self.cache_duration = 900  # 15 minutes
        self.max_parallel_engines = 2  # Only two engines
        self.timeout_seconds = 30
        self.quality_threshold = 0.4
        self.min_recommendations = 5
        logger.info("AI/NLP Ensemble Engine initialized with Smart and FastGemini only")
    
    def get_ensemble_recommendations(self, request: EnsembleRequest) -> List[EnsembleResult]:
        """Get ensemble recommendations with AI/NLP engines only"""
        start_time = time.time()
        try:
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Cache hit for ensemble recommendations")
                return cached_result

            # Only use smart and fast_gemini engines
            engines_to_use = ['smart', 'fast_gemini']
            available_engines = self._get_available_engines(engines_to_use)
            if not available_engines:
                logger.warning("No AI/NLP engines available")
                return []
            logger.info(f"Using AI/NLP engines: {available_engines}")
            engine_results = self._get_engine_results_quality_optimized(available_engines, request)
            ensemble_results = self._combine_results_quality_optimized(engine_results, request)
            self._cache_result(cache_key, ensemble_results)
            response_time = (time.time() - start_time) * 1000
            logger.info(f"AI/NLP ensemble completed in {response_time:.2f}ms")
            return ensemble_results
        except Exception as e:
            logger.error(f"Ensemble error: {e}")
            return []
    
    def _generate_cache_key(self, request: EnsembleRequest) -> str:
        """Generate cache key for ensemble request"""
        request_data = {
            'user_id': request.user_id,
            'title': request.title,
            'description': request.description,
            'technologies': request.technologies,
            'project_id': request.project_id,
            'max_recommendations': request.max_recommendations,
            'engines': sorted(request.engines or ['unified'])
        }
        request_hash = hashlib.md5(json.dumps(request_data, sort_keys=True).encode()).hexdigest()
        return f"ensemble_recommendations:{request_hash}"
    
    def _get_cached_result(self, cache_key: str) -> List[EnsembleResult]:
        """Get cached ensemble result"""
        try:
            cached_data = redis_cache.get_cache(cache_key)
            if cached_data:
                # Convert cached dict back to EnsembleResult objects
                return [EnsembleResult(**result) for result in cached_data]
            return None
        except Exception as e:
            logger.warning(f"Error getting cached result: {e}")
            return None
    
    def _cache_result(self, cache_key: str, results: List[EnsembleResult]):
        """Cache ensemble result"""
        try:
            # Convert to dict for caching
            cache_data = [asdict(result) for result in results]
            redis_cache.set_cache(cache_key, cache_data, self.cache_duration)
        except Exception as e:
            logger.warning(f"Error caching result: {e}")
    
    def _get_available_engines(self, requested_engines: List[str]) -> List[str]:
        """Return only available AI/NLP engines"""
        available = []
        for eng in requested_engines:
            if eng == 'smart':
                try:
                    from ai_recommendation_engine import SmartRecommendationEngine
                    available.append('smart')
                except Exception:
                    pass
            elif eng == 'fast_gemini':
                try:
                    from fast_gemini_engine import fast_gemini_engine
                    available.append('fast_gemini')
                except Exception:
                    pass
        return available
    
    def _get_engine_results_quality_optimized(self, engines: List[str], request: EnsembleRequest) -> Dict[str, List[Dict]]:
        """Get results from only smart and fast_gemini engines"""
        engine_results = {}
        if 'smart' in engines:
            try:
                engine_results['smart'] = self._get_smart_results(request)
            except Exception as e:
                logger.error(f"Error with smart engine: {e}")
                engine_results['smart'] = []
        if 'fast_gemini' in engines:
            try:
                engine_results['fast_gemini'] = self._get_fast_gemini_results(request)
            except Exception as e:
                logger.error(f"Error with fast_gemini engine: {e}")
                engine_results['fast_gemini'] = []
        return engine_results
    
    def _get_single_engine_results(self, engine_name: str, request: EnsembleRequest) -> List[Dict]:
        """Get results from a single AI/NLP engine"""
        try:
            if engine_name == 'smart':
                return self._get_smart_results(request)
            elif engine_name == 'fast_gemini':
                return self._get_fast_gemini_results(request)
            else:
                logger.warning(f"Unknown engine: {engine_name}")
                return []
        except Exception as e:
            logger.error(f"Error getting {engine_name} results: {e}")
            return []
    
    def _get_smart_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from SmartRecommendationEngine (ai_recommendation_engine.py)"""
        try:
            from ai_recommendation_engine import SmartRecommendationEngine
            engine = SmartRecommendationEngine()
            project_context = {
                'title': request.title,
                'description': request.description,
                'technologies': request.technologies
            }
            results = engine.get_smart_recommendations(
                bookmarks=[],  # Let engine fetch bookmarks internally if needed
                project_context=project_context,
                max_recommendations=request.max_recommendations * 2
            )
            return results
        except Exception as e:
            logger.warning(f"SmartRecommendationEngine not available: {e}")
            return []
    
    def _get_fast_gemini_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from Fast Gemini engine with optimized database query"""
        try:
            from fast_gemini_engine import fast_gemini_engine
            from models import SavedContent
            from app import app
            
            with app.app_context():
                # Optimized query with limits and specific fields to prevent timeouts
                user_bookmarks = SavedContent.query.filter_by(
                    user_id=request.user_id
                ).with_entities(
                    SavedContent.id,
                    SavedContent.title,
                    SavedContent.url,
                    SavedContent.extracted_text,
                    SavedContent.quality_score
                ).limit(100).all()  # Limit to prevent large result sets
                
                if not user_bookmarks:
                    logger.info(f"No bookmarks found for user {request.user_id}")
                    return []
                
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
                
                user_input = {
                    'title': request.title,
                    'description': request.description,
                    'technologies': request.technologies,
                    'user_id': request.user_id
                }
                
                result = fast_gemini_engine.get_fast_gemini_recommendations(
                    bookmarks_data, user_input, request.max_recommendations * 2
                )
                
                # Filter out bad recommendations using GeminiAnalyzer utility
                try:
                    filtered = GeminiAnalyzer().filter_bad_recommendations(result.get('recommendations', []))
                    return filtered
                except Exception as filter_error:
                    logger.warning(f"GeminiAnalyzer filtering failed, returning unfiltered results: {filter_error}")
                    return result.get('recommendations', [])
                    
        except Exception as e:
            logger.warning(f"FastGeminiEngine not available: {e}")
            return []
    
    def _check_quality_sufficient(self, results: List[Dict]) -> bool:
        """Check if results have sufficient quality"""
        if not results:
            return False
        
        # Check average score
        scores = [result.get('score', 0) for result in results]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Check if we have enough high-quality results
        high_quality_count = sum(1 for score in scores if score >= 70)
        
        return avg_score >= 60 and high_quality_count >= 3
    
    def _combine_results_quality_optimized(self, engine_results: Dict[str, List[Dict]], request: EnsembleRequest) -> List[EnsembleResult]:
        """Combine results using quality-optimized weighted voting"""
        # Track votes for each content item
        content_votes = defaultdict(lambda: {
            'votes': defaultdict(float),
            'content': None,
            'total_score': 0.0,
            'quality_score': 0.0,
            'engine_count': 0
        })
        
        # Collect votes from each engine with quality weighting
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for i, result in enumerate(results):
                content_id = result.get('id')
                if not content_id:
                    continue
                
                # Enhanced vote calculation with quality focus
                rank_score = 1.0 / (i + 1)  # Higher rank = higher score
                score = result.get('score', 0) / 100.0  # Normalize score
                
                # Quality bonus for high-scoring content
                quality_bonus = 1.0 if score >= 0.8 else 0.5 if score >= 0.6 else 0.2
                
                # Calculate vote with quality weighting
                vote = (rank_score * 0.4 + score * 0.6) * weight * quality_bonus
                
                content_votes[content_id]['votes'][engine_name] = vote
                content_votes[content_id]['total_score'] += vote
                content_votes[content_id]['quality_score'] += score
                content_votes[content_id]['engine_count'] += 1
                content_votes[content_id]['content'] = result
        
        # Convert to ensemble results with quality filtering
        ensemble_results = []
        for content_id, vote_data in content_votes.items():
            content = vote_data['content']
            if not content:
                continue
            
            # Calculate ensemble score with quality consideration
            avg_quality = vote_data['quality_score'] / vote_data['engine_count'] if vote_data['engine_count'] > 0 else 0
            ensemble_score = vote_data['total_score'] * (1 + avg_quality * 0.3)  # Quality boost
            
            # Filter by quality threshold
            if avg_quality < self.quality_threshold and vote_data['engine_count'] < 2:
                continue  # Skip low-quality content unless multiple engines agree
            
            # Filter out very low quality content more strictly
            if avg_quality < 0.2 and vote_data['engine_count'] < 2:
                continue  # Skip very low-quality content
            
            # Filter out content with generic reasons
            reason = content.get('reason', '')
            if reason and any(generic in reason.lower() for generic in ['helpful', 'useful', 'relevant']):
                if avg_quality < 0.5:  # Only allow generic reasons for high-quality content
                    continue
            
            # Create ensemble result
            ensemble_result = EnsembleResult(
                id=content.get('id'),
                title=content.get('title', ''),
                url=content.get('url', ''),
                score=content.get('score', 0),
                reason=content.get('reason', ''),
                ensemble_score=ensemble_score,
                engine_votes=dict(vote_data['votes']),
                technologies=content.get('technologies', []),
                content_type=content.get('content_type', 'article'),
                difficulty=content.get('difficulty', 'intermediate')
            )
            ensemble_results.append(ensemble_result)
        
        # Sort by ensemble score and limit results
        ensemble_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        
        # Apply quality filters and return final results
        final_recommendations = self._apply_quality_filters(ensemble_results)
        
        return final_recommendations[:request.max_recommendations]

    def _apply_quality_filters(self, recommendations: List[EnsembleResult]) -> List[EnsembleResult]:
        """Apply quality filters to ensure only high-quality recommendations are returned"""
        filtered_recommendations = []
        
        for rec in recommendations:
            # Skip very low quality recommendations
            if rec.score < 20:
                continue
                
            # Skip generic content (titles that are too generic)
            title = rec.title.lower()
            if any(generic in title for generic in [
                'javascript tutorial', 'python tutorial', 'html tutorial', 'css tutorial',
                'programming basics', 'coding tutorial', 'learn to code'
            ]):
                # Only include if it has very high score
                if rec.score < 40:
                    continue
            
            # Skip dictionary or reference content unless highly relevant
            if any(ref in title for ref in ['dictionary', 'reference', 'glossary']):
                if rec.score < 35:
                    continue
            
            # Boost user's own content (if we have that attribute)
            if hasattr(rec, 'is_user_content') and rec.is_user_content:
                rec.score = rec.score * 1.3  # 30% boost
                if hasattr(rec, 'confidence'):
                    rec.confidence = min(1.0, rec.confidence * 1.2)
            
            filtered_recommendations.append(rec)
        
        # Sort by score
        filtered_recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return filtered_recommendations

    def _generate_reason(self, content, request_techs, similarity, tech_overlap):
        matched_techs = [t for t in content.get('technologies', []) if t in request_techs]
        if tech_overlap > 0 and matched_techs:
            return f"Recommended because it covers: {', '.join(matched_techs)}. Highly relevant to your request."
        elif similarity > 0.7:
            return "Semantically similar to your request."
        else:
            return "High-quality, relevant content."

# Global instance
_ensemble_engine = None

def get_ensemble_engine() -> OptimizedEnsembleEngine:
    """Get singleton ensemble engine instance"""
    global _ensemble_engine
    if _ensemble_engine is None:
        _ensemble_engine = OptimizedEnsembleEngine()
    return _ensemble_engine

def get_ensemble_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get ensemble recommendations (optimized)"""
    try:
        # Create request object
        request = EnsembleRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engines=request_data.get('engines', ['unified'])
        )
        
        # Get ensemble engine
        engine = get_ensemble_engine()
        
        # Get recommendations
        results = engine.get_ensemble_recommendations(request)
        
        # Convert to dict format
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in get_ensemble_recommendations: {e}")
        return [] 