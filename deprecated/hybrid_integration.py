#!/usr/bin/env python3
"""
Hybrid Orchestrator Integration
Integrates the new 3-stage ML engines with the existing unified recommendation orchestrator
"""

import os
import sys
import time
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

# Fix OpenBLAS threading issues
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our new ML engines
ML_ENGINES_AVAILABLE = False
try:
    from learning_to_rank_engine import create_ranking_engine, RankingFeatures
    from collaborative_filtering_engine import create_cf_engine, UserInteraction
    from faiss_vector_engine import create_faiss_engine
    ML_ENGINES_AVAILABLE = True
    logger.info("✅ New ML engines imported successfully")
except ImportError as e:
    ML_ENGINES_AVAILABLE = False
    logger.warning(f"⚠️ New ML engines not available: {e}")

@dataclass
class HybridStageResult:
    """Result from each stage of the hybrid system"""
    stage_name: str
    candidates: List[Dict[str, Any]]
    scores: Dict[int, float]
    metadata: Dict[str, Any]
    execution_time_ms: float

class HybridOrchestratorIntegration:
    """Integration layer for the 3-stage hybrid recommendation system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.performance_history = []
        
        # Store ML engines availability as instance variable
        self.ml_engines_available = ML_ENGINES_AVAILABLE
        
        # Initialize ML engines
        self._initialize_ml_engines()
        
        # Performance tracking
        self.stage_performances = {}
        self.total_recommendations = 0
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for hybrid system"""
        return {
            'stages': {
                'semantic': {
                    'enabled': True,
                    'max_candidates': 200,
                    'min_score': 0.1,  # Lowered from 0.3 to allow more candidates
                    'engine_type': 'faiss_hnsw',
                    'dimension': 384
                },
                'collaborative': {
                    'enabled': True,
                    'max_candidates': 100,
                    'min_score': 0.2,
                    'engine_type': 'als',
                    'min_interactions': 5
                },
                'learning_to_rank': {
                    'enabled': True,
                    'max_candidates': 50,
                    'model_path': 'models/hybrid_ltr_model.txt'
                }
            },
            'integration': {
                'semantic_weight': 0.4,
                'cf_weight': 0.3,
                'ltr_weight': 0.3,
                'diversity_enabled': True,
                'diversity_weight': 0.15
            }
        }
    
    def _initialize_ml_engines(self):
        """Initialize all ML engines"""
        # Check if ML engines are available
        if not self.ml_engines_available:
            logger.warning("ML engines not available, hybrid system disabled")
            return
        
        try:
            # Stage 1: Semantic Search Engine (FAISS)
            semantic_config = self.config['stages']['semantic']
            self.semantic_engine = create_faiss_engine(
                semantic_config['engine_type'], 
                semantic_config['dimension']
            )
            logger.info("✅ FAISS semantic engine initialized")
            
            # Stage 2: Collaborative Filtering Engine
            cf_config = self.config['stages']['collaborative']
            self.cf_engine = create_cf_engine(cf_config['engine_type'])
            logger.info("✅ Collaborative filtering engine initialized")
            
            # Stage 3: Learning-to-Rank Engine
            ltr_config = self.config['stages']['learning_to_rank']
            if ltr_config['enabled']:
                model_path = ltr_config['model_path']
                if os.path.exists(model_path):
                    self.ltr_engine = create_ranking_engine(model_path)
                else:
                    self.ltr_engine = create_ranking_engine()
                logger.info("✅ Learning-to-Rank engine initialized")
            else:
                self.ltr_engine = None
            
            logger.info("✅ All ML engines initialized successfully")
            
            # Preload embedding model for faster processing
            self._preload_embedding_model()
            
        except Exception as e:
            logger.error(f"Error initializing ML engines: {e}")
            ML_ENGINES_AVAILABLE = False
    
    def _preload_embedding_model(self):
        """Preload embedding model to avoid delays during processing"""
        try:
            from embedding_utils import get_embedding_model
            model = get_embedding_model()
            if model:
                logger.info("✅ Preloaded global embedding model for faster processing")
                # Test the model to ensure it's working
                test_embedding = model.encode("test")
                logger.info(f"✅ Embedding model test successful: {len(test_embedding)} dimensions")
            else:
                logger.warning("⚠️ Could not preload global embedding model")
        except Exception as e:
            logger.warning(f"⚠️ Could not preload embedding model: {e}")
    
    def execute_hybrid_pipeline(self, request: Dict[str, Any], user_id: int, 
                              content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute the complete 3-stage hybrid pipeline"""
        start_time = time.time()
        
        try:
            logger.info("🚀 Starting 3-stage hybrid recommendation pipeline")
            
            # DEBUG: Log what content we're receiving
            logger.info(f"📊 Received {len(content_list)} content items for ML processing")
            if content_list:
                sample_content = content_list[0]
                logger.info(f"📋 Sample content fields: {list(sample_content.keys())}")
                logger.info(f"📋 Sample content title: '{sample_content.get('title', 'NO_TITLE')}'")
                logger.info(f"📋 Sample content url: '{sample_content.get('url', 'NO_URL')}'")
                logger.info(f"📋 Sample content techs: {len(sample_content.get('technologies', []))}")
            
            # Stage 1: Semantic Candidate Generation
            semantic_result = self._execute_semantic_stage(request, content_list)
            
            # Stage 2: Collaborative Filtering (when interactions exist)
            cf_result = None
            if self.config['stages']['collaborative']['enabled']:
                cf_result = self._execute_collaborative_stage(user_id, content_list)
            
            # Stage 3: Learning-to-Rank for final ordering
            final_recommendations = self._execute_learning_to_rank_stage(
                semantic_result, cf_result, request, user_id
            )
            
            # Apply diversity filtering
            if self.config['integration']['diversity_enabled']:
                final_recommendations = self._apply_diversity_filtering(final_recommendations)
            
            # Update performance metrics
            total_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(total_time, len(final_recommendations))
            
            logger.info(f"✅ Hybrid pipeline completed: {len(final_recommendations)} recommendations in {total_time:.2f}ms")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error in hybrid pipeline: {e}")
            # Fallback to semantic-only recommendations
            return self._get_fallback_recommendations(semantic_result, content_list)
    
    def _execute_semantic_stage(self, request: Dict[str, Any], 
                               content_list: List[Dict[str, Any]]) -> HybridStageResult:
        """Stage 1: Generate semantic candidates using FAISS with REAL user content analysis"""
        stage_start = time.time()
        
        try:
            # CRITICAL FIX: Retrain FAISS with real content IDs before searching
            logger.info("🔄 Retraining FAISS with real content IDs...")
            self._retrain_faiss_with_real_content(content_list)
            
            # Generate query embedding using user's real embedding system
            query_text = f"{request.get('title', '')} {request.get('description', '')} {request.get('technologies', '')}"
            query_embedding = self._generate_query_embedding(query_text)
            
            if query_embedding is None:
                logger.warning("⚠️ Could not generate query embedding, using fallback")
                return self._create_fallback_semantic_result(content_list)
            
            # Search FAISS index for semantic candidates
            max_candidates = self.config['stages']['semantic']['max_candidates']
            search_results = self.semantic_engine.search(query_embedding, k=max_candidates)
            
            # Process results and integrate with user's real content analysis
            candidates = []
            scores = {}
            
            for result in search_results:
                if result.similarity_score >= self.config['stages']['semantic']['min_score']:
                    content_id = result.content_id
                    
                    # Find corresponding content from user's real system
                    content_item = self._find_content_by_id(content_list, content_id)
                    
                    if content_item:
                        logger.info(f"✅ Found content {content_id}: title='{content_item.get('title', 'NO_TITLE')}', techs={len(content_item.get('technologies', []))}")
                        # Enhance with user's real content analysis
                        enhanced_content = self._enhance_content_with_semantic_analysis(
                            content_item, result.similarity_score, request
                        )
                        
                        candidates.append(enhanced_content)
                        scores[content_id] = result.similarity_score
                    else:
                        logger.warning(f"⚠️ Content {content_id} not found in content_list! Available IDs: {[c.get('id') for c in content_list[:5]]}")
                        # Fallback: create basic candidate if content not found
                        candidates.append({
                            'id': content_id,
                            'semantic_score': result.similarity_score,
                            'metadata': result.metadata,
                            'stage': 'semantic',
                            'ml_pipeline_stage': 'semantic'
                        })
                        scores[content_id] = result.similarity_score
            
            stage_time = (time.time() - stage_start) * 1000
            
            result = HybridStageResult(
                stage_name='semantic_search',
                candidates=candidates,
                scores=scores,
                metadata={
                    'query_text': query_text, 
                    'embedding_dim': len(query_embedding),
                    'real_content_integration': True
                },
                execution_time_ms=stage_time
            )
            
            logger.info(f"✅ Stage 1 (Semantic): {len(candidates)} candidates in {stage_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in semantic stage: {e}")
            return self._create_fallback_semantic_result(content_list)
    
    def _enhance_content_with_semantic_analysis(self, content: Dict, similarity_score: float, request: Dict) -> Dict:
        """Enhance content with semantic analysis from user's real system"""
        try:
            # Start with a complete copy of the original content to preserve ALL fields
            enhanced_content = content.copy()
            
            # CRITICAL: Ensure essential content fields are preserved
            enhanced_content.update({
                'id': content.get('id'),
                'title': content.get('title', 'Unknown Title'),
                'url': content.get('url', ''),
                'technologies': content.get('technologies', []),
                'content_type': content.get('content_type', 'unknown'),
                'difficulty': content.get('difficulty', 'unknown'),
                'quality_score': content.get('quality_score', 6),
                'extracted_text': content.get('extracted_text', ''),
                'tags': content.get('tags', ''),
                'description': content.get('description', ''),
                
                # Add semantic analysis scores
                'semantic_score': similarity_score,
                'stage1_score': similarity_score,
                'stage': 'semantic',
                'ml_pipeline_stage': 'semantic'
            })
            
            # Use user's intelligent relevance system if available
            if 'intelligent_relevance_score' in content:
                enhanced_content['user_relevance_score'] = content['intelligent_relevance_score']
            
            # Use user's technology analysis if available
            if 'technology_overlap_score' in content:
                enhanced_content['tech_overlap_score'] = content['technology_overlap_score']
            
            # Use user's content analysis if available
            if 'content_analysis' in content:
                enhanced_content['content_analysis_score'] = content.get('content_analysis', {}).get('quality_score', 0.0) / 10.0
            
            # Use user's project relevance if available
            if 'project_relevance_boost' in content:
                enhanced_content['project_relevance'] = content['project_relevance_boost']
            
            # Use user's content quality if available
            if 'quality_score' in content:
                enhanced_content['content_quality'] = content['quality_score'] / 10.0
            
            # Log what we're preserving for debugging
            logger.info(f"✅ Enhanced content {content.get('id')}: title='{enhanced_content.get('title')}', url='{enhanced_content.get('url')}', techs={len(enhanced_content.get('technologies', []))}")
            
            return enhanced_content
            
        except Exception as e:
            logger.error(f"Error enhancing content with semantic analysis: {e}")
            return content
    
    def _find_content_by_id(self, content_list: List[Dict], content_id: int) -> Optional[Dict]:
        """Find content by ID in user's real content list"""
        try:
            for content in content_list:
                if content.get('id') == content_id:
                    return content
            return None
        except Exception as e:
            logger.error(f"Error finding content by ID: {e}")
            return None
    
    def _execute_collaborative_stage(self, user_id: int, 
                                   content_list: List[Dict[str, Any]]) -> Optional[HybridStageResult]:
        """Stage 2: Generate collaborative filtering candidates"""
        stage_start = time.time()
        
        try:
            # Check if user has enough interactions
            user_stats = self.cf_engine.get_model_performance()
            if user_stats.get('status') != 'trained':
                logger.info("CF model not trained, skipping collaborative filtering")
                return None
            
            # Get CF recommendations
            max_candidates = self.config['stages']['collaborative']['max_candidates']
            min_score = self.config['stages']['collaborative']['min_score']
            
            cf_results = self.cf_engine.get_recommendations(
                user_id, n_recommendations=max_candidates, min_score=min_score
            )
            
            # Process results
            candidates = []
            scores = {}
            
            for result in cf_results:
                content_id = result.content_id
                candidates.append({
                    'id': content_id,
                    'cf_score': result.cf_score,
                    'confidence': result.confidence,
                    'metadata': {
                        'interaction_count': result.interaction_count,
                        'similar_users_count': result.similar_users_count
                    },
                    'stage': 'collaborative'
                })
                scores[content_id] = result.cf_score
            
            stage_time = (time.time() - stage_start) * 1000
            
            result = HybridStageResult(
                stage_name='collaborative_filtering',
                candidates=candidates,
                scores=scores,
                metadata={'user_id': user_id, 'cf_model_type': self.cf_engine.model_type},
                execution_time_ms=stage_time
            )
            
            logger.info(f"✅ Stage 2 (CF): {len(candidates)} candidates in {stage_time:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in collaborative stage: {e}")
            return None
    
    def _execute_learning_to_rank_stage(self, semantic_result: HybridStageResult,
                                      cf_result: Optional[HybridStageResult],
                                      request: Dict[str, Any], user_id: int) -> List[Dict[str, Any]]:
        """Stage 3: Apply Learning-to-Rank for final ordering"""
        stage_start = time.time()
        
        try:
            if not self.ltr_engine:
                logger.info("LTR engine not available, using simple ranking")
                return self._apply_simple_ranking(semantic_result, cf_result, request)
            
            # Merge candidates from both stages
            merged_candidates = self._merge_stage_candidates(semantic_result, cf_result)
            
            if not merged_candidates:
                return []
            
            # Prepare features for LTR
            ltr_features = self._prepare_ltr_features(merged_candidates, request, user_id)
            
            # Apply LTR ranking
            ltr_results = self.ltr_engine.rank_recommendations(
                ltr_features,  # Pass the features directly
                {'user_id': user_id, 'query': request.get('title', '')},
                {'user_id': user_id}
            )
            
            # Convert to final results
            final_results = []
            for result in ltr_results:
                # Find the corresponding candidate
                candidate = merged_candidates.get(result.content_id)
                if not candidate:
                    continue
                
                final_result = {
                    'id': result.content_id,
                    'title': candidate.get('title', 'Unknown Title'),
                    'url': candidate.get('url', ''),
                    'final_score': result.score,  # Use result.score instead of result.ranked_score
                    'semantic_score': candidate.get('semantic_score', 0.0),
                    'cf_score': candidate.get('cf_score', 0.0),
                    'ltr_score': result.score,  # Use result.score
                    'rank_position': getattr(result, 'rank_position', 0),  # Handle missing attribute
                    'recommendation_reason': getattr(result, 'reason', 'ML ranking applied'),
                    'content_type': candidate.get('content_type', 'unknown'),
                    'difficulty': candidate.get('difficulty', 'unknown'),
                    'technologies': candidate.get('technologies', []),
                    'metadata': candidate.get('metadata', {}),
                    'stage': 'learning_to_rank',
                    
                    # CRITICAL: Preserve ALL original content fields
                    'quality_score': candidate.get('quality_score', 6),
                    'extracted_text': candidate.get('extracted_text', ''),
                    'tags': candidate.get('tags', ''),
                    'description': candidate.get('description', ''),
                    'saved_at': candidate.get('saved_at'),
                    'user_id': candidate.get('user_id')
                }
                
                # Log what we're creating for debugging
                logger.info(f"✅ Final result {result.content_id}: title='{final_result['title']}', techs={len(final_result['technologies'])}")
                final_results.append(final_result)
            
            stage_time = (time.time() - stage_start) * 1000
            logger.info(f"✅ Stage 3 (LTR): {len(final_results)} ranked results in {stage_time:.2f}ms")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in LTR stage: {e}")
            return self._apply_simple_ranking(semantic_result, cf_result, request)
    
    def _merge_stage_candidates(self, semantic_result: HybridStageResult,
                               cf_result: Optional[HybridStageResult]) -> Dict[int, Dict[str, Any]]:
        """Merge candidates from different stages"""
        merged = {}
        
        # Add semantic candidates with ALL content fields preserved
        for candidate in semantic_result.candidates:
            content_id = candidate['id']
            merged[content_id] = {
                'id': content_id,
                'semantic_score': candidate['semantic_score'],
                'cf_score': 0.0,
                'stage': 'semantic',
                'metadata': candidate.get('metadata', {}),
                
                # CRITICAL: Preserve ALL original content fields
                'title': candidate.get('title', 'Unknown Title'),
                'url': candidate.get('url', ''),
                'technologies': candidate.get('technologies', []),
                'content_type': candidate.get('content_type', 'unknown'),
                'difficulty': candidate.get('difficulty', 'unknown'),
                'quality_score': candidate.get('quality_score', 6),
                'extracted_text': candidate.get('extracted_text', ''),
                'tags': candidate.get('tags', ''),
                'description': candidate.get('description', ''),
                'saved_at': candidate.get('saved_at'),
                'user_id': candidate.get('user_id')
            }
            
            # Log what we're preserving
            logger.info(f"✅ Merged semantic candidate {content_id}: title='{merged[content_id]['title']}', techs={len(merged[content_id]['technologies'])}")
        
        # Add/update with CF candidates
        if cf_result:
            for candidate in cf_result.candidates:
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
                        'metadata': candidate.get('metadata', {}),
                        
                        # CRITICAL: Preserve ALL original content fields
                        'title': candidate.get('title', 'Unknown Title'),
                        'url': candidate.get('url', ''),
                        'technologies': candidate.get('technologies', []),
                        'content_type': candidate.get('content_type', 'unknown'),
                        'difficulty': candidate.get('difficulty', 'unknown'),
                        'quality_score': candidate.get('quality_score', 6),
                        'extracted_text': candidate.get('extracted_text', ''),
                        'tags': candidate.get('tags', ''),
                        'description': candidate.get('description', ''),
                        'saved_at': candidate.get('saved_at'),
                        'user_id': candidate.get('user_id')
                    }
        
        return merged
    
    def _prepare_ltr_features(self, candidates: Dict[int, Dict], 
                             request: Dict[str, Any], user_id: int) -> List[Dict]:
        """Prepare features for Learning-to-Rank with exact feature mapping"""
        features = []
        
        for candidate in candidates.values():
            # Create feature dict that exactly matches what _extract_training_features_forced expects
            feature_dict = {
                'id': candidate['id'],
                'title': candidate.get('title', 'Unknown'),
                'url': candidate.get('url', ''),
                'intelligent_relevance_score': candidate.get('semantic_score', 0.0),
                'technology_overlap_score': self._calculate_tech_overlap(
                    candidate.get('technologies', []),
                    request.get('technologies', '').split(',') if request.get('technologies') else []
                ),
                'content_type_match_score': self._calculate_content_type_match(
                    candidate.get('content_type'),
                    request.get('content_type_preference')
                ),
                'difficulty_match_score': self._calculate_difficulty_match(
                    candidate.get('difficulty'),
                    request.get('difficulty_preference')
                ),
                'user_engagement_score': candidate.get('metadata', {}).get('user_engagement', 0.5),
                'content_quality_score': candidate.get('metadata', {}).get('quality_score', 0.5),
                'freshness_score': candidate.get('metadata', {}).get('freshness_score', 0.5),
                'diversity_score': candidate.get('metadata', {}).get('diversity_score', 0.5),
                'project_relevance_score': candidate.get('metadata', {}).get('project_relevance', 0.5),
                'learning_stage_match_score': candidate.get('metadata', {}).get('learning_stage_match', 0.5),
                'time_of_day_relevance_score': candidate.get('metadata', {}).get('time_relevance', 0.5),
                'session_context_match_score': candidate.get('metadata', {}).get('session_context', 0.5),
                'cross_technology_relevance_score': candidate.get('metadata', {}).get('cross_tech_relevance', 0.5),
                'functional_purpose_match_score': candidate.get('metadata', {}).get('purpose_match', 0.5),
                'title_query_alignment_score': candidate.get('metadata', {}).get('title_alignment', 0.5),
                'keyword_amplification_score': candidate.get('metadata', {}).get('keyword_relevance', 0.5),
                'recency_score': candidate.get('metadata', {}).get('recency', 0.5),
                'popularity_score': candidate.get('metadata', {}).get('popularity', 0.5),
                'content_length_score': candidate.get('metadata', {}).get('content_length', 0.5),
                'source_credibility_score': candidate.get('metadata', {}).get('credibility', 0.5),
                'cf_score': candidate.get('cf_score', 0.0),
                'semantic_score': candidate.get('semantic_score', 0.0),
                'content_type': candidate.get('content_type', 'unknown'),
                'difficulty': candidate.get('difficulty', 'unknown'),
                'technologies': candidate.get('technologies', []),
                'metadata': candidate.get('metadata', {}),
                'confidence': 0.8
            }
            features.append(feature_dict)
        
        return features
    
    def _apply_simple_ranking(self, semantic_result: HybridStageResult,
                             cf_result: Optional[HybridStageResult],
                             request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback simple ranking when LTR is not available"""
        try:
            # Merge candidates
            merged_candidates = self._merge_stage_candidates(semantic_result, cf_result)
            
            if not merged_candidates:
                return []
            
            # Calculate combined scores
            scored_candidates = []
            semantic_weight = self.config['integration']['semantic_weight']
            cf_weight = self.config['integration']['cf_weight']
            
            for candidate in merged_candidates.values():
                semantic_score = candidate.get('semantic_score', 0.0)
                cf_score = candidate.get('cf_score', 0.0)
                
                # Weighted combination
                combined_score = (semantic_weight * semantic_score) + (cf_weight * cf_score)
                
                scored_candidates.append((candidate, combined_score))
            
            # Sort by combined score
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Convert to final results
            final_results = []
            for i, (candidate, score) in enumerate(scored_candidates):
                final_result = {
                    'id': candidate['id'],
                    'title': candidate.get('title', 'Unknown'),
                    'url': candidate.get('url', ''),
                    'final_score': score,
                    'semantic_score': candidate.get('semantic_score', 0.0),
                    'cf_score': candidate.get('cf_score', 0.0),
                    'ltr_score': score,
                    'rank_position': i + 1,
                    'recommendation_reason': f"Combined score: {score:.3f} (Semantic: {candidate.get('semantic_score', 0.0):.3f}, CF: {candidate.get('cf_score', 0.0):.3f})",
                    'content_type': candidate.get('content_type', 'unknown'),
                    'difficulty': candidate.get('difficulty', 'unknown'),
                    'technologies': candidate.get('technologies', []),
                    'metadata': candidate.get('metadata', {}),
                    'stage': 'simple_ranking'
                }
                final_results.append(final_result)
            
            logger.info(f"✅ Applied simple ranking to {len(final_results)} candidates")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in simple ranking: {e}")
            return []
    
    def _apply_diversity_filtering(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply diversity filtering to final recommendations"""
        if not self.config['integration']['diversity_enabled']:
            return recommendations
        
        try:
            filtered_results = []
            used_technologies = set()
            used_difficulties = set()
            used_content_types = set()
            
            for result in recommendations:
                # Check technology diversity (less aggressive)
                tech_overlap = len(set(result.get('technologies', [])) & used_technologies) / max(len(result.get('technologies', [])), 1)
                if tech_overlap > 0.9:  # Max 90% overlap (was 70%)
                    continue
                
                # Check difficulty diversity (less aggressive)
                difficulty = result.get('difficulty', 'unknown')
                if difficulty in used_difficulties:
                    difficulty_count = sum(1 for r in filtered_results if r.get('difficulty') == difficulty)
                    if difficulty_count > 0 and len(filtered_results) > 0:
                        difficulty_ratio = difficulty_count / len(filtered_results)
                        if difficulty_ratio > 0.9:  # Max 90% same difficulty (was 80%)
                            continue
                
                # Check content type diversity (less aggressive)
                content_type = result.get('content_type', 'unknown')
                if content_type in used_content_types:
                    content_type_count = sum(1 for r in filtered_results if r.get('content_type') == content_type)
                    if content_type_count > 0 and len(filtered_results) > 0:
                        content_type_ratio = content_type_count / len(filtered_results)
                        if content_type_ratio > 0.8:  # Max 80% same content type (was 60%)
                            continue
                
                # Add to filtered results
                filtered_results.append(result)
                used_technologies.update(result.get('technologies', []))
                used_difficulties.add(difficulty)
                used_content_types.add(content_type)
            
            logger.info(f"✅ Applied diversity filtering: {len(recommendations)} -> {len(filtered_results)} results")
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error in diversity filtering: {e}")
            return recommendations
    
    def _generate_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Generate embedding for query with proper tensor handling"""
        try:
            if not self.embedding_model:
                logger.warning("No embedding model available for query embedding")
                return None
            
            # Fix PyTorch meta tensor issue
            try:
                import torch
                # Check if we're dealing with meta tensors
                if hasattr(torch, 'meta') and torch.meta.is_available():
                    # Use to_empty() for meta tensors
                    self.embedding_model = self.embedding_model.to_empty(device='cpu')
                    logger.info("✅ Fixed meta tensor issue with to_empty()")
                else:
                    # Fallback to CPU
                    self.embedding_model = self.embedding_model.to('cpu')
                    logger.info("✅ Using to() for CPU placement")
            except Exception as tensor_error:
                logger.warning(f"Tensor device placement error: {tensor_error}")
                # Continue without device placement
            
            # Generate embedding
            embedding = self.embedding_model.encode([query])
            if embedding is not None and len(embedding) > 0:
                return embedding[0]
            else:
                logger.warning("Embedding generation returned None or empty")
                return None
                
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return None
    
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
    
    def _retrain_faiss_with_real_content(self, content_list: List[Dict[str, Any]]):
        """Retrain FAISS with real content IDs to fix the ID mismatch issue"""
        try:
            if not self.semantic_engine:
                logger.warning("⚠️ Semantic engine not available for retraining")
                return
            
            # Clear existing FAISS index
            logger.info("🧹 Clearing existing FAISS index...")
            self.semantic_engine.clear_index()
            
            # Add real content to FAISS with proper IDs - OPTIMIZED with batch processing
            logger.info(f"📚 Adding {len(content_list)} real content items to FAISS...")
            
            # Prepare batch data for efficient embedding generation
            batch_texts = []
            batch_ids = []
            
            for content in content_list:
                content_id = content.get('id')
                if not content_id:
                    continue
                
                # Prepare content text
                content_text = f"{content.get('title', '')} {content.get('extracted_text', '')} {content.get('tags', '')}"
                if not content_text.strip():
                    continue
                
                batch_texts.append(content_text)
                batch_ids.append(content_id)
            
            if not batch_texts:
                logger.warning("⚠️ No valid content texts found for embedding generation")
                return
            
            # Generate embeddings in BATCH using the global embedding model
            try:
                from embedding_utils import get_embedding_model, generate_embedding
                
                # Get the global embedding model (singleton)
                model = get_embedding_model()
                if model:
                    logger.info(f"🚀 Generating embeddings for {len(batch_texts)} items in batch...")
                    
                    # Generate embeddings in batch (much faster)
                    batch_embeddings = model.encode(batch_texts, batch_size=32, show_progress_bar=True)
                    
                    # Add all embeddings to FAISS at once
                    for i, (content_id, embedding) in enumerate(zip(batch_ids, batch_embeddings)):
                        try:
                            self.semantic_engine.add_vector(embedding.astype(np.float32), content_id)
                            if i % 10 == 0:  # Log progress every 10 items
                                logger.info(f"✅ Added {i+1}/{len(batch_ids)} content items to FAISS")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not add content {content_id} to FAISS: {e}")
                            continue
                    
                    logger.info(f"✅ FAISS retrained with {len(batch_ids)} real content items in batch")
                else:
                    logger.warning("⚠️ Global embedding model not available, falling back to individual processing")
                    self._fallback_individual_embedding_generation(content_list)
                    
            except ImportError:
                logger.warning("⚠️ embedding_utils not available, falling back to individual processing")
                self._fallback_individual_embedding_generation(content_list)
            
        except Exception as e:
            logger.error(f"Error retraining FAISS: {e}")
    
    def _fallback_individual_embedding_generation(self, content_list: List[Dict[str, Any]]):
        """Fallback method for individual embedding generation when batch processing fails"""
        logger.info("🔄 Using fallback individual embedding generation...")
        
        for content in content_list:
            content_id = content.get('id')
            if not content_id:
                continue
            
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')} {content.get('tags', '')}"
            if not content_text.strip():
                continue
            
            try:
                content_embedding = self._generate_query_embedding(content_text)
                if content_embedding is not None:
                    self.semantic_engine.add_vector(content_embedding, content_id)
            except Exception as e:
                logger.warning(f"⚠️ Could not add content {content_id} to FAISS: {e}")
                continue
    
    def _create_fallback_semantic_result(self, content_list: List[Dict[str, Any]]) -> HybridStageResult:
        """Create fallback semantic result when FAISS fails"""
        candidates = []
        scores = {}
        
        for i, content in enumerate(content_list[:100]):  # Limit to 100
            content_id = content.get('id', i)
            candidates.append({
                'id': content_id,
                'semantic_score': 0.5,  # Default score
                'metadata': {},
                'stage': 'semantic_fallback',
                'title': content.get('title', ''),
                'url': content.get('url', ''),
                'content_type': content.get('content_type', 'unknown'),
                'difficulty': content.get('difficulty', 'unknown'),
                'technologies': content.get('technologies', [])
            })
            scores[content_id] = 0.5
        
        return HybridStageResult(
            stage_name='semantic_fallback',
            candidates=candidates,
            scores=scores,
            metadata={'fallback': True},
            execution_time_ms=0.0
        )
    
    def _get_fallback_recommendations(self, semantic_result: HybridStageResult,
                                    content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get fallback recommendations when pipeline fails"""
        try:
            candidates = semantic_result.candidates[:20]  # Limit to 20
            
            final_results = []
            for i, candidate in enumerate(candidates):
                final_result = {
                    'id': candidate['id'],
                    'title': candidate.get('title', 'Unknown'),
                    'url': candidate.get('url', ''),
                    'final_score': candidate.get('semantic_score', 0.5),
                    'semantic_score': candidate.get('semantic_score', 0.5),
                    'cf_score': 0.0,
                    'ltr_score': candidate.get('semantic_score', 0.5),
                    'rank_position': i + 1,
                    'recommendation_reason': 'Fallback recommendation (pipeline error)',
                    'content_type': candidate.get('content_type', 'unknown'),
                    'difficulty': candidate.get('difficulty', 'unknown'),
                    'technologies': candidate.get('technologies', []),
                    'metadata': candidate.get('metadata', {}),
                    'stage': 'fallback'
                }
                final_results.append(final_result)
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in fallback recommendations: {e}")
            return []
    
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
            
            return {
                'total_recommendations': self.total_recommendations,
                'recent_avg_time_ms': avg_time,
                'recent_avg_results': avg_results,
                'ml_engines_available': self.ml_engines_available,
                'stages_enabled': {
                    'semantic': self.config['stages']['semantic']['enabled'],
                    'collaborative': self.config['stages']['collaborative']['enabled'],
                    'learning_to_rank': self.config['stages']['learning_to_rank']['enabled']
                }
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

# Factory function
def create_hybrid_integration(config: Optional[Dict[str, Any]] = None) -> HybridOrchestratorIntegration:
    """Create a hybrid orchestrator integration instance"""
    return HybridOrchestratorIntegration(config)

