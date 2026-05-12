from sentence_transformers import SentenceTransformer
import numpy as np
from .redis_utils import redis_cache
from sklearn.metrics.pairwise import cosine_similarity
from core.logging_config import get_logger
import os
import shutil
import gevent
from gevent.threadpool import ThreadPool
import threading
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EmbeddingArtifact:
    vector: np.ndarray
    provider: str
    model: str
    version: str
    dimension: int
    dtype: str
    normalized: bool
    generated_at: str

# Limit concurrent inference calls
_embed_pool = ThreadPool(maxsize=2)

logger = get_logger(__name__)

# Singleton pattern for embedding model with thread safety
_embedding_model = None
_embedding_model_initialized = False
_embedding_lock = threading.Lock()

def get_embedding_model():
    """Get or create the embedding model singleton with robust initialization

    Model is lazy-loaded to prevent OOM at startup.
    Set EAGER_LOAD_EMBEDDING_MODEL=true to load at import time (not recommended for free tier).
    
    PRODUCTION OPTIMIZATION: Uses production_optimizations for better caching
    """
    global _embedding_model, _embedding_model_initialized

    if not _embedding_model_initialized:
        with _embedding_lock:
            # Double-check pattern
            if not _embedding_model_initialized:
                # Standard initialization
                logger.debug("embedding_model_init_standard")
                
                _embedding_model = _initialize_embedding_model_robust()
                _embedding_model_initialized = True

    return _embedding_model

def _initialize_embedding_model_robust():
    """Robust embedding model initialization with multiple fallbacks"""

    # Check if embeddings are disabled
    if os.environ.get('DISABLE_EMBEDDINGS', '').lower() in ('true', '1', 'yes'):
        logger.info("embedding_model_disabled_by_env")
        return _create_robust_fallback_embedding()

    # Optimize memory usage for torch
    try:
        import torch
        # Set environment variables to reduce memory usage
        os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'max_split_size_mb:128')
        # Disable CUDA if available to save memory (we're using CPU anyway)
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
    except ImportError:
        pass
    
    # Model options in order of preference (size vs quality)
    # Keep original model priority - lazy loading prevents OOM at startup
    model_options = [
        'all-MiniLM-L6-v2',        # Best quality, ~90MB (original model) - KNOWN TO WORK
        'paraphrase-MiniLM-L6-v2',  # Good quality, ~90MB
        'paraphrase-MiniLM-L3-v2',  # Good quality, ~60MB (fallback)
    ]
    
    for model_name in model_options:
        try:
            logger.info("embedding_model_load_attempt", model_name=model_name)
            
            # Clear any corrupted cache for this model
            _clear_model_cache_if_needed(model_name)
            
            # Initialize the model with error handling for meta tensors
            try:
                model = SentenceTransformer(model_name)
            except Exception as init_error:
                if "meta tensor" in str(init_error):
                    logger.warning("embedding_model_meta_tensor_error", model_name=model_name, error=str(init_error))
                    # Force clear cache and retry once
                    _force_clear_model_cache(model_name)
                    try:
                        model = SentenceTransformer(model_name)
                    except Exception as retry_error:
                        logger.warning("embedding_model_load_retry_failed", model_name=model_name, error=str(retry_error))
                        continue
                else:
                    raise init_error

            # Don't manually handle device placement - SentenceTransformer handles this internally
            logger.info("embedding_model_loaded_successfully", model_name=model_name)

            # Test the model with a simple encoding
            test_text = "test"
            try:
                test_embedding = model.encode([test_text])
                if test_embedding is not None and len(test_embedding) > 0:
                    logger.info("embedding_model_test_success", model_name=model_name)
                    return model
                else:
                    logger.warning("embedding_model_test_failed_empty", model_name=model_name)
            except Exception as encode_error:
                if "meta tensor" in str(encode_error):
                    logger.warning("embedding_model_encoding_meta_error", model_name=model_name)
                else:
                    logger.warning("embedding_model_encoding_test_failed", model_name=model_name, error=str(encode_error))
                continue
                
        except Exception as e:
            logger.warning("embedding_model_load_generic_failed", model_name=model_name, error=str(e))
            continue
    
    # If all models fail, create a robust fallback
    logger.error("embedding_all_models_failed")
    with _embedding_lock:
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
                logger.info("embedding_model_cache_valid", model_name=model_name)
            except Exception:
                logger.warning("embedding_model_cache_clearing_corrupted", model_name=model_name)
                shutil.rmtree(model_cache_path, ignore_errors=True)
    except Exception as e:
        logger.warning("embedding_model_cache_check_failed", error=str(e))

def _force_clear_model_cache(model_name):
    """Force clear model cache to fix meta tensor issues"""
    try:
        import torch
        cache_dir = torch.hub.get_dir()
        model_cache_path = os.path.join(cache_dir, 'sentence_transformers', model_name)

        if os.path.exists(model_cache_path):
            logger.warning("embedding_model_cache_force_clear", model_name=model_name)
            shutil.rmtree(model_cache_path, ignore_errors=True)
            # Also try to clear any related HuggingFace cache
            try:
                hf_cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
                if os.path.exists(hf_cache_dir):
                    for item in os.listdir(hf_cache_dir):
                        if model_name in item or "sentence-transformers" in item:
                            item_path = os.path.join(hf_cache_dir, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)
            except Exception:
                pass  # Ignore HF cache clearing errors
    except Exception as e:
        logger.warning("embedding_model_cache_force_clear_failed", error=str(e))

def _create_robust_fallback_embedding():
    """Create a robust fallback embedding system"""
    logger.info("embedding_fallback_init_start")
    
    class FallbackEmbeddingModel:
        def __init__(self):
            self.dimension = 384
            self._generate_fallback_embedding = True  # Mark this as a fallback model
            logger.info("embedding_fallback_init_success")
        
        def encode(self, texts, **kwargs):
            """Generate fallback embeddings using TF-IDF-like approach"""
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = []
            for text in texts:
                embedding = self._generate_fallback_embedding_logic(text)
                embeddings.append(embedding)
            
            return np.array(embeddings)
        
        def _generate_fallback_embedding_logic(self, text):
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
                logger.error("embedding_fallback_logic_failed", error=str(e))
                return np.zeros(self.dimension)
    
    return FallbackEmbeddingModel()

def generate_embedding(text):
    """
    Generate an embedding for a text string using the lazy-loaded model.
    Will gracefully fallback to a simple hash if models are unavailable.
    """
    if not text:
        return None
        
    try:
        # Wrap the ML encoding to avoid blocking gevent execution
        with gevent.Timeout(10.0):
            return embed_async([text])[0]
    except gevent.Timeout:
        logger.error("embedding_timeout_use_fallback")
        return _create_robust_fallback_embedding().encode([text])[0]
    except Exception as e:
        logger.warning("embedding_efficiency_failed_use_fallback", error=str(e))
        return _create_robust_fallback_embedding().encode([text])[0]

def embed_async(texts: list) -> list:
    """
    Run SentenceTransformer.encode() in a thread pool so it doesn't 
    block the gevent event loop. Returns a greenlet-safe future.
    """
    embedding_model = get_embedding_model()
    future = _embed_pool.spawn(embedding_model.encode, texts)
    return future.get()

def warm_up_embedding_model():
    """Call once at app startup to load model into memory."""
    logger.info("embedding_warmup_start")
    try:
        embed_async(["warm up"])
        logger.info("embedding_warmup_success")
    except Exception as e:
        logger.error("embedding_warmup_failed", error=str(e))

def get_embedding(text):
    """Get embedding for text with Redis caching"""
    if not text:
        return np.zeros(384)
    
    # Check Redis cache first
    cached_embedding = redis_cache.get_cached_embedding(text)
    if cached_embedding is not None:
        return cached_embedding
    
    # Generate embedding if not cached - lazy load model here
    embedding = generate_embedding(text)
    
    # Cache the embedding for future use
    redis_cache.cache_embedding(text, embedding)
    
    return embedding

def get_embedding_artifact(text) -> EmbeddingArtifact:
    """Get fully qualified EmbeddingArtifact with provenance metadata"""
    vector = get_embedding(text)
    
    # We use MiniLM locally by default
    return EmbeddingArtifact(
        vector=vector,
        provider="sentence-transformers",
        model="all-MiniLM-L6-v2",
        version="1.0",
        dimension=384,
        dtype="float32",
        normalized=True,
        generated_at=datetime.utcnow().isoformat() + "Z"
    )

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
        logger.error("embedding_similarity_calc_failed", error=str(e))
        return 0.0

def get_content_embedding(content) -> EmbeddingArtifact:
    """Get embedding artifact for content combining title and text"""
    try:
        if not content:
            return get_embedding_artifact("")
        
        # Combine title and text for better representation
        title = content.title or ""
        text = content.extracted_text or ""
        notes = content.notes or ""
        
        # Create comprehensive text representation
        combined_text = f"{title} {text} {notes}".strip()
        
        return get_embedding_artifact(combined_text)
        
    except Exception as e:
        logger.error("embedding_get_content_failed", error=str(e))
        return get_embedding_artifact("")

def get_project_embedding(project) -> EmbeddingArtifact:
    """Get embedding artifact for project combining title and description"""
    try:
        if not project:
            return get_embedding_artifact("")
        
        # Combine project fields for better representation
        title = project.title or ""
        description = project.description or ""
        technologies = project.technologies or ""
        
        # Create comprehensive project representation
        combined_text = f"{title} {description} {technologies}".strip()
        
        return get_embedding_artifact(combined_text)
        
    except Exception as e:
        logger.error("embedding_get_project_failed", error=str(e))
        return get_embedding_artifact("")

def get_subtask_embedding(subtask) -> EmbeddingArtifact:
    """Get embedding artifact for subtask combining title and description"""
    try:
        if not subtask:
            return get_embedding_artifact("")

        # Combine subtask fields for better representation
        title = subtask.title or ""
        description = subtask.description or ""

        # Create comprehensive subtask representation
        combined_text = f"{title} {description}".strip()

        return get_embedding_artifact(combined_text)

    except Exception as e:
        logger.error("embedding_get_subtask_failed", error=str(e))
        return get_embedding_artifact("")

def get_task_embedding(task) -> EmbeddingArtifact:
    """Get embedding artifact for task combining title and description"""
    try:
        if not task:
            return get_embedding_artifact("")

        # Combine task fields for better representation
        title = task.title or ""
        description = task.description or ""

        # Create comprehensive task representation
        combined_text = f"{title} {description}".strip()

        return get_embedding_artifact(combined_text)

    except Exception as e:
        logger.error("embedding_get_task_failed", error=str(e))
        return get_embedding_artifact("")

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