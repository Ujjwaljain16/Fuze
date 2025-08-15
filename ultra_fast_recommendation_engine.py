#!/usr/bin/env python3
"""
Ultra-Fast Recommendation Engine
Fixes the 7.52s recommendation computation time
Uses vector similarity search and optimized caching
"""

import time
import numpy as np
import logging
from typing import List, Dict, Optional, Any
from functools import lru_cache
from sqlalchemy import text, func
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraFastRecommendationEngine:
    """Ultra-fast recommendation engine using vector similarity search"""
    
    def __init__(self):
        self.cache_duration = 1800  # 30 minutes
        self.max_recommendations = 10
        self.similarity_threshold = 0.3
        self.batch_size = 100
        self.embedding_model = None
        self._init_embedding_model()
        
    def _init_embedding_model(self):
        """Initialize embedding model with error handling"""
        try:
            import torch
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Handle meta tensors properly
            if hasattr(torch, 'meta') and torch.meta.is_available():
                self.embedding_model = self.embedding_model.to_empty(device='cpu')
            else:
                self.embedding_model = self.embedding_model.to('cpu')
                
            logger.info("✅ Embedding model initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize embedding model: {e}")
            self.embedding_model = None
    
    @lru_cache(maxsize=1000)
    def _get_user_profile_vector(self, user_id: int) -> Optional[np.ndarray]:
        """Get cached user profile vector"""
        try:
            from models import SavedContent
            from redis_utils import redis_cache
            
            # Check cache first
            cache_key = f"user_profile_vector:{user_id}"
            cached_vector = redis_cache.get_cache(cache_key)
            if cached_vector is not None:
                return np.array(cached_vector)
            
            # Get user's bookmarks with embeddings
            user_bookmarks = SavedContent.query.filter(
                SavedContent.user_id == user_id,
                SavedContent.embedding.isnot(None)
            ).limit(50).all()  # Limit to top 50 for performance
            
            if not user_bookmarks:
                return None
            
            # Average user's bookmark embeddings
            embeddings = [np.array(bm.embedding) for bm in user_bookmarks if bm.embedding]
            if not embeddings:
                return None
            
            user_profile = np.mean(embeddings, axis=0)
            user_profile = user_profile / (np.linalg.norm(user_profile) + 1e-8)  # Normalize
            
            # Cache for 1 hour
            redis_cache.set_cache(cache_key, user_profile.tolist(), ttl=3600)
            
            return user_profile
            
        except Exception as e:
            logger.error(f"Error getting user profile vector: {e}")
            return None
    
    def _get_candidate_content(self, user_id: int, limit: int = 100) -> List[Any]:
        """Get candidate content with optimized querying"""
        try:
            from models import SavedContent
            
            # Use optimized query with indexes
            candidates = SavedContent.query.filter(
                SavedContent.quality_score >= 6,  # Quality threshold
                SavedContent.embedding.isnot(None),
                SavedContent.user_id != user_id  # Exclude user's own content
            ).order_by(
                SavedContent.quality_score.desc(),
                SavedContent.saved_at.desc()
            ).limit(limit).all()
            
            return candidates
            
        except Exception as e:
            logger.error(f"Error getting candidate content: {e}")
            return []
    
    def _compute_vector_similarities(self, user_profile: np.ndarray, 
                                   candidates: List[Any]) -> List[float]:
        """Compute vector similarities using optimized numpy operations"""
        try:
            if not candidates:
                return []
            
            # Extract embeddings as numpy array
            candidate_embeddings = []
            valid_candidates = []
            
            for candidate in candidates:
                if candidate.embedding is not None:
                    candidate_embeddings.append(np.array(candidate.embedding))
                    valid_candidates.append(candidate)
            
            if not candidate_embeddings:
                return []
            
            # Convert to numpy array for batch processing
            candidate_embeddings = np.stack(candidate_embeddings)
            
            # Normalize embeddings
            candidate_embeddings = candidate_embeddings / (
                np.linalg.norm(candidate_embeddings, axis=1, keepdims=True) + 1e-8
            )
            
            # Compute cosine similarities (vectorized)
            similarities = np.dot(candidate_embeddings, user_profile)
            
            # Update candidates list to only include valid ones
            candidates[:] = valid_candidates
            
            return similarities.tolist()
            
        except Exception as e:
            logger.error(f"Error computing similarities: {e}")
            return []
    
    def _rank_recommendations(self, candidates: List[Any], 
                            similarities: List[float]) -> List[Dict]:
        """Rank recommendations by similarity and quality"""
        try:
            if not candidates or not similarities:
                return []
            
            # Create recommendation objects
            recommendations = []
            for i, (candidate, similarity) in enumerate(zip(candidates, similarities)):
                if similarity >= self.similarity_threshold:
                    recommendations.append({
                        'id': candidate.id,
                        'title': candidate.title,
                        'url': candidate.url,
                        'similarity_score': float(similarity),
                        'quality_score': candidate.quality_score or 6.0,
                        'content_type': getattr(candidate, 'content_type', 'article'),
                        'difficulty': getattr(candidate, 'difficulty', 'intermediate'),
                        'technologies': candidate.tags or '',
                        'key_concepts': getattr(candidate, 'key_concepts', ''),
                        'reason': f"High similarity ({similarity:.2f}) and quality ({candidate.quality_score or 6.0})",
                        'engine_used': 'UltraFastRecommendationEngine',
                        'confidence': min(similarity * 100, 95),
                        'metadata': {
                            'processing_time_ms': 0,
                            'vector_search': True,
                            'optimized': True
                        }
                    })
            
            # Sort by similarity score (descending)
            recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return recommendations[:self.max_recommendations]
            
        except Exception as e:
            logger.error(f"Error ranking recommendations: {e}")
            return []
    
    def get_ultra_fast_recommendations(self, user_id: int, 
                                     user_input: Optional[Dict] = None) -> Dict:
        """Get ultra-fast recommendations using vector similarity search"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"ultra_fast_recommendations:{user_id}"
            from redis_utils import redis_cache
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
            
            # Get user profile vector
            user_profile = self._get_user_profile_vector(user_id)
            if user_profile is None:
                return {
                    'recommendations': [],
                    'cached': False,
                    'computation_time_ms': 0,
                    'message': 'No user profile available',
                    'engine_used': 'UltraFastRecommendationEngine'
                }
            
            # Get candidate content
            candidates = self._get_candidate_content(user_id, limit=self.batch_size)
            if not candidates:
                return {
                    'recommendations': [],
                    'cached': False,
                    'computation_time_ms': 0,
                    'message': 'No candidate content available',
                    'engine_used': 'UltraFastRecommendationEngine'
                }
            
            # Compute vector similarities
            similarities = self._compute_vector_similarities(user_profile, candidates)
            
            # Rank recommendations
            recommendations = self._rank_recommendations(candidates, similarities)
            
            # Calculate performance metrics
            computation_time = (time.time() - start_time) * 1000
            
            result = {
                'recommendations': recommendations,
                'total_recommendations': len(recommendations),
                'cached': False,
                'computation_time_ms': computation_time,
                'performance_metrics': {
                    'vector_search_used': True,
                    'candidates_processed': len(candidates),
                    'similarity_threshold': self.similarity_threshold,
                    'batch_size': self.batch_size,
                    'optimization_level': 'ultra_fast'
                },
                'engine_used': 'UltraFastRecommendationEngine',
                'message': f'Generated {len(recommendations)} recommendations in {computation_time:.1f}ms'
            }
            
            # Cache results
            redis_cache.set_cache(cache_key, result, ttl=self.cache_duration)
            
            logger.info(f"Ultra-fast recommendations: {computation_time:.1f}ms for {len(recommendations)} results")
            
            return result
            
        except Exception as e:
            computation_time = (time.time() - start_time) * 1000
            logger.error(f"Error in ultra-fast recommendations: {e}")
            
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': computation_time,
                'error': str(e),
                'engine_used': 'UltraFastRecommendationEngine'
            }
    
    def get_project_recommendations(self, user_id: int, project_id: int) -> Dict:
        """Get project-specific recommendations"""
        try:
            from models import Project
            
            # Get project details
            project = Project.query.filter_by(id=project_id, user_id=user_id).first()
            if not project:
                return {'error': 'Project not found'}
            
            # Create project context vector
            project_text = f"{project.title} {project.description or ''} {project.technologies or ''}"
            
            if self.embedding_model:
                project_embedding = self.embedding_model.encode([project_text])[0]
                project_embedding = project_embedding / (np.linalg.norm(project_embedding) + 1e-8)
                
                # Get candidates and compute similarities
                candidates = self._get_candidate_content(user_id, limit=self.batch_size)
                similarities = self._compute_vector_similarities(project_embedding, candidates)
                
                # Rank recommendations
                recommendations = self._rank_recommendations(candidates, similarities)
                
                return {
                    'recommendations': recommendations,
                    'project_id': project_id,
                    'project_title': project.title,
                    'engine_used': 'UltraFastRecommendationEngine'
                }
            else:
                # Fallback to regular recommendations
                return self.get_ultra_fast_recommendations(user_id)
                
        except Exception as e:
            logger.error(f"Error in project recommendations: {e}")
            return {'error': str(e)}

# Global instance
ultra_fast_engine = UltraFastRecommendationEngine()

def get_ultra_fast_engine():
    """Get global ultra-fast engine instance"""
    return ultra_fast_engine
