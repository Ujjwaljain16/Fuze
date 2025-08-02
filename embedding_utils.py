from sentence_transformers import SentenceTransformer
import numpy as np
from redis_utils import redis_cache

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    """Get embedding for text with Redis caching"""
    if not text:
        return np.zeros(384)
    
    # Check Redis cache first
    cached_embedding = redis_cache.get_cached_embedding(text)
    if cached_embedding is not None:
        return cached_embedding
    
    # Generate embedding if not cached
    embedding = embedding_model.encode([text])[0]
    
    # Cache the embedding for future use
    redis_cache.cache_embedding(text, embedding)
    
    return embedding 