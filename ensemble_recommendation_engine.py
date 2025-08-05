#!/usr/bin/env python3
"""
Ensemble Recommendation Engine
Combines results from multiple engines to get the best possible recommendations
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from collections import defaultdict
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedContent, ContentAnalysis, User
from redis_utils import redis_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EnsembleRecommendationRequest:
    """Ensemble recommendation request format"""
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    user_interests: str = ""
    project_id: Optional[int] = None
    max_recommendations: int = 10
    engines_to_use: List[str] = None  # ['fast', 'context', 'smart', 'enhanced']
    ensemble_method: str = 'weighted_voting'  # 'weighted_voting', 'rank_fusion', 'score_aggregation'
    diversity_weight: float = 0.3
    quality_threshold: int = 6
    include_global_content: bool = True
    cache_duration: int = 1800  # 30 minutes

@dataclass
class EnsembleRecommendationResult:
    """Ensemble recommendation result format"""
    id: int
    title: str
    url: str
    score: float
    reason: str
    content_type: str
    difficulty: str
    technologies: List[str]
    key_concepts: List[str]
    quality_score: float
    engine_used: str
    confidence: float
    metadata: Dict[str, Any]
    ensemble_score: float = 0.0
    engine_votes: Dict[str, float] = None
    cached: bool = False

class EnsembleRecommendationEngine:
    """Ensemble recommendation engine that combines multiple engines"""
    
    def __init__(self):
        self.engines = {}
        self.engine_weights = {
            'fast': 0.2,      # Fast but basic
            'context': 0.3,   # Good balance
            'smart': 0.25,    # AI-powered
            'enhanced': 0.25  # Advanced features
        }
        self._init_engines()
        logger.info("Ensemble Recommendation Engine initialized")
    
    def _init_engines(self):
        """Initialize available engines"""
        try:
            # Import unified orchestrator
            from unified_recommendation_orchestrator import get_unified_orchestrator
            self.engines['unified'] = get_unified_orchestrator()
            logger.info("Unified orchestrator loaded")
        except Exception as e:
            logger.warning(f"Unified orchestrator not available: {e}")
        
        try:
            # Import standalone engines
            from unified_recommendation_engine import UnifiedRecommendationEngine
            self.engines['unified_standalone'] = UnifiedRecommendationEngine()
            logger.info("Unified standalone engine loaded")
        except Exception as e:
            logger.warning(f"Unified standalone engine not available: {e}")
        
        try:
            from smart_recommendation_engine import SmartRecommendationEngine
            self.engines['smart'] = SmartRecommendationEngine()
            logger.info("Smart engine loaded")
        except Exception as e:
            logger.warning(f"Smart engine not available: {e}")
        
        try:
            from enhanced_recommendation_engine import EnhancedRecommendationEngine
            self.engines['enhanced'] = EnhancedRecommendationEngine()
            logger.info("Enhanced engine loaded")
        except Exception as e:
            logger.warning(f"Enhanced engine not available: {e}")
        
        logger.info(f"Total engines loaded: {len(self.engines)}")
    
    def get_ensemble_recommendations(self, request: EnsembleRecommendationRequest) -> List[EnsembleRecommendationResult]:
        """Get ensemble recommendations from multiple engines"""
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Cache hit for ensemble recommendations")
                return cached_result
            
            # Determine which engines to use
            engines_to_use = request.engines_to_use or list(self.engines.keys())
            available_engines = [eng for eng in engines_to_use if eng in self.engines]
            
            if not available_engines:
                logger.warning("No engines available for ensemble")
                return []
            
            logger.info(f"Using engines: {available_engines}")
            
            # Get recommendations from each engine
            engine_results = {}
            for engine_name in available_engines:
                try:
                    engine_results[engine_name] = self._get_engine_recommendations(
                        engine_name, request
                    )
                    logger.info(f"Engine {engine_name} returned {len(engine_results[engine_name])} results")
                except Exception as e:
                    logger.error(f"Error getting recommendations from {engine_name}: {e}")
                    engine_results[engine_name] = []
            
            # Combine results using ensemble method
            ensemble_results = self._combine_results(engine_results, request)
            
            # Cache results
            self._cache_result(cache_key, ensemble_results, request.cache_duration)
            
            # Log performance
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Ensemble recommendations generated in {response_time:.2f}ms using {len(available_engines)} engines")
            
            return ensemble_results
            
        except Exception as e:
            logger.error(f"Error in ensemble engine: {e}")
            return []
    
    def _get_engine_recommendations(self, engine_name: str, request: EnsembleRecommendationRequest) -> List[Dict]:
        """Get recommendations from a specific engine"""
        try:
            engine = self.engines[engine_name]
            
            if engine_name == 'unified':
                # Use unified orchestrator with different engine preferences
                from unified_recommendation_orchestrator import UnifiedRecommendationRequest
                unified_request = UnifiedRecommendationRequest(
                    user_id=request.user_id,
                    title=request.title,
                    description=request.description,
                    technologies=request.technologies,
                    user_interests=request.user_interests,
                    project_id=request.project_id,
                    max_recommendations=request.max_recommendations * 2,  # Get more for ensemble
                    engine_preference='auto',
                    diversity_weight=request.diversity_weight,
                    quality_threshold=request.quality_threshold,
                    include_global_content=request.include_global_content
                )
                results = engine.get_recommendations(unified_request)
                return [asdict(result) for result in results]
            
            elif engine_name == 'unified_standalone':
                # Use standalone unified engine
                results = engine.get_recommendations(
                    user_id=request.user_id,
                    title=request.title,
                    description=request.description,
                    technologies=request.technologies,
                    max_recommendations=request.max_recommendations * 2
                )
                return results.get('recommendations', [])
            
            elif engine_name == 'smart':
                # Use smart engine
                results = engine.get_smart_recommendations(
                    user_id=request.user_id,
                    title=request.title,
                    description=request.description,
                    technologies=request.technologies,
                    max_recommendations=request.max_recommendations * 2
                )
                return results.get('recommendations', [])
            
            elif engine_name == 'enhanced':
                # Use enhanced engine
                results = engine.get_enhanced_recommendations(
                    user_id=request.user_id,
                    title=request.title,
                    description=request.description,
                    technologies=request.technologies,
                    max_recommendations=request.max_recommendations * 2
                )
                return results.get('recommendations', [])
            
            else:
                logger.warning(f"Unknown engine: {engine_name}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting recommendations from {engine_name}: {e}")
            return []
    
    def _combine_results(self, engine_results: Dict[str, List[Dict]], request: EnsembleRecommendationRequest) -> List[EnsembleRecommendationResult]:
        """Combine results from multiple engines"""
        if request.ensemble_method == 'weighted_voting':
            return self._weighted_voting_ensemble(engine_results, request)
        elif request.ensemble_method == 'rank_fusion':
            return self._rank_fusion_ensemble(engine_results, request)
        elif request.ensemble_method == 'score_aggregation':
            return self._score_aggregation_ensemble(engine_results, request)
        else:
            return self._weighted_voting_ensemble(engine_results, request)
    
    def _weighted_voting_ensemble(self, engine_results: Dict[str, List[Dict]], request: EnsembleRecommendationRequest) -> List[EnsembleRecommendationResult]:
        """Combine results using weighted voting"""
        # Create content ID to engine votes mapping
        content_votes = defaultdict(lambda: {
            'votes': defaultdict(float),
            'content': None,
            'total_score': 0.0,
            'vote_count': 0
        })
        
        # Collect votes from each engine
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for i, result in enumerate(results):
                content_id = result.get('id')
                if not content_id:
                    continue
                
                # Calculate vote based on rank and score
                rank_score = 1.0 / (i + 1)  # Higher rank = higher score
                score = result.get('score', 0) / 100.0  # Normalize score
                vote = (rank_score * 0.6 + score * 0.4) * weight
                
                content_votes[content_id]['votes'][engine_name] = vote
                content_votes[content_id]['total_score'] += vote
                content_votes[content_id]['vote_count'] += 1
                content_votes[content_id]['content'] = result
        
        # Convert to ensemble results
        ensemble_results = []
        for content_id, vote_data in content_votes.items():
            if vote_data['content']:
                content = vote_data['content']
                
                # Calculate ensemble score
                ensemble_score = vote_data['total_score'] / max(vote_data['vote_count'], 1)
                
                # Generate ensemble reason
                engine_names = list(vote_data['votes'].keys())
                reason = f"Recommended by {len(engine_names)} engines: {', '.join(engine_names)}. "
                reason += content.get('reason', 'High-quality content')
                
                ensemble_result = EnsembleRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=content.get('score', 0),
                    reason=reason,
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 7),
                    engine_used='Ensemble',
                    confidence=ensemble_score,
                    metadata=content.get('metadata', {}),
                    ensemble_score=ensemble_score,
                    engine_votes=dict(vote_data['votes'])
                )
                
                ensemble_results.append(ensemble_result)
        
        # Sort by ensemble score and limit
        ensemble_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        return ensemble_results[:request.max_recommendations]
    
    def _rank_fusion_ensemble(self, engine_results: Dict[str, List[Dict]], request: EnsembleRecommendationRequest) -> List[EnsembleRecommendationResult]:
        """Combine results using rank fusion"""
        # Create content ID to rank mapping
        content_ranks = defaultdict(list)
        
        # Collect ranks from each engine
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for i, result in enumerate(results):
                content_id = result.get('id')
                if content_id:
                    content_ranks[content_id].append({
                        'rank': i + 1,
                        'weight': weight,
                        'content': result
                    })
        
        # Calculate fused scores
        fused_results = []
        for content_id, ranks in content_ranks.items():
            if ranks:
                content = ranks[0]['content']  # Use first occurrence
                
                # Calculate fused score (lower rank = higher score)
                total_weight = sum(rank['weight'] for rank in ranks)
                fused_score = sum(rank['weight'] / rank['rank'] for rank in ranks) / total_weight
                
                # Generate reason
                engine_names = [f"#{rank['rank']}" for rank in ranks]
                reason = f"Ranked highly by multiple engines. "
                reason += content.get('reason', 'High-quality content')
                
                ensemble_result = EnsembleRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=content.get('score', 0),
                    reason=reason,
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 7),
                    engine_used='Ensemble',
                    confidence=fused_score,
                    metadata=content.get('metadata', {}),
                    ensemble_score=fused_score,
                    engine_votes={f"rank_{i+1}": rank['weight'] for i, rank in enumerate(ranks)}
                )
                
                fused_results.append(ensemble_result)
        
        # Sort by fused score and limit
        fused_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        return fused_results[:request.max_recommendations]
    
    def _score_aggregation_ensemble(self, engine_results: Dict[str, List[Dict]], request: EnsembleRecommendationRequest) -> List[EnsembleRecommendationResult]:
        """Combine results using score aggregation"""
        # Create content ID to scores mapping
        content_scores = defaultdict(list)
        
        # Collect scores from each engine
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for result in results:
                content_id = result.get('id')
                if content_id:
                    score = result.get('score', 0) / 100.0  # Normalize score
                    content_scores[content_id].append({
                        'score': score * weight,
                        'weight': weight,
                        'content': result
                    })
        
        # Calculate aggregated scores
        aggregated_results = []
        for content_id, scores in content_scores.items():
            if scores:
                content = scores[0]['content']  # Use first occurrence
                
                # Calculate aggregated score
                total_weight = sum(score['weight'] for score in scores)
                aggregated_score = sum(score['score'] for score in scores) / total_weight
                
                # Generate reason
                engine_names = [f"{score['score']:.2f}" for score in scores]
                reason = f"High scores from multiple engines. "
                reason += content.get('reason', 'High-quality content')
                
                ensemble_result = EnsembleRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=content.get('score', 0),
                    reason=reason,
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 7),
                    engine_used='Ensemble',
                    confidence=aggregated_score,
                    metadata=content.get('metadata', {}),
                    ensemble_score=aggregated_score,
                    engine_votes={f"score_{i+1}": score['score'] for i, score in enumerate(scores)}
                )
                
                aggregated_results.append(ensemble_result)
        
        # Sort by aggregated score and limit
        aggregated_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        return aggregated_results[:request.max_recommendations]
    
    def _generate_cache_key(self, request: EnsembleRecommendationRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        
        # Create unique string from request
        request_str = f"ensemble:{request.user_id}:{request.title}:{request.description}:{request.technologies}:{request.max_recommendations}:{','.join(request.engines_to_use or [])}:{request.ensemble_method}"
        
        # Generate hash
        return f"ensemble_recommendations:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[EnsembleRecommendationResult]]:
        """Get cached result"""
        try:
            cached_data = redis_cache.get_cache(cache_key)
            if cached_data:
                # Convert back to EnsembleRecommendationResult objects
                results = []
                for item in cached_data:
                    result = EnsembleRecommendationResult(**item)
                    result.cached = True
                    results.append(result)
                return results
            return None
        except Exception as e:
            logger.error(f"Error getting cached result: {e}")
            return None
    
    def _cache_result(self, cache_key: str, results: List[EnsembleRecommendationResult], ttl: int):
        """Cache result"""
        try:
            # Convert to serializable format
            cache_data = [asdict(result) for result in results]
            redis_cache.set_cache(cache_key, cache_data, ttl)
        except Exception as e:
            logger.error(f"Error caching result: {e}")

# Global ensemble engine instance
_ensemble_engine_instance = None

def get_ensemble_engine() -> EnsembleRecommendationEngine:
    """Get global ensemble engine instance"""
    global _ensemble_engine_instance
    if _ensemble_engine_instance is None:
        _ensemble_engine_instance = EnsembleRecommendationEngine()
    return _ensemble_engine_instance

def get_ensemble_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Main function to get ensemble recommendations"""
    try:
        # Create request object
        request = EnsembleRecommendationRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            user_interests=request_data.get('user_interests', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engines_to_use=request_data.get('engines_to_use', ['unified', 'smart', 'enhanced']),
            ensemble_method=request_data.get('ensemble_method', 'weighted_voting'),
            diversity_weight=request_data.get('diversity_weight', 0.3),
            quality_threshold=request_data.get('quality_threshold', 6),
            include_global_content=request_data.get('include_global_content', True)
        )
        
        # Get ensemble engine
        ensemble_engine = get_ensemble_engine()
        
        # Get recommendations
        results = ensemble_engine.get_ensemble_recommendations(request)
        
        # Convert to dictionary format for API response
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error getting ensemble recommendations: {e}")
        return []

if __name__ == "__main__":
    # Test the ensemble engine
    test_request = EnsembleRecommendationRequest(
        user_id=1,
        title="React Learning Project",
        description="Building a modern web application with React",
        technologies="JavaScript, React, Node.js",
        user_interests="Frontend development, state management",
        max_recommendations=5,
        engines_to_use=['unified', 'smart'],
        ensemble_method='weighted_voting'
    )
    
    ensemble_engine = EnsembleRecommendationEngine()
    results = ensemble_engine.get_ensemble_recommendations(test_request)
    
    print(f"Generated {len(results)} ensemble recommendations:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Ensemble Score: {result.ensemble_score:.3f}")
        print(f"   Engine Votes: {result.engine_votes}")
        print(f"   Reason: {result.reason}") 