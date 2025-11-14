#!/usr/bin/env python3
"""
3-Stage Hybrid Recommendation System
Implements the complete recipe: Semantic Candidate Generation + Collaborative Candidates + Learning-to-Rank
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our ML engines
try:
    from learning_to_rank_engine import LearningToRankEngine, create_ranking_engine
    from collaborative_filtering_engine import CollaborativeFilteringEngine, create_cf_engine
    from faiss_vector_engine import FAISSVectorEngine, create_faiss_engine
    ML_ENGINES_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ All ML engines imported successfully")
except ImportError as e:
    ML_ENGINES_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Some ML engines not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HybridRecommendationRequest:
    """Request for hybrid recommendations"""
    user_id: int
    query_text: str
    technologies: List[str] = field(default_factory=list)
    content_type_preference: Optional[str] = None
    difficulty_preference: Optional[str] = None
    max_recommendations: int = 20
    diversity_weight: float = 0.3
    use_collaborative_filtering: bool = True
    use_learning_to_rank: bool = True
    min_semantic_score: float = 0.3
    min_cf_score: float = 0.2

@dataclass
class HybridRecommendationResult:
    """Result from hybrid recommendation system"""
    content_id: int
    title: str
    url: str
    final_score: float
    semantic_score: float
    cf_score: float
    ltr_score: float
    rank_position: int
    recommendation_reason: str
    content_type: str
    difficulty: str
    technologies: List[str]
    metadata: Dict[str, Any]

@dataclass
class StagePerformance:
    """Performance metrics for each stage"""
    stage_name: str
    execution_time_ms: float
    candidates_generated: int
    success: bool
    error_message: Optional[str] = None

class HybridRecommendationSystem:
    """Complete 3-stage hybrid recommendation system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.performance_history = []
        
        # Initialize engines
        self._initialize_engines()
        
        # Performance tracking
        self.stage_performances = {}
        self.total_recommendations = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'semantic': {
                'engine_type': 'faiss_hnsw',
                'dimension': 384,
                'min_score': 0.3,
                'max_candidates': 100
            },
            'collaborative': {
                'engine_type': 'als',
                'min_score': 0.2,
                'max_candidates': 50,
                'min_interactions': 5
            },
            'learning_to_rank': {
                'enabled': True,
                'model_path': 'models/hybrid_ltr_model.txt',
                'feature_weights': {
                    'semantic_similarity': 0.4,
                    'cf_score': 0.3,
                    'content_quality': 0.2,
                    'diversity': 0.1
                }
            },
            'diversity': {
                'enabled': True,
                'max_similar_tech': 0.7,
                'max_similar_difficulty': 0.8,
                'content_type_spread': 0.6
            },
            'caching': {
                'enabled': True,
                'ttl_seconds': 3600,
                'max_cache_size': 10000
            }
        }
    
    def _initialize_engines(self):
        """Initialize all ML engines"""
        try:
            # Stage 1: Semantic Candidate Generation
            if self.config['semantic']['engine_type'] == 'faiss_hnsw':
                self.semantic_engine = create_faiss_engine('hnsw', self.config['semantic']['dimension'])
            elif self.config['semantic']['engine_type'] == 'faiss_ivf':
                self.semantic_engine = create_faiss_engine('ivf', self.config['semantic']['dimension'])
            else:
                self.semantic_engine = create_faiss_engine('hnsw', self.config['semantic']['dimension'])
            
            # Stage 2: Collaborative Filtering
            self.cf_engine = create_cf_engine(self.config['collaborative']['engine_type'])
            
            # Stage 3: Learning-to-Rank
            if self.config['learning_to_rank']['enabled']:
                model_path = self.config['learning_to_rank']['model_path']
                if os.path.exists(model_path):
                    self.ltr_engine = create_ranking_engine(model_path)
                else:
                    self.ltr_engine = create_ranking_engine()
            else:
                self.ltr_engine = None
            
            logger.info("✅ All ML engines initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ML engines: {e}")
            ML_ENGINES_AVAILABLE = False
    
    def get_recommendations(self, request: HybridRecommendationRequest) -> List[HybridRecommendationResult]:
        """Get hybrid recommendations using the 3-stage pipeline"""
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Starting hybrid recommendation for user {request.user_id}")
            
            # Stage 1: Semantic Candidate Generation
            semantic_candidates = self._generate_semantic_candidates(request)
            if not semantic_candidates:
                logger.warning("No semantic candidates generated")
                return []
            
            # Stage 2: Collaborative Filtering (when interactions exist)
            cf_candidates = []
            if request.use_collaborative_filtering:
                cf_candidates = self._generate_collaborative_candidates(request)
            
            # Stage 3: Learning-to-Rank (final ordering)
            final_recommendations = []
            if request.use_learning_to_rank and self.ltr_engine:
                final_recommendations = self._apply_learning_to_rank(
                    semantic_candidates, cf_candidates, request
                )
            else:
                final_recommendations = self._apply_simple_ranking(
                    semantic_candidates, cf_candidates, request
                )
            
            # Apply diversity and final filtering
            final_recommendations = self._apply_diversity_filtering(final_recommendations, request)
            
            # Limit to requested number
            final_recommendations = final_recommendations[:request.max_recommendations]
            
            # Update performance metrics
            total_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(total_time, len(final_recommendations))
            
            logger.info(f"✅ Generated {len(final_recommendations)} hybrid recommendations in {total_time:.2f}ms")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error in hybrid recommendation pipeline: {e}")
            return []
    
    def _generate_semantic_candidates(self, request: HybridRecommendationRequest) -> List[Dict[str, Any]]:
        """Stage 1: Generate semantic candidates using FAISS"""
        stage_start = time.time()
        
        try:
            # Generate query embedding (this would come from your existing embedding system)
            query_embedding = self._generate_query_embedding(request.query_text)
            if query_embedding is None:
                return []
            
            # Search FAISS index
            search_results = self.semantic_engine.search(
                query_embedding, 
                k=self.config['semantic']['max_candidates']
            )
            
            # Convert to candidate format
            candidates = []
            for result in search_results:
                if result.similarity_score >= self.config['semantic']['min_score']:
                    candidate = {
                        'id': result.content_id,
                        'semantic_score': result.similarity_score,
                        'metadata': result.metadata,
                        'stage': 'semantic'
                    }
                    candidates.append(candidate)
            
            # Record performance
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['semantic'] = StagePerformance(
                'semantic_generation',
                stage_time,
                len(candidates),
                True
            )
            
            logger.info(f"✅ Stage 1: Generated {len(candidates)} semantic candidates in {stage_time:.2f}ms")
            return candidates
            
        except Exception as e:
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['semantic'] = StagePerformance(
                'semantic_generation',
                stage_time,
                0,
                False,
                str(e)
            )
            logger.error(f"Error in semantic candidate generation: {e}")
            return []
    
    def _generate_collaborative_candidates(self, request: HybridRecommendationRequest) -> List[Dict[str, Any]]:
        """Stage 2: Generate collaborative filtering candidates"""
        stage_start = time.time()
        
        try:
            # Check if user has enough interactions
            user_stats = self.cf_engine.get_model_performance()
            if user_stats.get('status') != 'trained':
                logger.info("CF model not trained, skipping collaborative filtering")
                return []
            
            # Get CF recommendations
            cf_results = self.cf_engine.get_recommendations(
                request.user_id,
                n_recommendations=self.config['collaborative']['max_candidates'],
                min_score=self.config['collaborative']['min_score']
            )
            
            # Convert to candidate format
            candidates = []
            for result in cf_results:
                candidate = {
                    'id': result.content_id,
                    'cf_score': result.cf_score,
                    'confidence': result.confidence,
                    'metadata': {
                        'interaction_count': result.interaction_count,
                        'similar_users_count': result.similar_users_count
                    },
                    'stage': 'collaborative'
                }
                candidates.append(candidate)
            
            # Record performance
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['collaborative'] = StagePerformance(
                'collaborative_generation',
                stage_time,
                len(candidates),
                True
            )
            
            logger.info(f"✅ Stage 2: Generated {len(candidates)} CF candidates in {stage_time:.2f}ms")
            return candidates
            
        except Exception as e:
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['collaborative'] = StagePerformance(
                'collaborative_generation',
                stage_time,
                0,
                False,
                str(e)
            )
            logger.error(f"Error in collaborative candidate generation: {e}")
            return []
    
    def _apply_learning_to_rank(self, semantic_candidates: List[Dict], 
                               cf_candidates: List[Dict], 
                               request: HybridRecommendationRequest) -> List[HybridRecommendationResult]:
        """Stage 3: Apply Learning-to-Rank for final ordering"""
        stage_start = time.time()
        
        try:
            # Merge candidates from both stages
            merged_candidates = self._merge_candidates(semantic_candidates, cf_candidates)
            
            if not merged_candidates:
                return []
            
            # Prepare features for LTR
            ltr_features = self._prepare_ltr_features(merged_candidates, request)
            
            # Apply LTR ranking
            ltr_results = self.ltr_engine.rank_recommendations(
                ltr_features, 
                {'user_id': request.user_id, 'query': request.query_text},
                {'user_id': request.user_id}
            )
            
            # Convert to final results
            final_results = []
            for result in ltr_results:
                candidate = merged_candidates[result.content_id]
                final_result = HybridRecommendationResult(
                    content_id=result.content_id,
                    title=candidate.get('title', 'Unknown'),
                    url=candidate.get('url', ''),
                    final_score=result.ranked_score,
                    semantic_score=candidate.get('semantic_score', 0.0),
                    cf_score=candidate.get('cf_score', 0.0),
                    ltr_score=result.ranked_score,
                    rank_position=result.rank_position,
                    recommendation_reason=result.ranking_reason,
                    content_type=candidate.get('content_type', 'unknown'),
                    difficulty=candidate.get('difficulty', 'unknown'),
                    technologies=candidate.get('technologies', []),
                    metadata=candidate.get('metadata', {})
                )
                final_results.append(final_result)
            
            # Record performance
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['learning_to_rank'] = StagePerformance(
                'learning_to_rank',
                stage_time,
                len(final_results),
                True
            )
            
            logger.info(f"✅ Stage 3: Applied LTR ranking to {len(final_results)} candidates in {stage_time:.2f}ms")
            return final_results
            
        except Exception as e:
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['learning_to_rank'] = StagePerformance(
                'learning_to_rank',
                stage_time,
                0,
                False,
                str(e)
            )
            logger.error(f"Error in learning-to-rank: {e}")
            return self._apply_simple_ranking(semantic_candidates, cf_candidates, request)
    
    def _apply_simple_ranking(self, semantic_candidates: List[Dict], 
                             cf_candidates: List[Dict], 
                             request: HybridRecommendationRequest) -> List[HybridRecommendationResult]:
        """Fallback simple ranking when LTR is not available"""
        stage_start = time.time()
        
        try:
            # Merge candidates
            merged_candidates = self._merge_candidates(semantic_candidates, cf_candidates)
            
            if not merged_candidates:
                return []
            
            # Calculate combined scores
            scored_candidates = []
            for candidate in merged_candidates.values():
                # Simple weighted combination
                semantic_score = candidate.get('semantic_score', 0.0)
                cf_score = candidate.get('cf_score', 0.0)
                
                # Weight semantic more heavily if CF score is low
                if cf_score > 0.1:
                    combined_score = 0.7 * semantic_score + 0.3 * cf_score
                else:
                    combined_score = semantic_score
                
                scored_candidates.append((candidate, combined_score))
            
            # Sort by combined score
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Convert to final results
            final_results = []
            for i, (candidate, score) in enumerate(scored_candidates):
                final_result = HybridRecommendationResult(
                    content_id=candidate['id'],
                    title=candidate.get('title', 'Unknown'),
                    url=candidate.get('url', ''),
                    final_score=score,
                    semantic_score=candidate.get('semantic_score', 0.0),
                    cf_score=candidate.get('cf_score', 0.0),
                    ltr_score=score,
                    rank_position=i + 1,
                    recommendation_reason=f"Combined score: {score:.3f} (Semantic: {candidate.get('semantic_score', 0.0):.3f}, CF: {candidate.get('cf_score', 0.0):.3f})",
                    content_type=candidate.get('content_type', 'unknown'),
                    difficulty=candidate.get('difficulty', 'unknown'),
                    technologies=candidate.get('technologies', []),
                    metadata=candidate.get('metadata', {})
                )
                final_results.append(final_result)
            
            # Record performance
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['simple_ranking'] = StagePerformance(
                'simple_ranking',
                stage_time,
                len(final_results),
                True
            )
            
            logger.info(f"✅ Applied simple ranking to {len(final_results)} candidates in {stage_time:.2f}ms")
            return final_results
            
        except Exception as e:
            stage_time = (time.time() - stage_start) * 1000
            self.stage_performances['simple_ranking'] = StagePerformance(
                'simple_ranking',
                stage_time,
                0,
                False,
                str(e)
            )
            logger.error(f"Error in simple ranking: {e}")
            return []
    
    def _merge_candidates(self, semantic_candidates: List[Dict], 
                         cf_candidates: List[Dict]) -> Dict[int, Dict[str, Any]]:
        """Merge candidates from different stages"""
        merged = {}
        
        # Add semantic candidates
        for candidate in semantic_candidates:
            content_id = candidate['id']
            merged[content_id] = {
                'id': content_id,
                'semantic_score': candidate['semantic_score'],
                'cf_score': 0.0,
                'stage': 'semantic',
                'metadata': candidate.get('metadata', {})
            }
        
        # Add/update with CF candidates
        for candidate in cf_candidates:
            content_id = candidate['id']
            if content_id in merged:
                merged[content_id]['cf_score'] = candidate['cf_score']
                merged[content_id]['stage'] = 'hybrid'
                # Merge metadata
                merged[content_id]['metadata'].update(candidate.get('metadata', {}))
            else:
                merged[content_id] = {
                    'id': content_id,
                    'semantic_score': 0.0,
                    'cf_score': candidate['cf_score'],
                    'stage': 'collaborative',
                    'metadata': candidate.get('metadata', {})
                }
        
        return merged
    
    def _prepare_ltr_features(self, candidates: Dict[int, Dict], 
                             request: HybridRecommendationRequest) -> List[Dict]:
        """Prepare features for Learning-to-Rank"""
        features = []
        
        for candidate in candidates.values():
            feature_dict = {
                'id': candidate['id'],
                'semantic_similarity': candidate.get('semantic_score', 0.0),
                'cf_score': candidate.get('cf_score', 0.0),
                'content_quality': candidate.get('metadata', {}).get('quality_score', 0.5),
                'content_freshness': candidate.get('metadata', {}).get('freshness_score', 0.5),
                'technology_overlap': self._calculate_tech_overlap(
                    candidate.get('metadata', {}).get('technologies', []),
                    request.technologies
                ),
                'content_type_match': self._calculate_content_type_match(
                    candidate.get('metadata', {}).get('content_type'),
                    request.content_type_preference
                ),
                'difficulty_match': self._calculate_difficulty_match(
                    candidate.get('metadata', {}).get('difficulty'),
                    request.difficulty_preference
                )
            }
            features.append(feature_dict)
        
        return features
    
    def _calculate_tech_overlap(self, content_techs: List[str], request_techs: List[str]) -> float:
        """Calculate technology overlap score"""
        if not request_techs:
            return 0.5
        
        content_set = set(tech.lower() for tech in content_techs)
        request_set = set(tech.lower() for tech in request_techs)
        
        overlap = len(content_set & request_set)
        return overlap / len(request_set)
    
    def _calculate_content_type_match(self, content_type: Optional[str], 
                                    preferred_type: Optional[str]) -> float:
        """Calculate content type match score"""
        if not preferred_type or not content_type:
            return 0.5
        
        if content_type.lower() == preferred_type.lower():
            return 1.0
        elif content_type.lower() in preferred_type.lower() or preferred_type.lower() in content_type.lower():
            return 0.8
        else:
            return 0.3
    
    def _calculate_difficulty_match(self, content_difficulty: Optional[str], 
                                  preferred_difficulty: Optional[str]) -> float:
        """Calculate difficulty match score"""
        if not preferred_difficulty or not content_difficulty:
            return 0.5
        
        difficulty_levels = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        
        content_level = difficulty_levels.get(content_difficulty.lower(), 2)
        preferred_level = difficulty_levels.get(preferred_difficulty.lower(), 2)
        
        level_diff = abs(content_level - preferred_level)
        if level_diff == 0:
            return 1.0
        elif level_diff == 1:
            return 0.7
        else:
            return 0.4
    
    def _apply_diversity_filtering(self, recommendations: List[HybridRecommendationResult], 
                                 request: HybridRecommendationRequest) -> List[HybridRecommendationResult]:
        """Apply diversity filtering to final recommendations"""
        if not self.config['diversity']['enabled']:
            return recommendations
        
        try:
            filtered_results = []
            used_technologies = set()
            used_difficulties = set()
            used_content_types = set()
            
            for result in recommendations:
                # Check technology diversity
                tech_overlap = len(set(result.technologies) & used_technologies) / max(len(result.technologies), 1)
                if tech_overlap > self.config['diversity']['max_similar_tech']:
                    continue
                
                # Check difficulty diversity
                if result.difficulty in used_difficulties:
                    difficulty_count = sum(1 for r in filtered_results if r.difficulty == result.difficulty)
                    if difficulty_count > 0 and len(filtered_results) > 0:
                        difficulty_ratio = difficulty_count / len(filtered_results)
                        if difficulty_ratio > self.config['diversity']['max_similar_difficulty']:
                            continue
                
                # Check content type diversity
                if result.content_type in used_content_types:
                    content_type_count = sum(1 for r in filtered_results if r.content_type == result.content_type)
                    if content_type_count > 0 and len(filtered_results) > 0:
                        content_type_ratio = content_type_count / len(filtered_results)
                        if content_type_ratio > self.config['diversity']['content_type_spread']:
                            continue
                
                # Add to filtered results
                filtered_results.append(result)
                used_technologies.update(result.technologies)
                used_difficulties.add(result.difficulty)
                used_content_types.add(result.content_type)
                
                if len(filtered_results) >= request.max_recommendations:
                    break
            
            logger.info(f"✅ Applied diversity filtering: {len(recommendations)} -> {len(filtered_results)} results")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error in diversity filtering: {e}")
            return recommendations
    
    def _generate_query_embedding(self, query_text: str) -> Optional[np.ndarray]:
        """Generate embedding for query text"""
        try:
            # This would integrate with your existing embedding system
            # For now, return a dummy embedding
            logger.warning("Using dummy embedding - integrate with your existing embedding system")
            return np.random.rand(384).astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return None
    
    def _update_performance_metrics(self, total_time: float, result_count: int):
        """Update performance tracking metrics"""
        self.total_recommendations += result_count
        
        performance_record = {
            'timestamp': datetime.now().isoformat(),
            'total_time_ms': total_time,
            'result_count': result_count,
            'stage_performances': self.stage_performances.copy()
        }
        
        self.performance_history.append(performance_record)
        
        # Keep only last 100 records
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get overall system performance metrics"""
        if not self.performance_history:
            return {'status': 'no_data'}
        
        try:
            recent_performances = self.performance_history[-10:]  # Last 10 requests
            
            avg_time = np.mean([p['total_time_ms'] for p in recent_performances])
            avg_results = np.mean([p['result_count'] for p in recent_performances])
            
            stage_stats = {}
            for stage_name in ['semantic', 'collaborative', 'learning_to_rank', 'simple_ranking']:
                stage_perfs = [p['stage_performances'].get(stage_name) for p in recent_performances if stage_name in p['stage_performances']]
                if stage_perfs:
                    stage_stats[stage_name] = {
                        'avg_time_ms': np.mean([p.execution_time_ms for p in stage_perfs if p]),
                        'success_rate': np.mean([1 if p and p.success else 0 for p in stage_perfs]),
                        'avg_candidates': np.mean([p.candidates_generated for p in stage_perfs if p])
                    }
            
            return {
                'total_recommendations': self.total_recommendations,
                'recent_avg_time_ms': avg_time,
                'recent_avg_results': avg_results,
                'stage_performances': stage_stats,
                'cache_hit_rate': self.cache_hits / max(self.total_recommendations, 1)
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def train_models(self, training_data: Dict[str, Any]) -> Dict[str, bool]:
        """Train all ML models"""
        results = {}
        
        try:
            # Train collaborative filtering model
            if 'cf_interactions' in training_data:
                cf_success = self.cf_engine.train_model()
                results['collaborative_filtering'] = cf_success
            
            # Train learning-to-rank model
            if 'ltr_training_data' in training_data and self.ltr_engine:
                ltr_success = self.ltr_engine.train_model(training_data['ltr_training_data'])
                results['learning_to_rank'] = ltr_success
            
            logger.info(f"✅ Model training results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error training models: {e}")
            return {'error': str(e)}
    
    def save_models(self, base_path: str = 'models') -> Dict[str, bool]:
        """Save all trained models"""
        results = {}
        
        try:
            # Save CF model
            cf_path = os.path.join(base_path, 'cf_model.pkl')
            results['collaborative_filtering'] = self.cf_engine.save_model(cf_path)
            
            # Save LTR model
            if self.ltr_engine:
                ltr_path = os.path.join(base_path, 'hybrid_ltr_model.txt')
                results['learning_to_rank'] = self.ltr_engine.save_model(ltr_path)
            
            # Save FAISS index
            faiss_path = os.path.join(base_path, 'hybrid_faiss_index.index')
            results['semantic_search'] = self.semantic_engine.save_index(faiss_path)
            
            logger.info(f"✅ Model saving results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
            return {'error': str(e)}

# Factory function
def create_hybrid_system(config: Optional[Dict[str, Any]] = None) -> HybridRecommendationSystem:
    """Create a hybrid recommendation system instance"""
    return HybridRecommendationSystem(config)

# Example usage
if __name__ == "__main__":
    # Create system
    system = create_hybrid_system()
    
    # Example request
    request = HybridRecommendationRequest(
        user_id=1,
        query_text="Python machine learning tutorial",
        technologies=['python', 'scikit-learn'],
        content_type_preference='tutorial',
        difficulty_preference='intermediate',
        max_recommendations=10
    )
    
    # Get recommendations
    recommendations = system.get_recommendations(request)
    
    print(f"Generated {len(recommendations)} recommendations:")
    for rec in recommendations:
        print(f"{rec.rank_position}. {rec.title} (Score: {rec.final_score:.3f})")
        print(f"   Semantic: {rec.semantic_score:.3f}, CF: {rec.cf_score:.3f}, LTR: {rec.ltr_score:.3f}")
        print(f"   Reason: {rec.recommendation_reason}")
        print()
    
    # Get performance metrics
    performance = system.get_system_performance()
    print(f"System performance: {performance}")

