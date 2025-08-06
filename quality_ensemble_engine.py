#!/usr/bin/env python3
"""
Quality Ensemble Recommendation Engine
Prioritizes the bestest recommendations with maximum quality
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
class QualityEnsembleRequest:
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    project_id: int = None
    max_recommendations: int = 10
    engines: List[str] = None  # ['unified', 'smart', 'enhanced', 'gemini']

@dataclass
class QualityEnsembleResult:
    id: int
    title: str
    url: str
    score: float
    reason: str
    ensemble_score: float
    engine_votes: Dict[str, float]
    quality_metrics: Dict[str, float]
    technologies: List[str] = None
    content_type: str = "article"
    difficulty: str = "intermediate"

class QualityEnsembleEngine:
    """Quality-focused ensemble engine for the bestest recommendations"""
    
    def __init__(self):
        self.engine_weights = {
            'unified': 0.2,         # Balanced weight for unified
            'smart': 0.15,          # Good weight for smart
            'enhanced': 0.15,       # Good weight for enhanced
            'high_relevance': 0.25, # High weight for relevance engine (most important)
            'phase3': 0.1,          # Phase 3 engine
            'fast_gemini': 0.1,     # Fast Gemini engine
            'gemini_enhanced': 0.05 # Gemini Enhanced engine
        }
        self.cache_duration = 1800  # 30 minutes (shorter for speed)
        self.max_parallel_engines = 7  # Allow all engines including high_relevance
        self.timeout_seconds = 15  # Increased to 15 seconds for high relevance engine
        self.quality_threshold = 0.2  # Lowered threshold for faster results
        self.min_engine_agreement = 1  # Keep at 1 for speed
        logger.info("High Relevance Engine initialized for independent operation")
    
    def get_quality_ensemble_recommendations(self, request: QualityEnsembleRequest) -> List[QualityEnsembleResult]:
        """Get high relevance recommendations (independent engine operation)"""
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Cache hit for high relevance recommendations")
                return cached_result
            
            # Use ONLY high relevance engine for this endpoint (independent operation)
            engines_to_use = ['high_relevance']  # Only use high relevance engine
            available_engines = self._get_available_engines(engines_to_use)
            
            if not available_engines:
                logger.warning("High Relevance Engine not available, returning empty results")
                return []
            
            logger.info(f"Using High Relevance Engine independently: {available_engines}")
            
            # Get recommendations from high relevance engine ONLY (independent operation)
            # Direct call to avoid any multi-engine complexity
            logger.info("Running High Relevance Engine directly (independent operation)")
            high_relevance_results = self._get_high_relevance_results_quality(request)
            engine_results = {'high_relevance': high_relevance_results}
            
            # Process High Relevance Engine results directly (independent operation)
            high_relevance_results = engine_results['high_relevance']
            # Convert to QualityEnsembleResult format
            ensemble_results = []
            for i, result in enumerate(high_relevance_results):
                ensemble_result = QualityEnsembleResult(
                    id=result.get('id'),
                    title=result.get('title', ''),
                    url=result.get('url', ''),
                    score=result.get('score', 0),
                    reason=result.get('reason', ''),
                    ensemble_score=result.get('score', 0),  # Use original score
                    engine_votes={'high_relevance': result.get('score', 0)},
                    quality_metrics={'high_relevance_score': result.get('score', 0)},
                    technologies=result.get('technologies', []),
                    content_type=result.get('content_type', 'article'),
                    difficulty=result.get('difficulty', 'intermediate')
                )
                ensemble_results.append(ensemble_result)
            
            # Sort by score and limit
            ensemble_results.sort(key=lambda x: x.ensemble_score, reverse=True)
            ensemble_results = ensemble_results[:request.max_recommendations]
            
            # Cache results
            self._cache_result(cache_key, ensemble_results)
            
            response_time = (time.time() - start_time) * 1000
            logger.info(f"High Relevance Engine (Independent) completed in {response_time:.2f}ms")
            
            return ensemble_results
            
        except Exception as e:
            logger.error(f"High Relevance Engine error: {e}")
            return []
    
    def _generate_cache_key(self, request: QualityEnsembleRequest) -> str:
        """Generate cache key for high relevance request"""
        request_data = {
            'user_id': request.user_id,
            'title': request.title,
            'description': request.description,
            'technologies': request.technologies,
            'project_id': request.project_id,
            'max_recommendations': request.max_recommendations,
            'engines': sorted(request.engines or ['unified', 'smart', 'enhanced'])
        }
        request_hash = hashlib.md5(json.dumps(request_data, sort_keys=True).encode()).hexdigest()
        return f"high_relevance_quality_recommendations:{request_hash}"
    
    def _get_cached_result(self, cache_key: str) -> List[QualityEnsembleResult]:
        """Get cached high relevance result"""
        try:
            cached_data = redis_cache.get_cache(cache_key)
            if cached_data:
                return [QualityEnsembleResult(**result) for result in cached_data]
            return None
        except Exception as e:
            logger.warning(f"Error getting cached result: {e}")
            return None
    
    def _cache_result(self, cache_key: str, results: List[QualityEnsembleResult]):
        """Cache high relevance result"""
        try:
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
                elif engine == 'high_relevance':
                    from high_relevance_engine import high_relevance_engine
                    available.append(engine)
            except ImportError:
                logger.warning(f"Engine {engine} not available")
        
        return available
    
    def _get_all_engine_results(self, engines: List[str], request: QualityEnsembleRequest) -> Dict[str, List[Dict]]:
        """Get results from all engines in parallel for maximum quality"""
        results = {}
        failed_engines = []
        with ThreadPoolExecutor(max_workers=self.max_parallel_engines) as executor:
            # Submit tasks for all engines
            future_to_engine = {
                executor.submit(self._get_single_engine_results, engine, request): engine 
                for engine in engines
            }
            try:
                for future in as_completed(future_to_engine, timeout=self.timeout_seconds):
                    engine_name = future_to_engine[future]
                    try:
                        engine_results = future.result(timeout=12)  # Increased to 12 seconds per engine
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
                logger.error(f"Quality ensemble error: {len(unfinished)} (of {len(engines)}) futures unfinished: {list(unfinished)}")
                for engine_name in unfinished:
                    results[engine_name] = []
        return results
    
    def _get_single_engine_results(self, engine_name: str, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from a single engine with maximum quality"""
        try:
            if engine_name == 'unified':
                return self._get_unified_results_quality(request)
            elif engine_name == 'smart':
                return self._get_smart_results_quality(request)
            elif engine_name == 'enhanced':
                return self._get_enhanced_results_quality(request)
            elif engine_name == 'phase3':
                return self._get_phase3_results_quality(request)
            elif engine_name == 'fast_gemini':
                return self._get_fast_gemini_results_quality(request)
            elif engine_name == 'gemini_enhanced':
                return self._get_gemini_enhanced_results_quality(request)
            elif engine_name == 'high_relevance':
                return self._get_high_relevance_results_quality(request)
            else:
                logger.warning(f"Unknown engine: {engine_name}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting {engine_name} results: {e}")
            return []
    
    def _get_unified_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from unified engine with maximum quality"""
        try:
            from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
            
            orchestrator = get_unified_orchestrator()
            unified_request = UnifiedRecommendationRequest(
                user_id=request.user_id,
                title=request.title,
                description=request.description,
                technologies=request.technologies,
                project_id=request.project_id,
                max_recommendations=request.max_recommendations * 2,  # Reduced from 4 to 2 for speed
                engine_preference='fast',  # Use fast engine preference for speed
                cache_duration=900,  # 15 minutes cache (shorter for speed)
                quality_threshold=6,  # Lowered from 8 to 6 for speed
                diversity_weight=0.3  # Reduced from 0.5 to 0.3 for speed
            )
            
            results = orchestrator.get_recommendations(unified_request)
            return [asdict(result) for result in results]
            
        except Exception as e:
            logger.error(f"Error getting unified results: {e}")
            return []
    
    def _get_smart_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from smart engine with maximum quality"""
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
                limit=request.max_recommendations * 2  # Reduced from 3 to 2 for speed
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
    
    def _get_enhanced_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from enhanced engine with maximum quality"""
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
                limit=request.max_recommendations * 2  # Reduced from 3 to 2 for speed
            )
            return results
            
        except Exception as e:
            logger.warning(f"Enhanced engine not available: {e}")
            return []
    
    def _get_phase3_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from Phase 3 engine with maximum quality"""
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
    
    def _get_fast_gemini_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from Fast Gemini engine with maximum quality"""
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
    
    def _get_gemini_enhanced_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from Gemini Enhanced engine with maximum quality"""
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
    
    def _get_high_relevance_results_quality(self, request: QualityEnsembleRequest) -> List[Dict]:
        """Get results from high relevance engine with quality focus"""
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
                # Get user's saved content dynamically (no hardcoding)
                with db.session.begin():
                    # Get user's technologies for filtering
                    user_technologies = [tech.strip().lower() for tech in request.technologies.split(',') if tech.strip()]
                    
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
                             total_tech_count = len(content_technologies)
                             
                             # Only include if it has good relevance (at least 50% of user techs or primary tech match)
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
                         
                         # Get high relevance recommendations with reduced processing
                         results = high_relevance_engine.get_high_relevance_recommendations(
                             bookmarks=bookmarks_data[:10],  # Only process top 10 bookmarks for speed
                             user_input=user_input,
                             max_recommendations=min(request.max_recommendations, 3)  # Limit to 3 for speed
                         )
                         
                         logger.info(f"High Relevance Engine: {len(results)} results")
                         return results
            
        except Exception as e:
            logger.warning(f"High Relevance engine not available: {e}")
            return []
    
    def _combine_results_maximum_quality(self, engine_results: Dict[str, List[Dict]], request: QualityEnsembleRequest) -> List[QualityEnsembleResult]:
        """Combine results using maximum quality voting"""
        # Track votes for each content item
        content_votes = defaultdict(lambda: {
            'votes': defaultdict(float),
            'content': None,
            'total_score': 0.0,
            'quality_score': 0.0,
            'engine_count': 0,
            'high_quality_votes': 0
        })
        
        # Collect votes from each engine with quality weighting
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for i, result in enumerate(results):
                content_id = result.get('id')
                if not content_id:
                    continue
                
                # Enhanced vote calculation with maximum quality focus
                rank_score = 1.0 / (i + 1)  # Higher rank = higher score
                score = result.get('score', 0) / 100.0  # Normalize score
                
                # Maximum quality bonus for high-scoring content
                if score >= 0.9:
                    quality_bonus = 2.0  # Maximum bonus for excellent content
                elif score >= 0.8:
                    quality_bonus = 1.5  # High bonus for very good content
                elif score >= 0.7:
                    quality_bonus = 1.2  # Good bonus for good content
                else:
                    quality_bonus = 0.5  # Low bonus for average content
                
                # Calculate vote with maximum quality weighting
                vote = (rank_score * 0.3 + score * 0.7) * weight * quality_bonus
                
                content_votes[content_id]['votes'][engine_name] = vote
                content_votes[content_id]['total_score'] += vote
                content_votes[content_id]['quality_score'] += score
                content_votes[content_id]['engine_count'] += 1
                if score >= 0.8:
                    content_votes[content_id]['high_quality_votes'] += 1
                content_votes[content_id]['content'] = result
        
        # Convert to ensemble results with maximum quality filtering
        ensemble_results = []
        for content_id, vote_data in content_votes.items():
            content = vote_data['content']
            if not content:
                continue
            
            # Calculate ensemble score with maximum quality consideration
            avg_quality = vote_data['quality_score'] / vote_data['engine_count'] if vote_data['engine_count'] > 0 else 0
            engine_agreement_bonus = min(vote_data['engine_count'] / 3.0, 1.0)  # Bonus for engine agreement
            quality_boost = (1 + avg_quality * 0.5) * (1 + engine_agreement_bonus * 0.3)
            ensemble_score = vote_data['total_score'] * quality_boost
            
            # Maximum quality filtering
            if avg_quality < self.quality_threshold and vote_data['engine_count'] < self.min_engine_agreement:
                continue  # Skip low-quality content unless multiple engines agree
            
            # Only filter out very low quality content
            if avg_quality < 0.1 and vote_data['engine_count'] < 2:
                continue  # Skip very low-quality content
            
            # Calculate quality metrics
            quality_metrics = {
                'average_quality': avg_quality,
                'engine_agreement': vote_data['engine_count'],
                'high_quality_votes': vote_data['high_quality_votes'],
                'quality_boost': quality_boost
            }
            
            # Create ensemble result
            ensemble_result = QualityEnsembleResult(
                id=content.get('id'),
                title=content.get('title', ''),
                url=content.get('url', ''),
                score=content.get('score', 0),
                reason=content.get('reason', ''),
                ensemble_score=ensemble_score,
                engine_votes=dict(vote_data['votes']),
                quality_metrics=quality_metrics,
                technologies=content.get('technologies', []),
                content_type=content.get('content_type', 'article'),
                difficulty=content.get('difficulty', 'intermediate')
            )
            ensemble_results.append(ensemble_result)
        
        # Sort by ensemble score and limit results
        ensemble_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        return ensemble_results[:request.max_recommendations]

# Global instance
_quality_ensemble_engine = None

def get_quality_ensemble_engine() -> QualityEnsembleEngine:
    """Get singleton quality ensemble engine instance"""
    global _quality_ensemble_engine
    if _quality_ensemble_engine is None:
        _quality_ensemble_engine = QualityEnsembleEngine()
    return _quality_ensemble_engine

def get_quality_ensemble_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get high relevance recommendations (independent engine)"""
    try:
        # Create request object
        request = QualityEnsembleRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engines=request_data.get('engines', ['unified', 'smart', 'enhanced'])
        )
        
        # Get quality ensemble engine
        engine = get_quality_ensemble_engine()
        
        # Get recommendations
        results = engine.get_quality_ensemble_recommendations(request)
        
        # Convert to dict format
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in get_high_relevance_recommendations: {e}")
        return [] 