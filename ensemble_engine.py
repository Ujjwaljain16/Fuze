#!/usr/bin/env python3
"""
Ensemble Recommendation Engine - Simplified Version
Combines results from multiple engines for better recommendations
"""

import time
import logging
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

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

class EnsembleEngine:
    """Simplified ensemble engine"""
    
    def __init__(self):
        self.engine_weights = {
            'unified': 0.4,
            'smart': 0.3,
            'enhanced': 0.3
        }
        logger.info("Ensemble Engine initialized")
    
    def get_ensemble_recommendations(self, request: EnsembleRequest) -> List[EnsembleResult]:
        """Get ensemble recommendations"""
        start_time = time.time()
        
        try:
            # Get recommendations from each engine
            engine_results = {}
            engines_to_use = request.engines or ['unified']
            
            # Optimize: Use unified engine first and cache results
            if 'unified' in engines_to_use:
                try:
                    logger.info("Getting unified engine results (will be cached)...")
                    results = self._get_engine_results('unified', request)
                    engine_results['unified'] = results
                    logger.info(f"Engine unified: {len(results)} results")
                    
                    # Don't skip other engines - let's test all engines
                    logger.info(f"Unified engine provided {len(results)} results, continuing with other engines")
                except Exception as e:
                    logger.error(f"Error with unified engine: {e}")
                    engine_results['unified'] = []
            
            # Only call other engines if unified didn't provide enough results
            for engine_name in engines_to_use:
                if engine_name == 'unified':
                    continue  # Already processed
                    
                try:
                    logger.info(f"Getting {engine_name} engine results...")
                    results = self._get_engine_results(engine_name, request)
                    engine_results[engine_name] = results
                    logger.info(f"Engine {engine_name}: {len(results)} results")
                except Exception as e:
                    logger.error(f"Error with {engine_name}: {e}")
                    engine_results[engine_name] = []
            
            # Combine results
            ensemble_results = self._combine_results(engine_results, request)
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Ensemble completed in {response_time:.2f}ms")
            
            return ensemble_results
            
        except Exception as e:
            logger.error(f"Ensemble error: {e}")
            return []
    
    def _get_engine_results(self, engine_name: str, request: EnsembleRequest) -> List[Dict]:
        """Get results from specific engine"""
        try:
            if engine_name == 'unified':
                # Use unified orchestrator
                from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
                
                orchestrator = get_unified_orchestrator()
                unified_request = UnifiedRecommendationRequest(
                    user_id=request.user_id,
                    title=request.title,
                    description=request.description,
                    technologies=request.technologies,
                    project_id=request.project_id,
                    max_recommendations=request.max_recommendations * 2
                )
                
                results = orchestrator.get_recommendations(unified_request)
                return [asdict(result) for result in results]
            
            elif engine_name == 'smart':
                # Use smart engine - handle import error gracefully
                try:
                    from smart_recommendation_engine import SmartRecommendationEngine
                    
                    engine = SmartRecommendationEngine(request.user_id)  # Pass user_id to constructor
                    # Smart engine expects project_info dict, not individual parameters
                    project_info = {
                        'title': request.title,
                        'description': request.description,
                        'technologies': request.technologies,
                        'learning_goals': request.description  # Use description as learning goals
                    }
                    results = engine.get_smart_recommendations(
                        project_info=project_info,
                        limit=request.max_recommendations * 2
                    )
                    # Convert SmartRecommendation objects to dict format
                    if results:
                        return [
                            {
                                'id': rec.bookmark_id,
                                'title': rec.title,
                                'url': rec.url,
                                'score': rec.match_score,
                                'reason': rec.reasoning,
                                'content_type': rec.content_type,
                                'difficulty': rec.difficulty,
                                'technologies': rec.technologies,
                                'key_concepts': rec.key_concepts
                            }
                            for rec in results
                        ]
                    return []
                except Exception as e:
                    logger.warning(f"Smart engine not available: {e}")
                    return []
            
            elif engine_name == 'enhanced':
                # Use enhanced engine
                from enhanced_recommendation_engine import get_enhanced_recommendations
                
                results = get_enhanced_recommendations(
                    user_id=request.user_id,
                    request_data={
                        'title': request.title,
                        'description': request.description,
                        'technologies': request.technologies,
                        'project_id': request.project_id
                    },
                    limit=request.max_recommendations * 2
                )
                return results
            
            else:
                logger.warning(f"Unknown engine: {engine_name}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting {engine_name} results: {e}")
            return []
    
    def _combine_results(self, engine_results: Dict[str, List[Dict]], request: EnsembleRequest) -> List[EnsembleResult]:
        """Combine results using weighted voting"""
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
                
                # Calculate vote based on rank and score
                rank_score = 1.0 / (i + 1)  # Higher rank = higher score
                score = result.get('score', 0) / 100.0  # Normalize score
                vote = (rank_score * 0.6 + score * 0.4) * weight
                
                content_votes[content_id]['votes'][engine_name] = vote
                content_votes[content_id]['total_score'] += vote
                content_votes[content_id]['content'] = result
        
        # Convert to ensemble results
        ensemble_results = []
        for content_id, vote_data in content_votes.items():
            if vote_data['content']:
                content = vote_data['content']
                
                # Calculate ensemble score
                ensemble_score = vote_data['total_score'] / len(vote_data['votes'])
                
                # Generate ensemble reason
                engine_names = list(vote_data['votes'].keys())
                reason = f"Recommended by {len(engine_names)} engines: {', '.join(engine_names)}. "
                reason += content.get('reason', 'High-quality content')
                
                ensemble_result = EnsembleResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=content.get('score', 0),
                    reason=reason,
                    ensemble_score=ensemble_score,
                    engine_votes=dict(vote_data['votes']),
                    technologies=content.get('technologies', []),
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate')
                )
                
                ensemble_results.append(ensemble_result)
        
        # Sort by ensemble score and limit
        ensemble_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        return ensemble_results[:request.max_recommendations]

# Global instance
_ensemble_instance = None

def get_ensemble_engine() -> EnsembleEngine:
    """Get global ensemble engine instance"""
    global _ensemble_instance
    if _ensemble_instance is None:
        _ensemble_instance = EnsembleEngine()
    return _ensemble_instance

def get_ensemble_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Main function to get ensemble recommendations"""
    try:
        request = EnsembleRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engines=request_data.get('engines', ['unified', 'smart'])
        )
        
        ensemble_engine = get_ensemble_engine()
        results = ensemble_engine.get_ensemble_recommendations(request)
        
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error getting ensemble recommendations: {e}")
        return [] 