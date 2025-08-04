#!/usr/bin/env python3
"""
Simple Optimized Recommendation Engine for Fuze
Simplified version to get basic functionality working
"""

import time
import numpy as np
from sentence_transformers import SentenceTransformer
from models import SavedContent, User, Feedback
from redis_utils import redis_cache
from sqlalchemy import text, func
import pickle

class SimpleOptimizedEngine:
    """Simple optimized recommendation engine"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.max_recommendations = 10
        self.similarity_threshold = 0.2
        
    def parse_embedding(self, embedding_data):
        """Parse embedding from string or array"""
        if embedding_data is None:
            return None
            
        if isinstance(embedding_data, str):
            try:
                # Remove brackets and split by comma
                embedding_str = embedding_data.strip('[]')
                embedding_values = [float(x.strip()) for x in embedding_str.split(',')]
                return np.array(embedding_values, dtype=np.float32)
            except:
                return None
        elif isinstance(embedding_data, (list, np.ndarray)):
            return np.array(embedding_data, dtype=np.float32)
        else:
            return None
    
    def get_user_profile(self, user_id):
        """Get user profile from bookmarks"""
        from app import app, db
        
        with app.app_context():
            # Get user's bookmarks
            bookmarks = db.session.execute(text("""
                SELECT extracted_text, embedding, quality_score 
                FROM saved_content 
                WHERE user_id = :user_id AND embedding IS NOT NULL
                ORDER BY quality_score DESC 
                LIMIT 20
            """), {'user_id': user_id}).fetchall()
            
            if not bookmarks:
                return None
                
            # Create user profile from bookmarks
            profile_embeddings = []
            weights = []
            
            for bookmark in bookmarks:
                embedding = self.parse_embedding(bookmark[1])  # embedding is at index 1
                if embedding is not None:
                    profile_embeddings.append(embedding)
                    weights.append(bookmark[2])  # quality_score is at index 2
            
            if not profile_embeddings:
                return None
                
            # Weighted average of embeddings
            profile_embeddings = np.array(profile_embeddings, dtype=np.float32)
            weights = np.array(weights, dtype=np.float32)
            profile_embedding = np.average(profile_embeddings, axis=0, weights=weights)
            profile_embedding = profile_embedding / np.linalg.norm(profile_embedding)
            
            return profile_embedding
    
    def get_candidate_content(self, user_id, limit=100):
        """Get candidate content"""
        from app import app, db
        
        with app.app_context():
            # Get candidates
            candidates = db.session.execute(text("""
                SELECT id, extracted_text, embedding, quality_score, user_id
                FROM saved_content 
                WHERE embedding IS NOT NULL 
                AND user_id != :user_id
                AND quality_score >= 5
                ORDER BY quality_score DESC, id DESC
                LIMIT :limit
            """), {'user_id': user_id, 'limit': limit}).fetchall()
            
            return candidates
    
    def compute_similarities(self, user_profile, candidates):
        """Compute similarities between user profile and candidates"""
        if user_profile is None or candidates is None or len(candidates) == 0:
            return []
            
        similarities = []
        
        for candidate in candidates:
            embedding = self.parse_embedding(candidate[2])  # embedding is at index 2
            if embedding is not None:
                similarity = np.dot(user_profile, embedding)
                similarities.append(similarity)
            else:
                similarities.append(0.0)
        
        return similarities
    
    def get_recommendations(self, user_id, use_cache=True):
        """Get optimized recommendations"""
        start_time = time.time()
        
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
        similarities = self.compute_similarities(user_profile, candidates)
        
        # Rank and filter recommendations
        recommendations = []
        for i, (candidate, similarity) in enumerate(zip(candidates, similarities)):
            if similarity >= self.similarity_threshold:
                recommendations.append({
                    'id': candidate[0],  # id
                    'content': candidate[1],  # extracted_text
                    'similarity_score': float(similarity),
                    'quality_score': candidate[3],  # quality_score
                    'user_id': candidate[4]  # user_id
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
        
        return result
    
    def get_project_recommendations(self, user_id, project_id, use_cache=True):
        """Get project-specific recommendations"""
        start_time = time.time()
        
        from app import app, db
        
        with app.app_context():
            # Get project content (user's content since no project_id column)
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
            embedding = self.parse_embedding(pc[1])  # embedding is at index 1
            if embedding is not None:
                project_embeddings.append(embedding)
        
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
        if candidates is None or len(candidates) == 0:
            return {
                'recommendations': [],
                'cached': False,
                'computation_time_ms': 0,
                'message': 'No candidates available'
            }
        
        # Compute similarities
        similarities = self.compute_similarities(project_profile, candidates)
        
        # Rank recommendations
        recommendations = []
        for i, (candidate, similarity) in enumerate(zip(candidates, similarities)):
            if similarity >= self.similarity_threshold:
                recommendations.append({
                    'id': candidate[0],  # id
                    'content': candidate[1],  # extracted_text
                    'similarity_score': float(similarity),
                    'quality_score': candidate[3],  # quality_score
                    'user_id': candidate[4]  # user_id
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
        
        return result

# Global instance
simple_engine = SimpleOptimizedEngine()

def get_simple_recommendations(user_id, use_cache=True):
    """Get simple optimized recommendations"""
    return simple_engine.get_recommendations(user_id, use_cache)

def get_simple_project_recommendations(user_id, project_id, use_cache=True):
    """Get simple optimized project recommendations"""
    return simple_engine.get_project_recommendations(user_id, project_id, use_cache) 