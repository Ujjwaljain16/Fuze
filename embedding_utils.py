from sentence_transformers import SentenceTransformer
import numpy as np
from redis_utils import redis_cache
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

import torch
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Fix meta tensor issue by using to_empty() instead of to()
if hasattr(torch, 'meta') and torch.meta.is_available():
    # Use to_empty() for meta tensors
    embedding_model = embedding_model.to_empty(device='cpu')
else:
    # Fallback to CPU
    embedding_model = embedding_model.to('cpu')

def get_embedding(text):
    """Get embedding for text with Redis caching"""
    if not text:
        return np.zeros(384)
    
    # Check Redis cache first
    cached_embedding = redis_cache.get_cached_embedding(text)
    if cached_embedding is not None:
        return cached_embedding
    
    # Generate embedding if not cached
    try:
        embedding = embedding_model.encode([text])[0]
        
        # Cache the embedding for future use
        redis_cache.cache_embedding(text, embedding)
        
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding for text: {e}")
        return np.zeros(384)

def calculate_cosine_similarity(embedding1, embedding2):
    """Calculate cosine similarity between two embeddings"""
    try:
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        # Ensure embeddings are 2D arrays for cosine_similarity
        if embedding1.ndim == 1:
            embedding1 = embedding1.reshape(1, -1)
        if embedding2.ndim == 1:
            embedding2 = embedding2.reshape(1, -1)
        
        similarity = cosine_similarity(embedding1, embedding2)[0][0]
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return 0.0

def get_content_embedding(content):
    """Get embedding for content combining title and text"""
    try:
        if not content:
            return np.zeros(384)
        
        # Combine title and text for better representation
        title = content.title or ""
        text = content.extracted_text or ""
        notes = content.notes or ""
        tags = content.tags or ""
        
        # Create comprehensive text representation
        combined_text = f"{title} {text[:1000]} {notes} {tags}".strip()
        
        if not combined_text:
            return np.zeros(384)
        
        return get_embedding(combined_text)
    except Exception as e:
        logger.error(f"Error getting content embedding: {e}")
        return np.zeros(384)

def get_user_profile_embedding(user_profile):
    """Get embedding for user profile combining interests and technologies"""
    try:
        if not user_profile:
            return np.zeros(384)
        
        # Extract profile components
        interests = user_profile.get('interests', [])
        technologies = user_profile.get('technologies', [])
        learning_goals = user_profile.get('learning_goals', [])
        
        # Combine into text representation
        profile_text = " ".join([
            " ".join(interests),
            " ".join(technologies),
            " ".join(learning_goals)
        ]).strip()
        
        if not profile_text:
            return np.zeros(384)
        
        return get_embedding(profile_text)
    except Exception as e:
        logger.error(f"Error getting user profile embedding: {e}")
        return np.zeros(384)

def get_project_embedding(project):
    """Get embedding for project combining title, description, and technologies"""
    try:
        if not project:
            return np.zeros(384)
        
        # Extract project components
        title = project.title or ""
        description = project.description or ""
        technologies = project.technologies or ""
        
        # Combine into text representation
        project_text = f"{title} {description} {technologies}".strip()
        
        if not project_text:
            return np.zeros(384)
        
        return get_embedding(project_text)
    except Exception as e:
        logger.error(f"Error getting project embedding: {e}")
        return np.zeros(384)

def get_task_embedding(task):
    """Get embedding for task combining title, description, and tags"""
    try:
        if not task:
            return np.zeros(384)
        
        # Extract task components
        title = task.title or ""
        description = task.description or ""
        tags = task.tags or ""
        
        # Combine into text representation
        task_text = f"{title} {description} {tags}".strip()
        
        if not task_text:
            return np.zeros(384)
        
        return get_embedding(task_text)
    except Exception as e:
        logger.error(f"Error getting task embedding: {e}")
        return np.zeros(384) 