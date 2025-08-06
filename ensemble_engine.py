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
            'unified': 0.25,    # Balanced weight for unified
            'smart': 0.2,       # Good weight for smart
            'enhanced': 0.2,    # Good weight for enhanced
            'phase3': 0.15,     # Phase 3 engine
            'fast_gemini': 0.1, # Fast Gemini engine
            'gemini_enhanced': 0.1  # Gemini Enhanced engine
        }
        self.cache_duration = 900  # 15 minutes (reduced for quality improvements)
        self.max_parallel_engines = 6  # Allow all engines
        self.timeout_seconds = 30  # Reduced timeout to prevent authentication issues
        self.quality_threshold = 0.4  # Increased threshold for better quality
        self.min_recommendations = 5  # Minimum recommendations before early termination
        logger.info("Complete Ensemble Engine initialized with all engines")
    
    def get_ensemble_recommendations(self, request: EnsembleRequest) -> List[EnsembleResult]:
        """Get ensemble recommendations with quality optimization"""
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first (but with shorter TTL for quality improvements)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Cache hit for ensemble recommendations")
                return cached_result
            
            # Determine engines to use - only use reliable engines
            engines_to_use = request.engines or ['unified']  # Default to unified only for reliability
            available_engines = self._get_available_engines(engines_to_use)
            
            if not available_engines:
                logger.warning("No engines available, falling back to unified only")
                available_engines = ['unified']
            
            logger.info(f"Using engines for quality: {available_engines}")
            
            # Get recommendations from engines with quality optimization
            engine_results = self._get_engine_results_quality_optimized(available_engines, request)
            
            # Combine results with quality preservation
            ensemble_results = self._combine_results_quality_optimized(engine_results, request)
            
            # Cache results with shorter TTL for quality improvements
            self._cache_result(cache_key, ensemble_results)
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Quality-optimized ensemble completed in {response_time:.2f}ms")
            
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
        """Check which engines are available"""
        available = []
        
        for engine in requested_engines:
            try:
                if engine == 'unified':
                    from unified_recommendation_orchestrator import get_unified_orchestrator
                    get_unified_orchestrator()  # Test if available
                    available.append(engine)
                elif engine == 'smart':
                    from smart_recommendation_engine import SmartRecommendationEngine
                    available.append(engine)
                elif engine == 'enhanced':
                    from enhanced_recommendation_engine import get_enhanced_recommendations
                    available.append(engine)
                elif engine == 'phase3':
                    from phase3_enhanced_engine import get_enhanced_recommendations_phase3
                    available.append(engine)
                elif engine == 'fast_gemini':
                    from fast_gemini_engine import fast_gemini_engine
                    available.append(engine)
                elif engine == 'gemini_enhanced':
                    from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
                    available.append(engine)
            except ImportError:
                logger.warning(f"Engine {engine} not available")
        
        return available
    
    def _get_engine_results_quality_optimized(self, engines: List[str], request: EnsembleRequest) -> Dict[str, List[Dict]]:
        """Get results from engines with quality optimization"""
        engine_results = {}
        
        # Always start with unified engine (fastest)
        if 'unified' in engines:
            try:
                logger.info("Getting unified engine results (fastest)...")
                results = self._get_unified_results_quality(request)
                engine_results['unified'] = results
                logger.info(f"Engine unified: {len(results)} results")
                
                # Only skip other engines if we have high-quality results
                if len(results) >= request.max_recommendations * 2 and self._check_quality_sufficient(results):
                    logger.info("Unified engine provided sufficient high-quality results")
                    return engine_results
                    
            except Exception as e:
                logger.error(f"Error with unified engine: {e}")
                engine_results['unified'] = []
        
        # Get results from quality engines in parallel
        quality_engines = [eng for eng in engines if eng != 'unified']
        if quality_engines:
            engine_results.update(self._get_parallel_quality_engine_results(quality_engines, request))
        
        return engine_results
    
    def _get_unified_results_quality(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from unified engine with quality focus"""
        try:
            from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
            
            orchestrator = get_unified_orchestrator()
            unified_request = UnifiedRecommendationRequest(
                user_id=request.user_id,
                title=request.title,
                description=request.description,
                technologies=request.technologies,
                project_id=request.project_id,
                max_recommendations=request.max_recommendations * 3,  # Get more for quality
                engine_preference='auto',  # Let it choose best engine
                cache_duration=900,  # 15 minutes cache
                quality_threshold=7,  # Higher threshold for quality
                diversity_weight=0.4  # Better diversity
            )
            
            results = orchestrator.get_recommendations(unified_request)
            return [asdict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting unified results: {e}")
            return []
    
    def _get_parallel_quality_engine_results(self, engines: List[str], request: EnsembleRequest) -> Dict[str, List[Dict]]:
        """Get results from quality engines in parallel with longer timeout"""
        results = {}
        failed_engines = []
        with ThreadPoolExecutor(max_workers=self.max_parallel_engines) as executor:
            # Submit tasks
            future_to_engine = {
                executor.submit(self._get_single_engine_results, engine, request): engine 
                for engine in engines
            }
            try:
                for future in as_completed(future_to_engine, timeout=self.timeout_seconds):
                    engine_name = future_to_engine[future]
                    try:
                        engine_results = future.result(timeout=30)  # 30 second timeout per engine
                        results[engine_name] = engine_results
                        logger.info(f"Engine {engine_name}: {len(engine_results)} results")
                    except Exception as e:
                        logger.warning(f"Engine {engine_name} failed or timed out: {e}")
                        results[engine_name] = []
                        failed_engines.append(engine_name)
            except Exception as e:
                logger.error(f"Error during parallel engine execution: {e}")
            # Check for unfinished futures
            unfinished = set(future_to_engine.values()) - set(results.keys())
            if unfinished:
                logger.error(f"Ensemble error: {len(unfinished)} (of {len(engines)}) futures unfinished: {list(unfinished)}")
                for engine_name in unfinished:
                    results[engine_name] = []
        return results
    
    def _get_single_engine_results(self, engine_name: str, request: EnsembleRequest) -> List[Dict]:
        """Get results from a single engine with error handling"""
        try:
            if engine_name == 'smart':
                return self._get_smart_results(request)
            elif engine_name == 'enhanced':
                return self._get_enhanced_results(request)
            elif engine_name == 'phase3':
                return self._get_phase3_results(request)
            elif engine_name == 'fast_gemini':
                return self._get_fast_gemini_results(request)
            elif engine_name == 'gemini_enhanced':
                return self._get_gemini_enhanced_results(request)
            else:
                logger.warning(f"Unknown engine: {engine_name}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting {engine_name} results: {e}")
            return []
    
    def _get_smart_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from smart engine (quality-focused)"""
        try:
            from smart_recommendation_engine import SmartRecommendationEngine
            
            engine = SmartRecommendationEngine(request.user_id)
            project_info = {
                'title': request.title,
                'description': request.description,
                'technologies': request.technologies,
                'learning_goals': request.description
            }
            
            results = engine.get_smart_recommendations(
                project_info=project_info,
                limit=request.max_recommendations * 2  # Get more for quality
            )
            
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
    
    def _get_enhanced_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from enhanced engine (quality-focused)"""
        try:
            from enhanced_recommendation_engine import get_enhanced_recommendations
            
            results = get_enhanced_recommendations(
                user_id=request.user_id,
                request_data={
                    'title': request.title,
                    'description': request.description,
                    'technologies': request.technologies,
                    'project_id': request.project_id
                },
                limit=request.max_recommendations * 2  # Get more for quality
            )
            return results
            
        except Exception as e:
            logger.warning(f"Enhanced engine not available: {e}")
            return []
    
    def _get_phase3_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from Phase 3 engine"""
        try:
            from phase3_enhanced_engine import get_enhanced_recommendations_phase3
            
            results = get_enhanced_recommendations_phase3(
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
            
        except Exception as e:
            logger.warning(f"Phase 3 engine not available: {e}")
            return []
    
    def _get_fast_gemini_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from Fast Gemini engine"""
        try:
            from fast_gemini_engine import fast_gemini_engine
            
            # Get user bookmarks first
            from models import SavedContent
            from app import app
            
            with app.app_context():
                user_bookmarks = SavedContent.query.filter_by(user_id=request.user_id).all()
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
                
                return result.get('recommendations', [])
            
        except Exception as e:
            logger.warning(f"Fast Gemini engine not available: {e}")
            return []
    
    def _get_gemini_enhanced_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from Gemini Enhanced engine"""
        try:
            from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
            
            # Get user bookmarks first
            from models import SavedContent
            from app import app
            
            with app.app_context():
                user_bookmarks = SavedContent.query.filter_by(user_id=request.user_id).all()
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
                
                engine = GeminiEnhancedRecommendationEngine()
                result = engine.get_enhanced_recommendations(
                    bookmarks_data, user_input, request.max_recommendations * 2
                )
                
                return result.get('recommendations', [])
            
        except Exception as e:
            logger.warning(f"Gemini Enhanced engine not available: {e}")
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