#!/usr/bin/env python3
"""
Optimized Recommendation Engine for Fuze
Addresses the remaining performance bottlenecks
"""

import time
import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from models import SavedContent, User, Feedback
from redis_utils import redis_cache
from sqlalchemy import text, func
import pickle

class OptimizedRecommendationEngine:
    """Highly optimized recommendation engine"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.cache_duration = 3600  # 1 hour
        self.max_recommendations = 10
        self.batch_size = 50
        self.similarity_threshold = 0.2
        
    @lru_cache(maxsize=100)
    def get_user_profile(self, user_id):
        """Get cached user profile with bookmarks"""
        cache_key = f"user_profile:{user_id}"
        cached = redis_cache.get_cache(cache_key)
        if cached is not None:
            return cached
            
        # Import here to avoid circular import
        from app import app, db
        
        with app.app_context():
            # Get user's bookmarks with optimized query
            bookmarks = db.session.execute(text("""
                SELECT extracted_text, embedding, quality_score 
                FROM saved_content 
                WHERE user_id = :user_id AND embedding IS NOT NULL
                ORDER BY quality_score DESC 
                LIMIT 20
            """), {'user_id': user_id}).fetchall()
            
            if bookmarks is None or len(bookmarks) == 0:
                return None
                
            # Create user profile from bookmarks
            profile_embeddings = []
            weights = []
            
            for bookmark in bookmarks:
                if bookmark.embedding:
                    # Parse embedding if it's a string
                    if isinstance(bookmark.embedding, str):
                        try:
                            # Remove brackets and split by comma
                            embedding_str = bookmark.embedding.strip('[]')
                            embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                            embedding_array = np.array(embedding_values, dtype=np.float32)
                        except:
                            continue
                    else:
                        embedding_array = np.array(bookmark.embedding, dtype=np.float32)
                    
                    profile_embeddings.append(embedding_array)
                    weights.append(bookmark.quality_score)
            
            if len(profile_embeddings) == 0:
                return None
                
            # Weighted average of embeddings
            profile_embeddings = np.array(profile_embeddings, dtype=np.float32)
            weights = np.array(weights, dtype=np.float32)
            profile_embedding = np.average(profile_embeddings, axis=0, weights=weights)
            profile_embedding = profile_embedding / np.linalg.norm(profile_embedding)
            
            # Cache for 1 hour
            redis_cache.set_cache(cache_key, profile_embedding, self.cache_duration)
            return profile_embedding
    
    def get_candidate_content(self, user_id, limit=100):
        """Get candidate content with optimized query"""
        cache_key = f"candidates:{user_id}"
        cached = redis_cache.get_cache(cache_key)
        if cached is not None:
            return cached
            
        # Import here to avoid circular import
        from app import app, db
        
        with app.app_context():
            # Optimized query using indexes
            raw_candidates = db.session.execute(text("""
                SELECT id, extracted_text, embedding, quality_score, user_id
                FROM saved_content 
                WHERE embedding IS NOT NULL 
                AND user_id != :user_id
                AND quality_score >= 5
                ORDER BY quality_score DESC, id DESC
                LIMIT :limit
            """), {'user_id': user_id, 'limit': limit}).fetchall()
            
            # Convert to objects with attributes
            candidates = []
            for row in raw_candidates:
                candidate = type('Candidate', (), {
                    'id': row[0],
                    'extracted_text': row[1],
                    'embedding': row[2],
                    'quality_score': row[3],
                    'user_id': row[4]
                })()
                candidates.append(candidate)
            
            # Cache for 30 minutes
            redis_cache.set_cache(cache_key, candidates, 1800)
            return candidates
    
    def compute_similarities_batch(self, user_profile, candidates):
        """Compute similarities in batches for better performance"""
        if user_profile is None or candidates is None or len(candidates) == 0:
            return []
            
        similarities = []
        
        # Process in batches
        for i in range(0, len(candidates), self.batch_size):
            batch = candidates[i:i + self.batch_size]
            batch_embeddings = [c.embedding for c in batch if c.embedding]
            
            if len(batch_embeddings) == 0:
                continue
                
            # Compute similarities
            batch_similarities = []
            for embedding in batch_embeddings:
                # Parse embedding if it's a string
                if isinstance(embedding, str):
                    try:
                        embedding_str = embedding.strip('[]')
                        embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                        embedding_array = np.array(embedding_values, dtype=np.float32)
                    except:
                        continue
                else:
                    embedding_array = np.array(embedding, dtype=np.float32)
                
                similarity = np.dot(user_profile, embedding_array)
                batch_similarities.append(similarity)
            
            similarities.extend(batch_similarities)
        
        return similarities
    
    def get_recommendations(self, user_id, use_cache=True):
        """Get optimized recommendations"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"opt_recommendations:{user_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        # Get user profile
        user_profile = self.get_user_profile(user_id)
        if user_profile is None:
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': 'No user profile available'
            }
        
        # Get candidate content
        candidates = self.get_candidate_content(user_id)
        if candidates is None or len(candidates) == 0:
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': 'No candidate content available'
            }
        
        # Compute similarities
        similarities = self.compute_similarities_batch(user_profile, candidates)
        
        # Rank and filter recommendations
        recommendations = []
        for i, (candidate, similarity) in enumerate(zip(candidates, similarities)):
            if similarity >= self.similarity_threshold:
                recommendations.append({
                    'id': candidate.id,
                    'content': candidate.extracted_text,
                    'similarity_score': float(similarity),
                    'quality_score': candidate.quality_score,
                    'user_id': candidate.user_id
                })
        
        # Sort by similarity and quality
        recommendations.sort(key=lambda x: (x['similarity_score'], x['quality_score']), reverse=True)
        recommendations = recommendations[:self.max_recommendations]
        
        computation_time = (time.time() - start_time) * 1000
        
        result = {
            'recommendations': recommendations,
            'cached': False,
            'computation_time_ms': computation_time,
            'total_candidates': len(candidates),
            'similarity_threshold': self.similarity_threshold
        }
        
        # Cache result
        if use_cache:
            cache_key = f"opt_recommendations:{user_id}"
            redis_cache.set_cache(cache_key, result, self.cache_duration)
        
        return result
    
    def get_project_recommendations(self, user_id, project_id, use_cache=True):
        """Get project-specific recommendations"""
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = f"opt_project_recommendations:{user_id}:{project_id}"
            cached_result = redis_cache.get_cache(cache_key)
            if cached_result:
                cached_result['cached'] = True
                cached_result['computation_time_ms'] = 0
                return cached_result
        
        # Import here to avoid circular import
        from app import app, db
        
        # Get project content - since there's no project_id column, we'll get user's content
        with app.app_context():
            project_content = db.session.execute(text("""
                SELECT extracted_text, embedding, quality_score
                FROM saved_content 
                WHERE user_id = :user_id 
                AND embedding IS NOT NULL
                ORDER BY quality_score DESC
                LIMIT 10
            """), {'user_id': user_id}).fetchall()
        
        if project_content is None or len(project_content) == 0:
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': 'No project content available'
            }
        
        # Create project profile
        project_embeddings = []
        for pc in project_content:
            if pc.embedding:
                # Parse embedding if it's a string
                if isinstance(pc.embedding, str):
                    try:
                        embedding_str = pc.embedding.strip('[]')
                        embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                        embedding_array = np.array(embedding_values, dtype=np.float32)
                        project_embeddings.append(embedding_array)
                    except:
                        continue
                else:
                    embedding_array = np.array(pc.embedding, dtype=np.float32)
                    project_embeddings.append(embedding_array)
        
        if len(project_embeddings) == 0:
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': 'No project embeddings available'
            }
        
        project_embeddings = np.array(project_embeddings, dtype=np.float32)
        project_profile = np.mean(project_embeddings, axis=0)
        project_profile = project_profile / np.linalg.norm(project_profile)
        
        # Get candidates (exclude user's own content)
        candidates = self.get_candidate_content(user_id)
        if candidates is None:
            candidates = []
        candidates = [c for c in candidates if c.user_id != user_id]
        
        # Compute similarities
        similarities = self.compute_similarities_batch(project_profile, candidates)
        
        # Rank recommendations
        recommendations = []
        for i, (candidate, similarity) in enumerate(zip(candidates, similarities)):
            if similarity >= self.similarity_threshold:
                recommendations.append({
                    'id': candidate.id,
                    'content': candidate.extracted_text,
                    'similarity_score': float(similarity),
                    'quality_score': candidate.quality_score,
                    'user_id': candidate.user_id
                })
        
        recommendations.sort(key=lambda x: (x['similarity_score'], x['quality_score']), reverse=True)
        recommendations = recommendations[:self.max_recommendations]
        
        computation_time = (time.time() - start_time) * 1000
        
        result = {
            'recommendations': recommendations,
            'cached': False,
            'computation_time_ms': computation_time,
            'project_id': project_id,
            'total_candidates': len(candidates)
        }
        
        # Cache result
        if use_cache:
            cache_key = f"opt_project_recommendations:{user_id}:{project_id}"
            redis_cache.set_cache(cache_key, result, self.cache_duration)
        
        return result
    
    def invalidate_cache(self, user_id):
        """Invalidate user's cached data"""
        keys_to_delete = [
            f"user_profile:{user_id}",
            f"candidates:{user_id}",
            f"opt_recommendations:{user_id}",
            f"opt_project_recommendations:{user_id}:*"
        ]
        
        for key in keys_to_delete:
            redis_cache.delete_cache(key)

# Global instance
optimized_engine = OptimizedRecommendationEngine()

def get_optimized_recommendations(user_id, use_cache=True):
    """Get optimized recommendations"""
    return optimized_engine.get_recommendations(user_id, use_cache)

def get_optimized_project_recommendations(user_id, project_id, use_cache=True):
    """Get optimized project recommendations"""
    return optimized_engine.get_project_recommendations(user_id, project_id, use_cache)

def invalidate_optimized_cache(user_id):
    """Invalidate optimized cache for user"""
    optimized_engine.invalidate_cache(user_id) 