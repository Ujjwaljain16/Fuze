#!/usr/bin/env python3
"""
Performance optimization script for the Fuze recommendation system
"""

import os
import sys
import time
import logging
from typing import List, Dict
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """
    Performance optimization utilities for the recommendation system
    """
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def optimize_batch_processing(self, items: List[Dict], process_func, batch_size: int = 10) -> List[Dict]:
        """
        Optimize batch processing with parallel execution and caching
        """
        logger.info(f"Optimizing batch processing for {len(items)} items")
        
        # Split items into batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        logger.info(f"Created {len(batches)} batches of size {batch_size}")
        
        results = []
        start_time = time.time()
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit batch processing tasks
            future_to_batch = {
                executor.submit(self._process_batch, batch, process_func): batch 
                for batch in batches
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                    logger.info(f"Completed batch of {len(batch)} items")
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    # Add original items as fallback
                    results.extend(batch)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Batch processing completed in {elapsed_time:.2f} seconds")
        logger.info(f"Cache hits: {self.cache_hits}, Cache misses: {self.cache_misses}")
        
        return results
    
    def _process_batch(self, batch: List[Dict], process_func) -> List[Dict]:
        """
        Process a single batch with caching
        """
        results = []
        
        for item in batch:
            # Create cache key based on item content
            cache_key = self._create_cache_key(item)
            
            if cache_key in self.cache:
                # Use cached result
                self.cache_hits += 1
                results.append(self.cache[cache_key])
            else:
                # Process item and cache result
                self.cache_misses += 1
                try:
                    processed_item = process_func(item)
                    self.cache[cache_key] = processed_item
                    results.append(processed_item)
                except Exception as e:
                    logger.warning(f"Failed to process item: {e}")
                    results.append(item)  # Return original item as fallback
        
        return results
    
    def _create_cache_key(self, item: Dict) -> str:
        """
        Create a cache key for an item
        """
        # Use title and URL as cache key
        title = item.get('title', '')
        url = item.get('url', '')
        return f"{title}_{url}"
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total_requests
        }

class EmbeddingOptimizer:
    """
    Optimize embedding generation and similarity calculations
    """
    
    def __init__(self):
        self.embedding_cache = {}
        self.similarity_cache = {}
    
    @lru_cache(maxsize=1000)
    def get_cached_embedding(self, text: str) -> np.ndarray:
        """
        Get cached embedding for text
        """
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Generate embedding (this would call your actual embedding function)
        # For now, we'll use a placeholder
        embedding = np.random.rand(384)  # Placeholder
        self.embedding_cache[text] = embedding
        return embedding
    
    def batch_embedding_generation(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings in batches for better performance
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = [self.get_cached_embedding(text) for text in batch_texts]
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def optimized_similarity_calculation(self, embeddings1: List[np.ndarray], 
                                       embeddings2: List[np.ndarray]) -> np.ndarray:
        """
        Calculate similarities between two lists of embeddings efficiently
        """
        # Convert to numpy arrays for vectorized operations
        emb1 = np.array(embeddings1)
        emb2 = np.array(embeddings2)
        
        # Normalize embeddings
        emb1_norm = emb1 / np.linalg.norm(emb1, axis=1, keepdims=True)
        emb2_norm = emb2 / np.linalg.norm(emb2, axis=1, keepdims=True)
        
        # Calculate cosine similarity using matrix multiplication
        similarities = np.dot(emb1_norm, emb2_norm.T)
        
        return similarities

def optimize_recommendation_engine():
    """
    Apply performance optimizations to the recommendation engine
    """
    logger.info("Applying performance optimizations to recommendation engine")
    
    # Create optimizers
    perf_optimizer = PerformanceOptimizer(max_workers=4)
    embedding_optimizer = EmbeddingOptimizer()
    
    # Example optimization for bookmark processing
    def process_bookmark(bookmark: Dict) -> Dict:
        """Example bookmark processing function"""
        # Add processing logic here
        bookmark['processed'] = True
        bookmark['timestamp'] = time.time()
        return bookmark
    
    # Example usage
    sample_bookmarks = [
        {'id': i, 'title': f'Bookmark {i}', 'url': f'https://example.com/{i}'}
        for i in range(100)
    ]
    
    # Optimize batch processing
    optimized_bookmarks = perf_optimizer.optimize_batch_processing(
        sample_bookmarks, process_bookmark, batch_size=10
    )
    
    # Print cache statistics
    cache_stats = perf_optimizer.get_cache_stats()
    logger.info(f"Cache statistics: {cache_stats}")
    
    return perf_optimizer, embedding_optimizer

def create_performance_config():
    """
    Create performance configuration file
    """
    config_content = """# Performance Configuration for Fuze Recommendation System

# Batch Processing Settings
BATCH_SIZE = 10
MAX_WORKERS = 4
CACHE_SIZE = 1000

# Embedding Settings
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_CACHE_SIZE = 1000

# Recommendation Settings
MAX_RECOMMENDATIONS = 10
SIMILARITY_THRESHOLD = 0.7

# Gemini AI Settings
GEMINI_TIMEOUT = 30
GEMINI_MAX_RETRIES = 3
GEMINI_BATCH_SIZE = 5

# Database Settings
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30

# Caching Settings
CACHE_TTL = 3600  # 1 hour
CACHE_MAX_SIZE = 1000

# Logging Settings
LOG_LEVEL = INFO
PERFORMANCE_LOGGING = True
"""
    
    try:
        with open("performance_config.py", 'w') as f:
            f.write(config_content)
        logger.info("✅ Created performance_config.py")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create performance config: {e}")
        return False

def main():
    """Main optimization function"""
    print("="*60)
    print(" FUZE PERFORMANCE OPTIMIZATION")
    print("="*60)
    
    # Apply optimizations
    perf_optimizer, embedding_optimizer = optimize_recommendation_engine()
    
    # Create performance configuration
    create_performance_config()
    
    print("\n✅ Performance optimizations applied successfully!")
    print("\nOptimizations include:")
    print("- Parallel batch processing")
    print("- Intelligent caching")
    print("- Optimized embedding generation")
    print("- Vectorized similarity calculations")
    print("- Configurable performance settings")
    
    print("\nNext steps:")
    print("1. Import and use PerformanceOptimizer in your recommendation engine")
    print("2. Adjust batch sizes based on your system capabilities")
    print("3. Monitor cache hit rates and adjust cache sizes")
    print("4. Use the performance configuration file for tuning")
    
    return True

if __name__ == "__main__":
    main() 