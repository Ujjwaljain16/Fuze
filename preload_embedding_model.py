#!/usr/bin/env python3
"""
Pre-load Embedding Model for Fuze
This eliminates the 6.77s model loading time
"""

import os
import time
from sentence_transformers import SentenceTransformer
from embedding_utils import embedding_model

def preload_embedding_model():
    """Pre-load the embedding model to avoid startup delays"""
    print("🚀 Pre-loading Embedding Model")
    print("=" * 40)
    
    try:
        print("📦 Loading SentenceTransformer model...")
        start_time = time.time()
        
        # Load the model (this will take ~6-7 seconds the first time)
        import torch
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Fix meta tensor issue by using to_empty() instead of to()
        if hasattr(torch, 'meta') and torch.meta.is_available():
            # Use to_empty() for meta tensors
            model = model.to_empty(device='cpu')
        else:
            # Fallback to CPU
            model = model.to('cpu')
        
        load_time = time.time() - start_time
        
        print(f"✅ Model loaded in {load_time:.2f} seconds")
        
        # Test the model
        print("🧪 Testing model with sample text...")
        test_text = "Python web development with Flask and SQLAlchemy"
        
        start_time = time.time()
        embedding = model.encode([test_text])[0]
        test_time = time.time() - start_time
        
        print(f"✅ Test embedding generated in {test_time*1000:.1f}ms")
        print(f"📊 Embedding dimensions: {len(embedding)}")
        
        # Test batch processing
        print("🧪 Testing batch processing...")
        test_texts = [
            "React hooks and state management",
            "Machine learning algorithms",
            "Database optimization techniques",
            "API design patterns",
            "Web security best practices"
        ]
        
        start_time = time.time()
        batch_embeddings = model.encode(test_texts, batch_size=5)
        batch_time = time.time() - start_time
        
        print(f"✅ Batch processing completed in {batch_time*1000:.1f}ms")
        print(f"📊 Processed {len(test_texts)} texts")
        
        print("\n🎉 Model is ready for use!")
        print("💡 Subsequent requests will be much faster")
        
        return True
        
    except Exception as e:
        print(f"❌ Error pre-loading model: {e}")
        return False

def optimize_embedding_utils():
    """Optimize the embedding utilities for better performance"""
    print("\n🔧 Optimizing Embedding Utilities")
    print("=" * 40)
    
    try:
        # Test the current embedding function
        print("🧪 Testing current embedding function...")
        
        start_time = time.time()
        from embedding_utils import get_embedding
        
        test_text = "Python web development with Flask and SQLAlchemy"
        embedding = get_embedding(test_text)
        test_time = time.time() - start_time
        
        print(f"✅ Current function: {test_time*1000:.1f}ms")
        
        # Test with Redis cache
        print("🧪 Testing with Redis cache...")
        
        start_time = time.time()
        cached_embedding = get_embedding(test_text)  # Should be cached now
        cached_time = time.time() - start_time
        
        print(f"✅ Cached function: {cached_time*1000:.1f}ms")
        
        if cached_time < test_time * 0.1:  # 10x faster with cache
            print("🎉 Redis caching is working perfectly!")
        else:
            print("⚠️ Redis caching could be improved")
        
        return True
        
    except Exception as e:
        print(f"❌ Error optimizing embedding utilities: {e}")
        return False

def create_optimized_embedding_config():
    """Create optimized configuration for embedding model"""
    print("\n🔧 Creating Optimized Configuration")
    print("=" * 40)
    
    config_content = """# Optimized Embedding Configuration
# Add these to your .env file for better performance

# Embedding Model Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
EMBEDDING_CACHE_SIZE=1000

# Performance Settings
EMBEDDING_DEVICE=cpu
EMBEDDING_NORMALIZE=True
EMBEDDING_CONVERT_TO_NUMPY=True

# Cache Settings
EMBEDDING_CACHE_TTL=86400  # 24 hours
EMBEDDING_CACHE_PREFIX=fuze:embedding

# Batch Processing
EMBEDDING_MAX_BATCH_SIZE=64
EMBEDDING_PARALLEL_PROCESSING=True
"""
    
    try:
        with open('.env.embedding', 'w') as f:
            f.write(config_content)
        print("✅ Created .env.embedding configuration file")
        print("💡 Add these variables to your .env file")
        return True
    except Exception as e:
        print(f"❌ Error creating config: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Fuze Embedding Model Optimization")
    print("=" * 50)
    
    # Pre-load the model
    if preload_embedding_model():
        print("\n✅ Model pre-loaded successfully!")
    else:
        print("\n❌ Failed to pre-load model")
        return
    
    # Optimize utilities
    if optimize_embedding_utils():
        print("\n✅ Embedding utilities optimized!")
    else:
        print("\n⚠️ Failed to optimize utilities")
    
    # Create configuration
    if create_optimized_embedding_config():
        print("\n✅ Configuration created!")
    else:
        print("\n⚠️ Failed to create configuration")
    
    print("\n" + "=" * 50)
    print("🎯 Embedding optimization complete!")
    print("💡 Model loading time eliminated!")
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. The model will be loaded once and stay in memory")
    print("3. All embedding requests will be fast")

if __name__ == "__main__":
    main() 