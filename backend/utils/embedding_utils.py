from sentence_transformers import SentenceTransformer
import numpy as np
from .redis_utils import redis_cache
from sklearn.metrics.pairwise import cosine_similarity
import logging
import os
import shutil

logger = logging.getLogger(__name__)

# Singleton pattern for embedding model
_embedding_model = None
_embedding_model_initialized = False

def get_embedding_model():
    """Get or create the embedding model singleton with robust initialization"""
    global _embedding_model, _embedding_model_initialized
    
    if not _embedding_model_initialized:
        _embedding_model = _initialize_embedding_model_robust()
        _embedding_model_initialized = True
    
    return _embedding_model

def _initialize_embedding_model_robust():
    """Robust embedding model initialization with multiple fallbacks"""
    
    # Optimize memory usage for torch
    try:
        import torch
        import os
        # Set environment variables to reduce memory usage
        os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'max_split_size_mb:128')
        # Disable CUDA if available to save memory (we're using CPU anyway)
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
    except ImportError:
        pass
    
    # Model options in order of preference (size vs quality)
    # Prioritize smaller models for memory-constrained environments
    model_options = [
        'paraphrase-MiniLM-L3-v2', # Good quality, ~60MB (smallest, best for memory)
        'all-MiniLM-L3-v2',        # Decent quality, ~60MB
        'all-MiniLM-L6-v2',        # Best quality, ~90MB
        'paraphrase-MiniLM-L6-v2'  # Good quality, ~90MB
    ]
    
    for model_name in model_options:
        try:
            logger.info(f"🔄 Attempting to load embedding model: {model_name}")
            
            # Clear any corrupted cache for this model
            _clear_model_cache_if_needed(model_name)
            
            # Initialize the model
            model = SentenceTransformer(model_name)
            
            # Handle device placement
            try:
                import torch
                if hasattr(torch, 'meta') and torch.meta.is_available():
                    model = model.to_empty(device='cpu')
                    logger.info(f"✅ Model {model_name} loaded with to_empty() for meta tensors")
                else:
                    model = model.to('cpu')
                    logger.info(f"✅ Model {model_name} loaded with to() for CPU")
            except Exception as tensor_error:
                logger.warning(f"Tensor device placement error: {tensor_error}")
                logger.info(f"Using model {model_name} without device placement")
            
            # Test the model with a simple encoding
            test_text = "test"
            test_embedding = model.encode([test_text])
            if test_embedding is not None and len(test_embedding) > 0:
                logger.info(f"🎉 Successfully loaded and tested embedding model: {model_name}")
                return model
            else:
                logger.warning(f"Model {model_name} loaded but failed test encoding")
                
        except Exception as e:
            logger.warning(f"Failed to load model {model_name}: {e}")
            continue
    
    # If all models fail, create a robust fallback
    logger.error("❌ All embedding models failed to load. Creating robust fallback.")
    return _create_robust_fallback_embedding()

def _clear_model_cache_if_needed(model_name):
    """Clear corrupted model cache if needed"""
    try:
        import torch
        cache_dir = torch.hub.get_dir()
        model_cache_path = os.path.join(cache_dir, 'sentence_transformers', model_name)
        
        if os.path.exists(model_cache_path):
            # Check if cache is corrupted by trying to load
            try:
                test_model = SentenceTransformer(model_name)
                del test_model
                logger.info(f"✅ Model cache for {model_name} is valid")
            except Exception:
                logger.warning(f"🗑️ Clearing corrupted cache for {model_name}")
                shutil.rmtree(model_cache_path, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Could not check model cache: {e}")

def _create_robust_fallback_embedding():
    """Create a robust fallback embedding system"""
    logger.info("🔧 Creating robust fallback embedding system")
    
    class FallbackEmbeddingModel:
        def __init__(self):
            self.dimension = 384
            logger.info("✅ Fallback embedding model initialized")
        
        def encode(self, texts, **kwargs):
            """Generate fallback embeddings using TF-IDF-like approach"""
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = []
            for text in texts:
                embedding = self._generate_fallback_embedding(text)
                embeddings.append(embedding)
            
            return np.array(embeddings)
        
        def _generate_fallback_embedding(self, text):
            """Generate fallback embedding using advanced text analysis"""
            try:
                import re
                from collections import Counter
                
                # Advanced text preprocessing
                text = text.lower()
                # Remove special characters but keep important ones
                text = re.sub(r'[^\w\s\-\.]', ' ', text)
                words = re.findall(r'\b\w+\b', text)
                
                # Create word frequency vector
                word_counts = Counter(words)
                
                # Create embedding vector
                vector = [0.0] * self.dimension
                
                # Hash-based distribution for better coverage
                for word, count in word_counts.items():
                    # Use multiple hash functions for better distribution
                    hash1 = hash(word) % self.dimension
                    hash2 = hash(word + 'salt') % self.dimension
                    hash3 = hash(word[::-1]) % self.dimension
                    
                    # Distribute weight across multiple positions
                    vector[hash1] += count * 0.1
                    vector[hash2] += count * 0.05
                    vector[hash3] += count * 0.03
                
                # Normalize the vector
                magnitude = sum(x*x for x in vector) ** 0.5
                if magnitude > 0:
                    vector = [x / magnitude for x in vector]
                
                return vector
                
            except Exception as e:
                logger.error(f"Error in fallback embedding: {e}")
                return np.zeros(self.dimension)
    
    return FallbackEmbeddingModel()

# Don't initialize the model at import time - load lazily when needed
# This prevents memory issues at startup

def get_embedding(text):
    """Get embedding for text with Redis caching"""
    if not text:
        return np.zeros(384)
    
    # Check Redis cache first
    cached_embedding = redis_cache.get_cached_embedding(text)
    if cached_embedding is not None:
        return cached_embedding
    
    # Generate embedding if not cached - lazy load model here
    try:
        embedding_model = get_embedding_model()  # Load model only when needed
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
        
        # Create comprehensive text representation
        combined_text = f"{title} {text} {notes}".strip()
        
        if not combined_text:
            return np.zeros(384)
        
        return get_embedding(combined_text)
        
    except Exception as e:
        logger.error(f"Error getting content embedding: {e}")
        return np.zeros(384)

def get_project_embedding(project):
    """Get embedding for project combining title and description"""
    try:
        if not project:
            return np.zeros(384)
        
        # Combine project fields for better representation
        title = project.title or ""
        description = project.description or ""
        technologies = project.technologies or ""
        
        # Create comprehensive project representation
        combined_text = f"{title} {description} {technologies}".strip()
        
        if not combined_text:
            return np.zeros(384)
        
        return get_embedding(combined_text)
        
    except Exception as e:
        logger.error(f"Error getting project embedding: {e}")
        return np.zeros(384)

def is_embedding_available():
    """Check if proper embedding model is available (not fallback)"""
    try:
        model = get_embedding_model()
        return model is not None and not hasattr(model, '_generate_fallback_embedding')
    except:
        return False

def get_embedding_model_info():
    """Get information about the current embedding model"""
    try:
        model = get_embedding_model()
        if model is None:
            return "No embedding model available"
        
        if hasattr(model, '_generate_fallback_embedding'):
            return "Fallback embedding model (limited functionality)"
        
        # Try to get model name
        try:
            model_name = getattr(model, 'model_name', 'Unknown')
            return f"Proper embedding model: {model_name}"
        except:
            return "Proper embedding model (unknown name)"
    except:
        return "No embedding model available" 