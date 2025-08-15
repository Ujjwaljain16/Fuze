#!/usr/bin/env python3
"""
Fast Ensemble Recommendation Engine
Ultra-fast ensemble engine that prioritizes speed over accuracy
"""

import time
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib
import json

# Add project root to path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_utils import redis_cache

logger = logging.getLogger(__name__)

@dataclass
class FastEnsembleRequest:
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    project_id: int = None
    max_recommendations: int = 10
    engines: List[str] = None  # ['unified', 'fast']

@dataclass
class FastEnsembleResult:
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

class FastEnsembleEngine:
    """Ultra-fast ensemble engine optimized for speed"""
    
    def __init__(self):
        self.engine_weights = {
            'unified': 0.5,        # Balanced weight for unified
            'fast': 0.2,           # Light weight for fast engine
            'high_relevance': 0.3  # High weight for relevance engine
        }
        self.cache_duration = 900  # 15 minutes (shorter for speed)
        self.timeout_seconds = 10  # Very short timeout
        logger.info("Fast Ensemble Engine initialized")
    
    def get_fast_ensemble_recommendations(self, request: FastEnsembleRequest) -> List[FastEnsembleResult]:
        """Get ultra-fast ensemble recommendations"""
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Cache hit for fast ensemble recommendations")
                return cached_result
            
            # Use fast engines including high relevance
            engines_to_use = ['unified', 'high_relevance']  # Always include unified and high relevance
            if 'fast' in (request.engines or []):
                engines_to_use.append('fast')
            
            # Get results from engines
            engine_results = {}
            
            # Get unified results first (fastest)
            try:
                logger.info("Getting unified engine results (fastest)...")
                results = self._get_unified_results(request)
                engine_results['unified'] = results
                logger.info(f"Engine unified: {len(results)} results")
                
                # If we have enough results, skip other engines
                if len(results) >= request.max_recommendations:
                    logger.info("Unified engine provided sufficient results, skipping other engines")
                    engine_results = {'unified': results}
                    
            except Exception as e:
                logger.error(f"Error with unified engine: {e}")
                engine_results['unified'] = []
            
            # Get high relevance results (high priority for quality)
            if 'high_relevance' in engines_to_use:
                try:
                    logger.info("Getting high relevance engine results...")
                    results = self._get_high_relevance_results(request)
                    engine_results['high_relevance'] = results
                    logger.info(f"Engine high_relevance: {len(results)} results")
                except Exception as e:
                    logger.error(f"Error with high relevance engine: {e}")
                    engine_results['high_relevance'] = []
            
            # Only try fast engine if we still need more results
            if len(engine_results.get('unified', [])) + len(engine_results.get('high_relevance', [])) < request.max_recommendations and 'fast' in engines_to_use:
                try:
                    logger.info("Getting fast engine results...")
                    results = self._get_fast_results(request)
                    engine_results['fast'] = results
                    logger.info(f"Engine fast: {len(results)} results")
                except Exception as e:
                    logger.error(f"Error with fast engine: {e}")
                    engine_results['fast'] = []
            
            # Combine results
            ensemble_results = self._combine_results(engine_results, request)
            
            # Cache results
            self._cache_result(cache_key, ensemble_results)
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Fast ensemble completed in {response_time:.2f}ms")
            
            return ensemble_results
            
        except Exception as e:
            logger.error(f"Fast ensemble error: {e}")
            return []
    
    def _generate_cache_key(self, request: FastEnsembleRequest) -> str:
        """Generate cache key for fast ensemble request"""
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
        return f"fast_ensemble_recommendations:{request_hash}"
    
    def _get_cached_result(self, cache_key: str) -> List[FastEnsembleResult]:
        """Get cached fast ensemble result"""
        try:
            cached_data = redis_cache.get_cache(cache_key)
            if cached_data:
                return [FastEnsembleResult(**result) for result in cached_data]
            return None
        except Exception as e:
            logger.warning(f"Error getting cached result: {e}")
            return None
    
    def _cache_result(self, cache_key: str, results: List[FastEnsembleResult]):
        """Cache fast ensemble result"""
        try:
            cache_data = [asdict(result) for result in results]
            redis_cache.set_cache(cache_key, cache_data, self.cache_duration)
        except Exception as e:
            logger.warning(f"Error caching result: {e}")
    
    def _get_unified_results(self, request: FastEnsembleRequest) -> List[Dict]:
        """Get results from unified engine (ultra-fast)"""
        try:
            from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
            
            orchestrator = get_unified_orchestrator()
            unified_request = UnifiedRecommendationRequest(
                user_id=request.user_id,
                title=request.title,
                description=request.description,
                technologies=request.technologies,
                project_id=request.project_id,
                max_recommendations=request.max_recommendations,
                engine_preference='fast',  # Use fast engine preference
                cache_duration=600,  # 10 minutes cache
                quality_threshold=5  # Lower threshold for speed
            )
            
            results = orchestrator.get_recommendations(unified_request)
            return [asdict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting unified results: {e}")
            return []
    
    def _get_fast_results(self, request: FastEnsembleRequest) -> List[Dict]:
        """Get results from fast engine"""
        try:
            from fast_recommendation_engine import FastRecommendationEngine
            
            engine = FastRecommendationEngine()
            results = engine.get_fast_recommendations(
                user_id=request.user_id,
                use_cache=True
            )
            
            return results.get('recommendations', [])
            
        except Exception as e:
            logger.warning(f"Fast engine not available: {e}")
            return []
    
    def _get_high_relevance_results(self, request: FastEnsembleRequest) -> List[Dict]:
        """Get results from high relevance engine"""
        try:
            from high_relevance_engine import high_relevance_engine
            from models import SavedContent
            
            # Get database session
            session = get_db_session()
            if not session:
                logger.error("Could not get database session")
                return []
            
            # Get user's saved content dynamically
            # Get high-quality content from all users (dynamic, not hardcoded)
            all_content = session.query(SavedContent).filter(
                SavedContent.quality_score >= 5,  # Dynamic quality threshold
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).order_by(
                SavedContent.quality_score.desc(),
                SavedContent.saved_at.desc()
            ).limit(50).all()  # Further reduced limit for faster processing
            
            # Convert to format expected by high relevance engine (while still in app context)
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
                'title': request.title,
                'description': request.description,
                'technologies': request.technologies,
                'project_id': request.project_id
            }
            
            # Get high relevance recommendations
            results = high_relevance_engine.get_high_relevance_recommendations(
                bookmarks=bookmarks_data,
                user_input=user_input,
                max_recommendations=request.max_recommendations * 2  # Get more for ensemble
            )
            
            return results
                
        except Exception as e:
            logger.error(f"Error getting high relevance results: {e}")
            return []
    
    def _combine_results(self, engine_results: Dict[str, List[Dict]], request: FastEnsembleRequest) -> List[FastEnsembleResult]:
        """Combine results using simple weighted voting (optimized for speed)"""
        # Track votes for each content item
        content_votes = defaultdict(lambda: {
            'votes': defaultdict(float),
            'content': None,
            'total_score': 0.0
        })
        
        # Collect votes from each engine
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for i, result in enumerate(results):
                content_id = result.get('id')
                if not content_id:
                    continue
                
                # Simple vote calculation for speed
                score = result.get('score', 0) / 100.0  # Normalize score
                vote = score * weight
                
                content_votes[content_id]['votes'][engine_name] = vote
                content_votes[content_id]['total_score'] += vote
                content_votes[content_id]['content'] = result
        
        # Convert to ensemble results
        ensemble_results = []
        for content_id, vote_data in content_votes.items():
            content = vote_data['content']
            if not content:
                continue
            
            # Calculate ensemble score
            ensemble_score = vote_data['total_score']
            
            # Create ensemble result
            ensemble_result = FastEnsembleResult(
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
        return ensemble_results[:request.max_recommendations]

# Global instance
_fast_ensemble_engine = None

def get_fast_ensemble_engine() -> FastEnsembleEngine:
    """Get singleton fast ensemble engine instance"""
    global _fast_ensemble_engine
    if _fast_ensemble_engine is None:
        _fast_ensemble_engine = FastEnsembleEngine()
    return _fast_ensemble_engine

def get_fast_ensemble_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get fast ensemble recommendations"""
    try:
        # Create request object
        request = FastEnsembleRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engines=request_data.get('engines', ['unified'])
        )
        
        # Get fast ensemble engine
        engine = get_fast_ensemble_engine()
        
        # Get recommendations
        results = engine.get_fast_ensemble_recommendations(request)
        
        # Convert to dict format
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in get_fast_ensemble_recommendations: {e}")
        return [] 