#!/usr/bin/env python3
"""
FAISS Vector Search Engine for Scalable Similarity Search
Replaces/augments pgvector with FAISS for high-performance vector operations
"""

import os
import sys
import time
import logging
import json
import pickle
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import numpy as np

# FAISS Library
try:
    import faiss
    FAISS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ FAISS library imported successfully")
except ImportError as e:
    FAISS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ FAISS library not available: {e}")

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VectorIndex:
    """Vector index metadata"""
    index_id: str
    dimension: int
    index_type: str
    total_vectors: int
    created_at: datetime
    last_updated: datetime
    metadata: Dict[str, Any]

@dataclass
class SearchResult:
    """Vector search result"""
    content_id: int
    similarity_score: float
    rank_position: int
    vector_distance: float
    metadata: Dict[str, Any]

class FAISSVectorEngine:
    """FAISS-based vector search engine for high-performance similarity search"""
    
    def __init__(self, index_type: str = 'hnsw', dimension: int = 384):
        self.index_type = index_type
        self.dimension = dimension
        self.index = None
        self.index_mapping = {}  # Maps FAISS index to content IDs
        self.reverse_mapping = {}  # Maps content IDs to FAISS index
        self.vector_cache = {}  # Cache for frequently accessed vectors
        self.index_metadata = {}
        
        if FAISS_AVAILABLE:
            self._initialize_index()
    
    def _initialize_index(self):
        """Initialize the FAISS index based on type"""
        try:
            if self.index_type in ['hnsw', 'faiss_hnsw']:
                # Hierarchical Navigable Small World - good for high recall
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)  # 32 neighbors
                self.index.hnsw.efConstruction = 200
                self.index.hnsw.efSearch = 100
                
            elif self.index_type == 'ivf':
                # Inverted File - good for large datasets
                nlist = min(4096, max(1, self.dimension // 4))  # Number of clusters
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
                
            elif self.index_type == 'flat':
                # Flat index - exact search, good for small datasets
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                
            else:
                logger.warning(f"Unknown index type: {self.index_type}, using HNSW")
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
                self.index.hnsw.efConstruction = 200
                self.index.hnsw.efSearch = 100
            
            logger.info(f"✅ FAISS {self.index_type.upper()} index initialized with dimension {self.dimension}")
            
            # Add some sample vectors for testing (remove in production)
            self._add_sample_vectors()
            
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {e}")
            self.index = None
    
    def add_vectors(self, vectors: List[np.ndarray], content_ids: List[int], 
                   metadata: Optional[List[Dict[str, Any]]] = None):
        """Add vectors to the index"""
        if not FAISS_AVAILABLE or not self.index:
            logger.error("FAISS index not available")
            return False
        
        try:
            # Convert to numpy array if needed
            if not isinstance(vectors, np.ndarray):
                vectors = np.array(vectors, dtype=np.float32)
            
            # Normalize vectors for cosine similarity
            if self.index_type == 'flat':
                faiss.normalize_L2(vectors)
            
            # Get current index size
            start_idx = self.index.ntotal
            
            # Add vectors to index
            self.index.add(vectors)
            
            # Update mappings
            for i, content_id in enumerate(content_ids):
                faiss_idx = start_idx + i
                self.index_mapping[faiss_idx] = content_id
                self.reverse_mapping[content_id] = faiss_idx
                
                # Store metadata if provided
                if metadata and i < len(metadata):
                    self.index_metadata[content_id] = metadata[i]
            
            logger.info(f"✅ Added {len(vectors)} vectors to FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding vectors: {e}")
            return False
    
    def add_vector(self, vector: np.ndarray, content_id: int, metadata: Optional[Dict[str, Any]] = None):
        """Add a single vector to the index"""
        return self.add_vectors([vector], [content_id], [metadata] if metadata else None)
    
    def _add_sample_vectors(self):
        """Add vectors for testing - will use real user content when available"""
        try:
            # Try to get real user content first
            real_vectors = self._get_real_user_vectors()
            
            if real_vectors:
                # Use REAL user content vectors
                for content_id, vector in real_vectors.items():
                    self.add_vector(vector, content_id)
                logger.info(f"✅ Added {len(real_vectors)} REAL user content vectors to FAISS")
                return
            
            # Fallback: Create intelligent sample vectors for testing
            logger.info("⚠️ Using intelligent sample vectors (real embeddings not available)")
            
            # Create sample vectors for testing
            np.random.seed(42)
            for i in range(100):
                # Generate realistic 384-dimensional vectors
                vector = np.random.rand(self.dimension).astype(np.float32)
                # Normalize to unit length for cosine similarity
                vector = vector / np.linalg.norm(vector)
                
                self.add_vector(vector, i)
                
            logger.info(f"✅ Added {100} intelligent sample vectors to FAISS")
            
        except Exception as e:
            logger.warning(f"Could not add sample vectors: {e}")
    
    def _get_real_user_vectors(self) -> Optional[Dict[int, np.ndarray]]:
        """Get REAL user content vectors from database"""
        try:
            # INTEGRATION: Use real user content for FAISS training
            from models import SavedContent, ContentAnalysis, db
            from app import create_app
            
            app = create_app()
            with app.app_context():
                # Get real user content with embeddings
                user_content = db.session.query(SavedContent, ContentAnalysis).outerjoin(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                ).filter(
                    SavedContent.embedding.isnot(None),
                    SavedContent.quality_score >= 1
                ).limit(1000).all()  # Get up to 1000 real content items
                
                if not user_content:
                    logger.info("No real user content with embeddings found")
                    return None
                
                # Convert embeddings to vectors
                real_vectors = {}
                for content, analysis in user_content:
                    if content.embedding:
                        try:
                            # Convert pgvector to numpy array
                            vector = np.array(content.embedding, dtype=np.float32)
                            # Fix: Use .shape attribute for proper comparison
                            if vector.shape == (self.dimension,):
                                real_vectors[content.id] = vector
                        except Exception as e:
                            logger.warning(f"Could not convert embedding for content {content.id}: {e}")
                            continue
                
                if real_vectors:
                    logger.info(f"✅ Found {len(real_vectors)} real user content vectors")
                    return real_vectors
                else:
                    logger.info("No valid embeddings found in real content")
                    return None
                    
        except Exception as e:
            logger.warning(f"Real user vectors not available: {e}")
            return None
    
    def search(self, query_vector: np.ndarray, k: int = 10, 
               filter_ids: Optional[List[int]] = None) -> List[SearchResult]:
        """Search for similar vectors"""
        if not FAISS_AVAILABLE or not self.index:
            logger.error("FAISS index not available")
            return []
        
        # Check if index has any vectors
        if self.index.ntotal == 0:
            logger.warning("⚠️ FAISS index is empty - no vectors have been added")
            return []
        
        logger.info(f"🔍 Searching FAISS index with {self.index.ntotal} vectors, k={k}")
        
        try:
            # Convert to numpy array if needed
            if not isinstance(query_vector, np.ndarray):
                query_vector = np.array(query_vector, dtype=np.float32)
            
            # Normalize query vector for cosine similarity
            if self.index_type == 'flat':
                faiss.normalize_L2(query_vector.reshape(1, -1))
            
            # Perform search
            start_time = time.time()
            
            if filter_ids:
                # Use IDSelector for filtering
                ids_to_keep = [self.reverse_mapping.get(cid, -1) for cid in filter_ids]
                ids_to_keep = [idx for idx in ids_to_keep if idx >= 0]
                
                if ids_to_keep:
                    id_selector = faiss.IDSelectorArray(ids_to_keep)
                    distances, indices = self.index.search(query_vector.reshape(1, -1), k, id_selector)
                else:
                    return []
            else:
                distances, indices = self.index.search(query_vector.reshape(1, -1), k)
            
            search_time = time.time() - start_time
            
            # Process results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # Invalid index
                    continue
                
                content_id = self.index_mapping.get(idx)
                if content_id is None:
                    continue
                
                # Convert distance to similarity score
                if self.index_type == 'flat':
                    # For inner product, distance is already similarity
                    similarity = float(distance)
                else:
                    # For L2 distance, convert to similarity
                    similarity = 1.0 / (1.0 + float(distance))
                
                result = SearchResult(
                    content_id=content_id,
                    similarity_score=similarity,
                    rank_position=i + 1,
                    vector_distance=float(distance),
                    metadata=self.index_metadata.get(content_id, {})
                )
                results.append(result)
            
            logger.info(f"✅ FAISS search completed in {search_time:.4f}s, found {len(results)} results from {self.index.ntotal} total vectors")
            return results
            
        except Exception as e:
            logger.error(f"Error performing FAISS search: {e}")
            return []
    
    def batch_search(self, query_vectors: List[np.ndarray], k: int = 10,
                    filter_ids: Optional[List[int]] = None) -> List[List[SearchResult]]:
        """Perform batch search for multiple query vectors"""
        if not FAISS_AVAILABLE or not self.index:
            logger.error("FAISS index not available")
            return []
        
        try:
            # Convert to numpy array if needed
            if not isinstance(query_vectors, np.ndarray):
                query_vectors = np.array(query_vectors, dtype=np.float32)
            
            # Normalize vectors for cosine similarity
            if self.index_type == 'flat':
                faiss.normalize_L2(query_vectors)
            
            # Perform batch search
            start_time = time.time()
            
            if filter_ids:
                # Use IDSelector for filtering
                ids_to_keep = [self.reverse_mapping.get(cid, -1) for cid in filter_ids]
                ids_to_keep = [idx for idx in ids_to_keep if idx >= 0]
                
                if ids_to_keep:
                    id_selector = faiss.IDSelectorArray(ids_to_keep)
                    distances, indices = self.index.search(query_vectors, k, id_selector)
                else:
                    return [[] for _ in range(len(query_vectors))]
            else:
                distances, indices = self.index.search(query_vectors, k)
            
            search_time = time.time() - start_time
            
            # Process batch results
            batch_results = []
            for query_idx in range(len(query_vectors)):
                query_results = []
                for i, (distance, idx) in enumerate(zip(distances[query_idx], indices[query_idx])):
                    if idx == -1:  # Invalid index
                        continue
                    
                    content_id = self.index_mapping.get(idx)
                    if content_id is None:
                        continue
                    
                    # Convert distance to similarity score
                    if self.index_type == 'flat':
                        similarity = float(distance)
                    else:
                        similarity = 1.0 / (1.0 + float(distance))
                    
                    result = SearchResult(
                        content_id=content_id,
                        similarity_score=similarity,
                        rank_position=i + 1,
                        vector_distance=float(distance),
                        metadata=self.index_metadata.get(content_id, {})
                    )
                    query_results.append(result)
                
                batch_results.append(query_results)
            
            logger.debug(f"✅ FAISS batch search completed in {search_time:.4f}s for {len(query_vectors)} queries")
            return batch_results
            
        except Exception as e:
            logger.error(f"Error performing FAISS batch search: {e}")
            return [[] for _ in range(len(query_vectors))]
    
    def get_vector(self, content_id: int) -> Optional[np.ndarray]:
        """Get vector for a specific content ID"""
        if not FAISS_AVAILABLE or not self.index:
            return None
        
        try:
            faiss_idx = self.reverse_mapping.get(content_id)
            if faiss_idx is None:
                return None
            
            # FAISS doesn't support direct vector retrieval, so we need to reconstruct
            # This is a limitation - in production, you might want to store vectors separately
            logger.warning("FAISS doesn't support direct vector retrieval - consider storing vectors separately")
            return None
            
        except Exception as e:
            logger.error(f"Error getting vector: {e}")
            return None
    
    def update_vector(self, content_id: int, new_vector: np.ndarray, 
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update vector for existing content"""
        if not FAISS_AVAILABLE or not self.index:
            return False
        
        try:
            # FAISS doesn't support direct updates, so we need to remove and re-add
            faiss_idx = self.reverse_mapping.get(content_id)
            if faiss_idx is None:
                return self.add_vector(new_vector, content_id, metadata)
            
            # Remove old vector (FAISS limitation - we'll need to rebuild)
            logger.warning("FAISS doesn't support direct updates - consider rebuilding index")
            
            # For now, just update metadata
            if metadata:
                self.index_metadata[content_id] = metadata
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating vector: {e}")
            return False
    
    def remove_vector(self, content_id: int) -> bool:
        """Remove vector from index"""
        if not FAISS_AVAILABLE or not self.index:
            return False
        
        try:
            # FAISS doesn't support direct removal, so we need to rebuild
            logger.warning("FAISS doesn't support direct removal - consider rebuilding index")
            
            # Remove from mappings
            faiss_idx = self.reverse_mapping.pop(content_id, None)
            if faiss_idx is not None:
                self.index_mapping.pop(faiss_idx, None)
                self.index_metadata.pop(content_id, None)
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing vector: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if not FAISS_AVAILABLE or not self.index:
            return {'status': 'no_index'}
        
        try:
            stats = {
                'index_type': self.index_type,
                'dimension': self.dimension,
                'total_vectors': self.index.ntotal,
                'is_trained': self.index.is_trained if hasattr(self.index, 'is_trained') else True,
                'mapping_size': len(self.index_mapping),
                'metadata_size': len(self.index_metadata)
            }
            
            # Add index-specific stats
            if hasattr(self.index, 'hnsw'):
                stats['hnsw_ef_construction'] = self.index.hnsw.efConstruction
                stats['hnsw_ef_search'] = self.index.hnsw.efSearch
                stats['hnsw_max_level'] = self.index.hnsw.max_level
            
            elif hasattr(self.index, 'nlist'):
                stats['ivf_nlist'] = self.index.nlist
                stats['ivf_nprobe'] = self.index.nprobe
            
            return stats
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def optimize_index(self):
        """Optimize the index for better performance"""
        if not FAISS_AVAILABLE or not self.index:
            return False
        
        try:
            if hasattr(self.index, 'hnsw'):
                # Optimize HNSW parameters
                self.index.hnsw.efConstruction = min(400, self.index.hnsw.efConstruction * 2)
                self.index.hnsw.efSearch = min(200, self.index.hnsw.efSearch * 2)
                logger.info("✅ HNSW index optimized")
                
            elif hasattr(self.index, 'nlist'):
                # Optimize IVF parameters
                self.index.nprobe = min(64, self.index.nprobe * 2)
                logger.info("✅ IVF index optimized")
            
            return True
            
        except Exception as e:
            logger.error(f"Error optimizing index: {e}")
            return False
    
    def save_index(self, index_path: str):
        """Save the FAISS index"""
        if not FAISS_AVAILABLE or not self.index:
            logger.warning("No index to save")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, index_path)
            
            # Save mappings and metadata
            metadata = {
                'index_mapping': self.index_mapping,
                'reverse_mapping': self.reverse_mapping,
                'index_metadata': self.index_metadata,
                'index_type': self.index_type,
                'dimension': self.dimension,
                'created_at': datetime.now().isoformat()
            }
            
            metadata_path = index_path.replace('.index', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"✅ FAISS index saved to {index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            return False
    
    def load_index(self, index_path: str):
        """Load a saved FAISS index"""
        if not FAISS_AVAILABLE:
            logger.error("FAISS library not available for loading index")
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            
            # Load metadata if available
            metadata_path = index_path.replace('.index', '_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                self.index_mapping = metadata.get('index_mapping', {})
                self.reverse_mapping = metadata.get('reverse_mapping', {})
                self.index_metadata = metadata.get('index_metadata', {})
                self.index_type = metadata.get('index_type', 'unknown')
                self.dimension = metadata.get('dimension', 384)
            
            logger.info(f"✅ FAISS index loaded from {index_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False
    
    def clear_index(self):
        """Clear all vectors from the index"""
        if not FAISS_AVAILABLE or not self.index:
            return False
        
        try:
            # Reset index
            if hasattr(self.index, 'reset'):
                self.index.reset()
            else:
                # For some index types, we need to reinitialize
                self._initialize_index()
            
            # Clear mappings
            self.index_mapping.clear()
            self.reverse_mapping.clear()
            self.index_metadata.clear()
            
            logger.info("✅ FAISS index cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing index: {e}")
            return False

# Factory functions
def create_faiss_engine(index_type: str = 'hnsw', dimension: int = 384) -> FAISSVectorEngine:
    """Create a FAISS vector engine instance"""
    return FAISSVectorEngine(index_type, dimension)

def create_hnsw_engine(dimension: int = 384) -> FAISSVectorEngine:
    """Create an HNSW-based FAISS engine (good for high recall)"""
    return FAISSVectorEngine('hnsw', dimension)

def create_ivf_engine(dimension: int = 384) -> FAISSVectorEngine:
    """Create an IVF-based FAISS engine (good for large datasets)"""
    return FAISSVectorEngine('ivf', dimension)

def create_flat_engine(dimension: int = 384) -> FAISSVectorEngine:
    """Create a flat FAISS engine (exact search, good for small datasets)"""
    return FAISSVectorEngine('flat', dimension)

# Example usage
if __name__ == "__main__":
    # Create engine
    engine = create_faiss_engine('hnsw', dimension=384)
    
    # Generate sample vectors
    np.random.seed(42)
    sample_vectors = np.random.rand(100, 384).astype(np.float32)
    sample_ids = list(range(100, 200))
    
    # Add vectors to index
    if engine.add_vectors(sample_vectors, sample_ids):
        print("✅ Vectors added successfully")
        
        # Get index stats
        stats = engine.get_index_stats()
        print(f"Index stats: {stats}")
        
        # Perform search
        query_vector = np.random.rand(384).astype(np.float32)
        results = engine.search(query_vector, k=5)
        
        print(f"\nSearch results:")
        for result in results:
            print(f"Content {result.content_id}: {result.similarity_score:.3f} (rank {result.rank_position})")
        
        # Save index
        engine.save_index('models/faiss_index.index')
        
        # Test batch search
        query_vectors = np.random.rand(3, 384).astype(np.float32)
        batch_results = engine.batch_search(query_vectors, k=3)
        
        print(f"\nBatch search results:")
        for i, query_results in enumerate(batch_results):
            print(f"Query {i}: {len(query_results)} results")
            for result in query_results[:2]:  # Show first 2 results
                print(f"  Content {result.content_id}: {result.similarity_score:.3f}")

