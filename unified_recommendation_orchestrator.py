#!/usr/bin/env python3
"""
Unified Recommendation Orchestrator
Coordinates all recommendation engines with proper hierarchy and fallback strategies
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import hashlib

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue without it

# Conditional imports to avoid circular dependencies
try:
    from models import db, SavedContent, ContentAnalysis, User
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("ΓÜá∩╕Å Models not available, some functionality will be limited")

try:
    from redis_utils import redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("ΓÜá∩╕Å Redis not available, caching will be disabled")

try:
    from intent_analysis_engine import analyze_user_intent, UserIntent
    INTENT_ANALYSIS_AVAILABLE = True
except ImportError:
    INTENT_ANALYSIS_AVAILABLE = False
    logger.warning("ΓÜá∩╕Å Intent analysis not available, some functionality will be limited")

try:
    from gemini_utils import GeminiAnalyzer
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("ΓÜá∩╕Å Gemini not available, AI features will be disabled")

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our universal semantic matcher
try:
    from universal_semantic_matcher import UniversalSemanticMatcher
    UNIVERSAL_MATCHER_AVAILABLE = True
    logger.info("Γ£à UniversalSemanticMatcher imported successfully")
except ImportError:
    UNIVERSAL_MATCHER_AVAILABLE = False
    logger.warning("ΓÜá∩╕Å UniversalSemanticMatcher not available, using fallback matching")

# Global Gemini instance for caching
_gemini_analyzer = None
_gemini_last_used = None
_gemini_cache_timeout = 300  # 5 minutes

def get_cached_gemini_analyzer():
    """Get or create a cached GeminiAnalyzer instance"""
    global _gemini_analyzer, _gemini_last_used
    
    current_time = time.time()
    
    # Check if we need to create a new instance or refresh
    if (_gemini_analyzer is None or 
        _gemini_last_used is None or 
        current_time - _gemini_last_used > _gemini_cache_timeout):
        
        try:
            _gemini_analyzer = GeminiAnalyzer()
            _gemini_last_used = current_time
            logger.info("Created new cached GeminiAnalyzer instance")
        except Exception as e:
            logger.error(f"Failed to create GeminiAnalyzer: {e}")
            return None
    
    _gemini_last_used = current_time
    return _gemini_analyzer

@dataclass
class UnifiedRecommendationRequest:
    """Standardized recommendation request format"""
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    user_interests: str = ""
    project_id: Optional[int] = None
    max_recommendations: int = 10
    engine_preference: Optional[str] = "context"  # Default to 'context' for better quality
    diversity_weight: float = 0.3
    quality_threshold: int = 6
    include_global_content: bool = True
    cache_duration: int = 1800  # 30 minutes

@dataclass
class UnifiedRecommendationResult:
    """Standardized recommendation result format"""
    id: int
    title: str
    url: str
    score: float
    reason: str
    content_type: str
    difficulty: str
    technologies: List[str]
    key_concepts: List[str]
    quality_score: float
    engine_used: str
    confidence: float
    metadata: Dict[str, Any]
    cached: bool = False

@dataclass
class EnginePerformance:
    """Engine performance metrics"""
    engine_name: str
    response_time_ms: float
    success_rate: float
    cache_hit_rate: float
    error_count: int
    last_used: datetime
    total_requests: int

class UnifiedDataLayer:
    """Standardized data layer for all engines"""
    
    def __init__(self):
        self.embedding_model = None
        self._init_embedding_model()
        
        # Initialize universal semantic matcher if available
        self.universal_matcher = None
        if UNIVERSAL_MATCHER_AVAILABLE:
            try:
                self.universal_matcher = UniversalSemanticMatcher()
                if self.universal_matcher.embedding_model is not None:
                    logger.info("Γ£à UniversalSemanticMatcher initialized in UnifiedDataLayer")
                else:
                    logger.warning("ΓÜá∩╕Å UniversalSemanticMatcher initialized but embedding model is None")
            except Exception as e:
                logger.warning(f"ΓÜá∩╕Å Failed to initialize UniversalSemanticMatcher: {e}")
                # Try to create a minimal version without embedding model
                try:
                    from universal_semantic_matcher import UniversalSemanticMatcher
                    # Create instance without embedding model
                    self.universal_matcher = UniversalSemanticMatcher.__new__(UniversalSemanticMatcher)
                    self.universal_matcher.embedding_model = None
                    logger.info("Γ£à UniversalSemanticMatcher created with fallback mode")
                except Exception as fallback_error:
                    logger.warning(f"ΓÜá∩╕Å Fallback UniversalSemanticMatcher also failed: {fallback_error}")
                    self.universal_matcher = None
    
    def _init_embedding_model(self):
        """Initialize embedding model with fallback for network issues"""
        try:
            # Try to use the global embedding model first
            try:
                from embedding_utils import get_embedding_model
                self.embedding_model = get_embedding_model()
                if self.embedding_model is not None:
                    logger.info("Γ£à Using global embedding model from embedding_utils")
                    return
            except ImportError:
                logger.info("Global embedding model not available, using local initialization")
            
            # Fallback to local initialization
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Try to load the model with network fallback
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # More robust meta tensor handling
                try:
                    # Check if we're dealing with meta tensors
                    if hasattr(torch, 'meta') and torch.meta.is_available():
                        # Use to_empty() for meta tensors
                        self.embedding_model = self.embedding_model.to_empty(device='cpu')
                        logger.info("Γ£à Embedding model loaded with to_empty() for meta tensors")
                    else:
                        # Fallback to CPU
                        self.embedding_model = self.embedding_model.to('cpu')
                        logger.info("Γ£à Embedding model loaded with to() for CPU")
                except Exception as tensor_error:
                    logger.warning(f"Tensor device placement error: {tensor_error}")
                    # Try alternative approach - don't move the model
                    logger.info("Using embedding model without device placement")
                
                logger.info("Γ£à Local embedding model loaded successfully")
            except Exception as network_error:
                logger.warning(f"Network error loading embedding model: {network_error}")
                logger.info("Using fallback embedding approach...")
                # Create a simple fallback embedding function
                self.embedding_model = None
                self._use_fallback_embeddings = True
                
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            self.embedding_model = None
            self._use_fallback_embeddings = True
    
    def get_db_session(self):
        """Get database session with retry logic and error handling"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                from models import db
                if db.session.is_active:
                    return db.session
                else:
                    # Create new session if current one is inactive
                    return db.create_scoped_session()
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to get database session after {max_retries} attempts: {e}")
                    raise
        
        return None

    def normalize_content_data(self, content: Any, analysis: Optional[Any] = None) -> Dict[str, Any]:
        """Normalize content data to unified format"""
        try:
            # Extract technologies from multiple sources
            technologies = []
            
            # From tags
            if content.tags:
                technologies.extend([tech.strip() for tech in content.tags.split(',') if tech.strip()])
            
            # From analysis
            if analysis:
                if analysis.technology_tags:
                    technologies.extend([tech.strip() for tech in analysis.technology_tags.split(',') if tech.strip()])
                
                # From analysis_data JSON
                if analysis.analysis_data:
                    analysis_techs = analysis.analysis_data.get('technologies', [])
                    if isinstance(analysis_techs, list):
                        technologies.extend(analysis_techs)
                    elif isinstance(analysis_techs, str):
                        technologies.extend([tech.strip() for tech in analysis_techs.split(',') if tech.strip()])
            
            # Remove duplicates and normalize
            technologies = list(set([tech.lower().strip() for tech in technologies if tech.strip()]))
            
            # Extract key concepts
            key_concepts = []
            if analysis and analysis.key_concepts:
                key_concepts = [concept.strip() for concept in analysis.key_concepts.split(',') if concept.strip()]
            
            # Determine content type
            content_type = 'article'  # default
            if analysis:
                content_type = analysis.content_type or 'article'
            
            # Determine difficulty
            difficulty = 'intermediate'  # default
            if analysis:
                difficulty = analysis.difficulty_level or 'intermediate'
            
            # Create unified format
            unified_data = {
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'extracted_text': content.extracted_text or '',
                'notes': content.notes or '',
                'technologies': technologies,
                'key_concepts': key_concepts,
                'content_type': content_type,
                'difficulty': difficulty,
                'quality_score': content.quality_score or 6,
                'saved_at': content.saved_at,
                'tags': content.tags or '',
                'analysis_data': analysis.analysis_data if analysis else {},
                'embedding': content.embedding,
                'relevance_score': analysis.relevance_score if analysis else 0
            }
            
            return unified_data
            
        except Exception as e:
            logger.error(f"Error normalizing content data: {e}")
            # Return minimal data
            return {
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'extracted_text': content.extracted_text or '',
                'technologies': [],
                'key_concepts': [],
                'content_type': 'article',
                'difficulty': 'intermediate',
                'quality_score': content.quality_score or 6,
                'saved_at': content.saved_at,
                'tags': content.tags or '',
                'analysis_data': {},
                'embedding': content.embedding,
                'relevance_score': 0
            }
    
    def get_candidate_content(self, user_id: int, request: UnifiedRecommendationRequest) -> List[Dict[str, Any]]:
        """Get candidate content in unified format"""
        try:
            from database_utils import get_db_session, with_db_session
            
            @with_db_session
            def get_content(session):
                return self._get_content_from_db_with_session(user_id, request, session)
            
            return get_content()
        except Exception as e:
            logger.error(f"Error getting candidate content: {e}")
            return []
    
    def _get_content_from_db_with_session(self, user_id: int, request: UnifiedRecommendationRequest, session) -> List[Dict[str, Any]]:
        """Get content from database using provided session - OPTIMIZED FOR PERFORMANCE"""
        try:
            from models import SavedContent, ContentAnalysis
            
            # OPTIMIZATION 1: Use more efficient query with proper indexing
            # Build query with optimized joins and filtering
            query = session.query(SavedContent, ContentAnalysis).outerjoin(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            )
            
            # OPTIMIZATION 2: Apply filters early to reduce data transfer
            query = query.filter(
                SavedContent.user_id == user_id,
                SavedContent.quality_score >= 3,  # Lowered to include more user content
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                SavedContent.title.isnot(None),
                SavedContent.title != ''
            )
            
            # OPTIMIZATION 3: Use more efficient filtering with indexed columns
            # Filter out test content and generic/low-quality content
            query = query.filter(
                ~SavedContent.title.like('%Test Bookmark%'),
                ~SavedContent.title.like('%test bookmark%'),
                ~SavedContent.title.like('%Dictionary%'),
                ~SavedContent.title.like('%dictionary%'),
                ~SavedContent.title.like('%International%'),
                ~SavedContent.url.like('%dbooks.org%'),
                ~SavedContent.url.like('%pdfdrive.com%'),
                ~SavedContent.url.like('%scribd.com%')
            )
            
            # OPTIMIZATION 4: Limit results early and use proper ordering
            user_content = query.order_by(
                SavedContent.quality_score.desc(),
                SavedContent.saved_at.desc()
            ).limit(100).all()  # Reduced limit for better performance
            
            logger.info(f"Found {len(user_content)} content items from user {user_id}")
            
            # OPTIMIZATION 5: Batch process content normalization
            content_list = []
            request_techs = [tech.strip().lower() for tech in request.technologies.split(',') if tech.strip()]
            request_text = f"{request.title} {request.description}".lower()
            
            for content, analysis in user_content:
                # Use the normalize_content_data method to ensure all required fields
                normalized_content = self.normalize_content_data(content, analysis)
                
                # OPTIMIZATION 6: Simplified relevance scoring for better performance
                relevance_score = self._calculate_fast_content_relevance(
                    normalized_content, request_techs, request_text, request
                )
                
                # Add additional fields needed by engines
                normalized_content.update({
                    'user_id': content.user_id,
                    'is_user_content': True,
                    'project_relevance_boost': relevance_score,
                    'relevance_score': relevance_score
                })
                
                content_list.append(normalized_content)
            
            # OPTIMIZATION 7: Use more efficient sorting
            content_list.sort(key=lambda x: (x.get('relevance_score', 0), x.get('quality_score', 0)), reverse=True)
            
            logger.info(f"Retrieved {len(content_list)} content items from user {user_id}")
            return content_list
            
        except Exception as e:
            logger.error(f"Error getting content from database: {e}")
            return []
    
    def _get_content_from_db(self, user_id: int, request: UnifiedRecommendationRequest) -> List[Dict[str, Any]]:
        """Get content from database with focus on the requesting user's own saved content"""
        try:
            from database_utils import get_db_session
            from models import SavedContent, ContentAnalysis
            
            session = get_db_session()
            if not session:
                logger.error("Could not get database session")
                return []
            
            return self._get_content_from_db_with_session(user_id, request, session)
                
        except Exception as e:
            logger.error(f"Error getting content from database: {e}")
            return []
    
    def _calculate_content_relevance(self, content: Dict[str, Any], request_techs: List[str], request_text: str, request: UnifiedRecommendationRequest) -> float:
        """Calculate relevance score for user's own content"""
        relevance_score = 0.0
        
        # Technology overlap (50% weight) - Higher weight for user content
        content_techs = content.get('technologies', [])
        if request_techs and content_techs:
            tech_overlap = len(set(request_techs).intersection(set(content_techs)))
            tech_relevance = tech_overlap / len(request_techs) if request_techs else 0
            relevance_score += tech_relevance * 0.5
        
        # Text similarity (30% weight)
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        if request_text and content_text:
            # Simple keyword matching for now
            request_words = set(request_text.split())
            content_words = set(content_text.split())
            word_overlap = len(request_words.intersection(content_words))
            text_relevance = word_overlap / len(request_words) if request_words else 0
            relevance_score += text_relevance * 0.3
        
        # Quality score (15% weight) - Lower weight since it's user's own content
        quality_score = content.get('quality_score', 5) / 10.0
        relevance_score += quality_score * 0.15
        
        # User content boost (5% weight) - Small boost since all content is user's
        relevance_score += 0.05
        
        # Project-specific boost
        if request.project_id:
            project_boost = content.get('project_relevance_boost', 0) / 10.0
            relevance_score += project_boost * 0.1
        
        return min(relevance_score, 1.0)  # Cap at 1.0
    
    def _calculate_fast_content_relevance(self, content: Dict[str, Any], request_techs: List[str], request_text: str, request: UnifiedRecommendationRequest) -> float:
        """FAST relevance scoring for better performance - simplified version"""
        relevance_score = 0.0
        
        # OPTIMIZATION: Simplified technology overlap calculation
        content_techs = content.get('technologies', [])
        if request_techs and content_techs:
            # Use set intersection for faster calculation
            tech_overlap = len(set(request_techs).intersection(set(content_techs)))
            tech_relevance = tech_overlap / len(request_techs) if request_techs else 0
            relevance_score += tech_relevance * 0.6  # Increased weight for technology match
        
        # OPTIMIZATION: Simplified text similarity using basic keyword matching
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        if request_text and content_text:
            # Use simple word overlap for speed
            request_words = set(request_text.split()[:20])  # Limit to first 20 words for speed
            content_words = set(content_text.split()[:50])  # Limit to first 50 words for speed
            word_overlap = len(request_words.intersection(content_words))
            text_relevance = word_overlap / len(request_words) if request_words else 0
            relevance_score += text_relevance * 0.3
        
        # OPTIMIZATION: Simplified quality scoring
        quality_score = content.get('quality_score', 6) / 10.0  # Default to 6 if not set
        relevance_score += quality_score * 0.1
        
        # OPTIMIZATION: Skip complex project-specific calculations for speed
        if request.project_id:
            relevance_score += 0.05  # Small boost for project context
        
        return min(relevance_score, 1.0)  # Cap at 1.0
    
    def _boost_project_relevance(self, content: Dict[str, Any], request: UnifiedRecommendationRequest) -> Dict[str, Any]:
        """Boost content relevance for project-based recommendations"""
        try:
            if not request.project_id:
                return content
            
            # Get project details
            from models import Project
            project = Project.query.filter_by(id=request.project_id, user_id=request.user_id).first()
            if not project:
                return content
            
            # Extract project technologies
            project_techs = [tech.strip().lower() for tech in (project.technologies or '').split(',') if tech.strip()]
            if not project_techs:
                return content
            
            # Check content for project technology matches
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')} {content.get('tags', '')}".lower()
            content_techs = content.get('technologies', [])
            
            # Calculate technology overlap
            tech_matches = 0
            for project_tech in project_techs:
                if project_tech in content_text or any(project_tech in tech.lower() for tech in content_techs):
                    tech_matches += 1
            
            # Boost quality score based on technology matches
            if tech_matches > 0:
                boost_factor = min(tech_matches * 0.5, 2.0)  # Max 2 point boost
                content['quality_score'] = min(content.get('quality_score', 7) + boost_factor, 10)
                content['project_relevance_boost'] = boost_factor
                logger.debug(f"Boosted content {content.get('id')} by {boost_factor} for project {request.project_id}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error boosting project relevance: {e}")
            return content
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text"""
        if not self.embedding_model or not text:
            return None
        
        try:
            return self.embedding_model.encode([text])[0]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        try:
            emb1 = self.generate_embedding(text1)
            emb2 = self.generate_embedding(text2)
            
            if emb1 is None or emb2 is None:
                return 0.5  # Neutral similarity
            
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.5
    
    def calculate_batch_similarities(self, request_text: str, content_texts: List[str]) -> List[float]:
        """Calculate semantic similarities for multiple content texts in batch - OPTIMIZED FOR PERFORMANCE"""
        try:
            # OPTIMIZATION 1: Try universal semantic matcher first if available
            if self.universal_matcher:
                try:
                    logger.debug("Using UniversalSemanticMatcher for enhanced similarity calculation")
                    similarities = []
                    for content_text in content_texts:
                        similarity = self.universal_matcher.calculate_semantic_similarity(request_text, content_text)
                        similarities.append(similarity)
                    return similarities
                except Exception as e:
                    logger.warning(f"UniversalSemanticMatcher failed, falling back to embedding model: {e}")
            
            # OPTIMIZATION 2: Check if we have the embedding model
            if not self.embedding_model:
                return [0.5] * len(content_texts)
            
            # OPTIMIZATION 2: Use larger batch size for better GPU utilization
            all_texts = [request_text] + content_texts
            batch_size = min(64, len(all_texts))  # Increased batch size for better performance
            
            # OPTIMIZATION 3: Generate embeddings in optimized batches
            embeddings = self.embedding_model.encode(
                all_texts, 
                show_progress_bar=False, 
                batch_size=batch_size,
                convert_to_numpy=True,  # Ensure numpy arrays for faster computation
                normalize_embeddings=True  # Pre-normalize for faster similarity calculation
            )
            
            # OPTIMIZATION 4: Extract embeddings efficiently
            request_embedding = embeddings[0]
            content_embeddings = embeddings[1:]
            
            # OPTIMIZATION 5: Use vectorized similarity calculation for better performance
            if len(content_embeddings) > 0:
                # Convert to numpy arrays for vectorized operations
                request_emb = np.array(request_embedding)
                content_embs = np.array(content_embeddings)
                
                # OPTIMIZATION 6: Use pre-normalized embeddings for faster dot product
                if hasattr(self.embedding_model, 'normalize_embeddings') and self.embedding_model.normalize_embeddings:
                    # If embeddings are already normalized, just use dot product
                    similarities = np.dot(content_embs, request_emb)
                else:
                    # Manual normalization for compatibility
                    request_norm = np.linalg.norm(request_emb)
                    content_norms = np.linalg.norm(content_embs, axis=1)
                    
                    # Avoid division by zero
                    valid_norms = content_norms > 0
                    similarities = np.zeros(len(content_embs))
                    
                    if request_norm > 0:
                        similarities[valid_norms] = np.dot(
                            content_embs[valid_norms], request_emb
                        ) / (content_norms[valid_norms] * request_norm)
                    
                    similarities[~valid_norms] = 0.0
                
                return similarities.tolist()
            else:
                return []
            
        except Exception as e:
            logger.error(f"Error calculating batch similarities: {e}")
            # OPTIMIZATION 7: Return neutral similarities on error for graceful degradation
            return [0.5] * len(content_texts)

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text with fallback support"""
        if self.embedding_model is not None:
            try:
                return self.embedding_model.encode(text).tolist()
            except Exception as e:
                logger.warning(f"Error with embedding model: {e}")
                return self._fallback_embedding(text)
        else:
            return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """Simple fallback embedding using TF-IDF-like approach"""
        try:
            import re
            from collections import Counter
            
            # Simple text preprocessing
            text = text.lower()
            words = re.findall(r'\b\w+\b', text)
            
            # Create a simple vector representation
            word_counts = Counter(words)
            
            # Create a fixed-size vector (384 dimensions like the original model)
            vector = [0.0] * 384
            
            # Simple hash-based embedding
            for word, count in word_counts.items():
                # Use hash to distribute words across dimensions
                hash_val = hash(word) % 384
                vector[hash_val] += count * 0.1  # Normalize
            
            # Normalize the vector
            magnitude = sum(x*x for x in vector) ** 0.5
            if magnitude > 0:
                vector = [x / magnitude for x in vector]
            
            return vector
            
        except Exception as e:
            logger.error(f"Error in fallback embedding: {e}")
            # Return zero vector as last resort
            return [0.0] * 384

class FastSemanticEngine:
    """Fast semantic similarity engine (Primary)"""
    
    def __init__(self, data_layer: UnifiedDataLayer):
        self.data_layer = data_layer
        self.name = "FastSemanticEngine"
        self.performance = EnginePerformance(
            engine_name=self.name,
            response_time_ms=0.0,
            success_rate=1.0,
            cache_hit_rate=0.0,
            error_count=0,
            last_used=datetime.utcnow(),
            total_requests=0
        )
    
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get fast semantic recommendations"""
        start_time = time.time()
        
        try:
            # If no content_list provided, fetch all relevant content from DB
            if not content_list:
                from models import SavedContent, ContentAnalysis
                from sqlalchemy.orm import joinedload
                from flask import current_app
                # Use the current app context if available
                try:
                    db_session = self.data_layer.get_db_session()
                    if not db_session:
                        logger.error("Could not get database session")
                        return []
                    query = db_session.query(SavedContent).options(joinedload(SavedContent.analyses))
                    query = query.filter(
                        SavedContent.quality_score >= 3,
                        SavedContent.extracted_text.isnot(None),
                        SavedContent.extracted_text != ''
                    )
                    # Optionally, filter out test/generic content
                    query = query.filter(~SavedContent.title.ilike('%test%'))
                    content_objs = query.order_by(SavedContent.quality_score.desc(), SavedContent.saved_at.desc()).limit(200).all()
                    content_list = []
                    for content in content_objs:
                        # Use normalize_content_data if available
                        try:
                            normalized = self.data_layer.normalize_content_data(content)
                        except Exception:
                            normalized = {
                                'id': content.id,
                                'title': content.title,
                                'url': content.url,
                                'extracted_text': content.extracted_text,
                                'quality_score': content.quality_score,
                                'technologies': getattr(content, 'technologies', []),
                                'content_type': getattr(content, 'content_type', 'article'),
                                'difficulty': getattr(content, 'difficulty', 'intermediate'),
                                'key_concepts': [],
                            }
                        content_list.append(normalized)
                    logger.info(f"[FastSemanticEngine] Fetched {len(content_list)} candidates from DB.")
                except Exception as e:
                    logger.error(f"[FastSemanticEngine] Error fetching content from DB: {e}")
                    content_list = []
            
            # Filter out low-quality/incomplete content
            filtered_content = []
            for c in content_list:
                title = c.get('title', '').strip().lower()
                url = c.get('url', '').strip()
                extracted_text = c.get('extracted_text', '').strip()
                quality_score = c.get('quality_score', 0)
                if not title or title.startswith('here are some') or len(title) < 10:
                    continue
                if not url or url in ('', '#', 'http://', 'https://'):
                    continue
                if not extracted_text or len(extracted_text) < 20:
                    continue
                if quality_score < 6:
                    continue
                filtered_content.append(c)
            content_list = filtered_content
            
            # OPTIMIZATION 1: Simplified request text creation
            request_text = f"{request.title} {request.description} {request.technologies}"
            
            # OPTIMIZATION 2: Simplified project context (skip if not critical)
            if request.project_id:
                try:
                    from models import Project
                    project = Project.query.filter_by(id=request.project_id, user_id=request.user_id).first()
                    if project:
                        project_context = f"{project.title} {project.technologies or ''}"
                        request_text += f" {project_context}"
                        logger.debug(f"Enhanced request with project context: {project.title}")
                except Exception as e:
                    logger.debug(f"Could not load project context: {e}")
            
            # OPTIMIZATION 3: Streamlined content text preparation
            content_texts = []
            for content in content_list:
                # Ensure technologies field exists
                technologies = content.get('technologies', [])
                if not isinstance(technologies, list):
                    technologies = []
                
                # OPTIMIZATION: Use shorter text for faster processing
                title = content.get('title', '')[:100]  # Limit title length
                extracted_text = content.get('extracted_text', '')[:200]  # Limit text length
                content_text = f"{title} {extracted_text} {' '.join(technologies[:5])}"  # Limit technologies
                content_texts.append(content_text)
            
            # OPTIMIZATION 4: Use optimized batch similarity calculation
            similarities = self.data_layer.calculate_batch_similarities(request_text, content_texts)
            
            # OPTIMIZATION 5: Streamlined scoring calculation
            recommendations_data = []
            request_techs = [tech.strip().lower() for tech in request.technologies.split(',') if tech.strip()]
            
            for i, content in enumerate(content_list):
                similarity = similarities[i]
                
                # OPTIMIZATION: Simplified technology overlap calculation
                content_techs = content.get('technologies', [])
                if not isinstance(content_techs, list):
                    content_techs = []
                
                # OPTIMIZATION: Use universal semantic matcher for enhanced technology overlap if available
                if hasattr(self.data_layer, 'universal_matcher') and self.data_layer.universal_matcher:
                    try:
                        # Use universal matcher for better technology matching
                        tech_overlap = self.data_layer.universal_matcher.calculate_technology_overlap(
                            f"{request.title} {request.technologies}", 
                            {'technologies': content_techs}
                        )
                    except Exception as e:
                        logger.debug(f"Universal matcher tech overlap failed, using fallback: {e}")
                        tech_overlap = self._calculate_technology_overlap(content_techs, request_techs)
                else:
                    # Fallback to standard technology overlap calculation
                    tech_overlap = self._calculate_technology_overlap(content_techs, request_techs)
                
                # OPTIMIZATION: Simplified scoring with fewer calculations
                # Technology overlap (50%) + Semantic similarity (40%) + Quality (10%)
                final_score = (tech_overlap * 0.5) + (similarity * 0.4) + (content.get('quality_score', 6) / 10.0 * 0.1)
                
                # OPTIMIZATION: Simplified user content boost
                final_score += 0.05  # Reduced boost for speed
                
                # OPTIMIZATION: Skip complex project-specific calculations for speed
                if request.project_id:
                    final_score += 0.02  # Small boost for project context
                
                # OPTIMIZATION: Simplified relevance score boost
                relevance_score = content.get('relevance_score', 0)
                if relevance_score > 0:
                    final_score = min(final_score + (relevance_score * 0.1), 1.0)
                
                # Store data for batch processing
                recommendations_data.append({
                    'content': content,
                    'similarity': similarity,
                    'tech_overlap': tech_overlap,
                    'final_score': final_score,
                    'relevance_score': relevance_score
                })
            
            # Sort and filter for final recommendations
            recommendations_data.sort(key=lambda x: x['final_score'], reverse=True)
            filtered_recommendations = [r for r in recommendations_data if r['final_score'] * 100 >= 5]
            if len(filtered_recommendations) < 3:
                medium_quality = [r for r in recommendations_data if r['final_score'] * 100 >= 15 and r not in filtered_recommendations]
                filtered_recommendations.extend(medium_quality[:2])
            filtered_recommendations = filtered_recommendations[:request.max_recommendations]

            # OPTIMIZATION 6: Skip Gemini reasoning for speed (can be enabled later)
            # gemini_analyzer = get_cached_gemini_analyzer()
            
            # OPTIMIZATION: Simplified content analysis (skip database queries for speed)
            enhanced_recommendations = []
            for rec in filtered_recommendations:
                content = rec['content']
                
                # OPTIMIZATION: Skip ContentAnalysis database queries for speed
                enhanced_rec = {
                    'content_title': content['title'],
                    'content_url': content['url'],
                    'content_technologies': content.get('technologies', []) or [],
                    'score': rec['final_score'],
                    'similarity': rec['similarity'],
                    'tech_overlap': rec['tech_overlap'],
                    'content_type': content.get('content_type', 'article'),
                    'difficulty': content.get('difficulty', 'intermediate'),
                    'quality_score': content.get('quality_score', 6)
                }
                
                enhanced_recommendations.append(enhanced_rec)
            
            # OPTIMIZATION: Skip Gemini reasoning for now to improve speed
            batch_reasons = []

            # OPTIMIZATION 7: Simplified reason generation for speed
            for i, rec in enumerate(filtered_recommendations):
                if batch_reasons and i < len(batch_reasons):
                    rec['reason'] = batch_reasons[i]
                else:
                    # OPTIMIZATION: Use fast reason generation
                    rec['reason'] = self._generate_fast_reason(
                        rec['content'],
                        rec['similarity'],
                        rec['tech_overlap'],
                        request.project_id
                    )

            # Create final UnifiedRecommendationResult list
            recommendations = []
            for rec in filtered_recommendations:
                content = rec['content']
                recommendations.append(UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=rec['final_score'] * 100,
                    reason=rec['reason'],
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 6),
                    engine_used=self.name,
                    confidence=rec['similarity'],
                    metadata={
                        'semantic_similarity': rec['similarity'],
                        'tech_overlap': rec['tech_overlap'],
                        'project_boost': content.get('project_relevance_boost', 0),
                        'relevance_score': rec['relevance_score'],
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                ))

            self._update_performance(start_time, True)
            return recommendations
        except Exception as e:
            logger.error(f"Error in FastSemanticEngine: {e}")
            self._update_performance(start_time, False)
            return []
    
    def _calculate_technology_overlap(self, content_techs: List[str], request_techs: List[str]) -> float:
        """Calculate technology overlap score with improved accuracy"""
        if not content_techs or not request_techs:
            return 0.0
        
        # Normalize to lowercase and clean
        content_set = set([tech.lower().strip() for tech in content_techs if tech.strip()])
        request_set = set([tech.lower().strip() for tech in request_techs if tech.strip()])
        
        if not content_set or not request_set:
            return 0.0
        
        # Calculate exact matches
        exact_matches = len(content_set.intersection(request_set))
        
        # Calculate partial matches (one technology contains another)
        partial_matches = 0
        for req_tech in request_set:
            for content_tech in content_set:
                if req_tech in content_tech or content_tech in req_tech:
                    partial_matches += 0.5
                    break
        
        # Calculate related technology matches
        related_matches = 0
        tech_relations = {
            'javascript': ['js', 'node', 'nodejs', 'react', 'vue', 'angular'],
            'python': ['py', 'django', 'flask', 'fastapi'],
            'java': ['spring', 'maven', 'gradle'],
            'react': ['reactjs', 'jsx', 'tsx'],
            'typescript': ['ts', 'javascript'],
            'node': ['nodejs', 'javascript'],
            'sql': ['mysql', 'postgresql', 'database'],
            'mongodb': ['nosql', 'database'],
            'docker': ['container', 'kubernetes'],
            'aws': ['amazon', 'cloud'],
            'git': ['github', 'gitlab', 'version control']
        }
        
        for req_tech in request_set:
            if req_tech in tech_relations:
                related_techs = tech_relations[req_tech]
                for content_tech in content_set:
                    if content_tech in related_techs:
                        related_matches += 0.3
                        break
        
        # Calculate total matches
        total_matches = exact_matches + partial_matches + related_matches
        
        # Calculate overlap ratio
        union_size = len(content_set.union(request_set))
        overlap_ratio = total_matches / union_size if union_size > 0 else 0.0
        
        # Apply non-linear scaling for better differentiation
        if overlap_ratio >= 0.8:
            return 1.0
        elif overlap_ratio >= 0.6:
            return 0.8
        elif overlap_ratio >= 0.4:
            return 0.6
        elif overlap_ratio >= 0.2:
            return 0.4
        else:
            return overlap_ratio * 2  # Scale up small overlaps
    
    def _generate_fast_reason(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int]) -> str:
        """FAST reason generation for better performance"""
        reasons = []
        
        # OPTIMIZATION: Use simple, fast reason generation
        if similarity > 0.7:
            reasons.append("High semantic similarity")
        elif similarity > 0.5:
            reasons.append("Good semantic match")
        elif similarity > 0.3:
            reasons.append("Moderate semantic relevance")
        
        if tech_overlap > 0.8:
            reasons.append("Excellent technology match")
        elif tech_overlap > 0.5:
            reasons.append("Good technology overlap")
        elif tech_overlap > 0.2:
            reasons.append("Some technology relevance")
        
        quality_score = content.get('quality_score', 6)
        if quality_score >= 8:
            reasons.append("High quality content")
        elif quality_score >= 6:
            reasons.append("Good quality content")
        
        if project_id:
            reasons.append("Project-specific relevance")
        
        # OPTIMIZATION: Return simple reason if no specific reasons found
        if not reasons:
            return "Relevant learning content"
        
        return ". ".join(reasons)
    
    def _generate_reason(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int], request: UnifiedRecommendationRequest) -> str:
        """Generate recommendation reason using Gemini AI for better insights"""
        try:
            # Calculate overall relevance score
            overall_score = (similarity * 0.6 + tech_overlap * 0.4)
            
            # Check if content is not very relevant
            if overall_score < 0.3:
                return self._generate_low_relevance_reason_fast(content, similarity, tech_overlap, project_id, request)
            
            # Use Gemini for high-quality reasoning
            return self._generate_gemini_reasoning_fast(content, similarity, tech_overlap, project_id, request)
            
        except Exception as e:
            logger.warning(f"Gemini reasoning generation failed in FastSemanticEngine: {e}, using fallback")
            return self._generate_fallback_reason_fast(content, similarity, tech_overlap, project_id, request)
    
    def _generate_gemini_reasoning_fast(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int], request: UnifiedRecommendationRequest) -> str:
        """Generate reasoning using Gemini AI for FastSemanticEngine"""
        try:
            gemini_analyzer = get_cached_gemini_analyzer()
            
            # Prepare user context for Gemini
            user_context = {
                'title': request.title,
                'description': request.description,
                'technologies': [tech.strip() for tech in request.technologies.split(',') if tech.strip()],
                'project_type': 'general',
                'learning_needs': [],
                'intent_goal': 'learn'
            }
            
            # Generate reasoning using Gemini
            reason = gemini_analyzer.generate_recommendation_reasoning(content, user_context)
            
            # Add semantic search indicator
            if similarity > 0.7:
                reason += " High semantic relevance to your request."
            
            return reason
            
        except Exception as e:
            logger.error(f"Gemini reasoning failed in FastSemanticEngine: {e}")
            return self._generate_fallback_reason_fast(content, similarity, tech_overlap, project_id)
    
    def _generate_low_relevance_reason_fast(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int], request: UnifiedRecommendationRequest) -> str:
        """Generate reason for low-relevance content using Gemini for FastSemanticEngine"""
        try:
            gemini_analyzer = get_cached_gemini_analyzer()
            
            # Create a special prompt for low-relevance content
            prompt = f"""
            This content has low relevance to the user's request. Generate a brief, honest reason explaining why.
            
            Content:
            - Title: {content.get('title', '')}
            - Technologies: {content.get('technologies', [])}
            - Content Type: {content.get('content_type', '')}
            
            User Request:
            - Title: {request.title}
            - Technologies: {[tech.strip() for tech in request.technologies.split(',') if tech.strip()]}
            
            Semantic Similarity: {similarity:.2f}
            Technology Overlap: {tech_overlap:.2f}
            
            Provide a brief, honest explanation (1 sentence) about why this content might not be very relevant.
            Be direct but helpful.
            """
            
            response = gemini_analyzer._make_gemini_request(prompt)
            if response:
                return response.strip()
            else:
                return f"Limited relevance to your request (similarity: {similarity:.1f}, tech overlap: {tech_overlap:.1f})."
                
        except Exception as e:
            logger.error(f"Low relevance reasoning failed in FastSemanticEngine: {e}")
            return f"Limited relevance to your request (similarity: {similarity:.1f}, tech overlap: {tech_overlap:.1f})."
    
    def _generate_fallback_reason_fast(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int], request: UnifiedRecommendationRequest) -> str:
        """Generate fallback reasoning when Gemini is unavailable for FastSemanticEngine"""
        reasons = []
        
        # Semantic relevance
        if similarity > 0.8:
            reasons.append("Highly relevant to your request")
        elif similarity > 0.6:
            reasons.append("Very relevant to your request")
        elif similarity > 0.4:
            reasons.append("Moderately relevant to your request")
        elif similarity > 0.2:
            reasons.append("Somewhat relevant to your request")
        
        # Technology match
        if tech_overlap > 0.7:
            tech_list = ', '.join(content.get('technologies', [])[:3])
            reasons.append(f"Directly covers {tech_list} technologies")
        elif tech_overlap > 0.4:
            tech_list = ', '.join(content.get('technologies', [])[:2])
            reasons.append(f"Includes {tech_list} technologies")
        elif tech_overlap > 0.2:
            reasons.append("Some technology overlap")
        
        # Quality indicator
        quality_score = content.get('quality_score', 0)
        if quality_score >= 9:
            reasons.append("Exceptional quality content")
        elif quality_score >= 8:
            reasons.append("High-quality content")
        elif quality_score >= 7:
            reasons.append("Good quality content")
        
        # Content type
        content_type = content.get('content_type', 'article')
        if content_type in ['tutorial', 'guide', 'example']:
            reasons.append(f"Practical {content_type} content")
        elif content_type == 'documentation':
            reasons.append("Comprehensive documentation")
        
        # User content boost
        if content.get('is_user_content', False):
            reasons.append("From your saved content")
        
        # Project relevance
        if project_id:
            reasons.append(f"Relevant to your project")
        
        # Relevance score
        relevance_score = content.get('relevance_score', 0)
        if relevance_score > 0.7:
            reasons.append("Highly relevant based on your request")
        elif relevance_score > 0.5:
            reasons.append("Very relevant based on your request")
        
        # Fallback if no specific reasons
        if not reasons:
            if similarity > 0.1:
                reasons.append("Relevant learning material from your saved content")
            else:
                reasons.append("Quality content from your saved bookmarks")
        
        return ". ".join(reasons) + "."
    
    def _update_performance(self, start_time: float, success: bool):
        """Update performance metrics"""
        response_time = (time.time() - start_time) * 1000
        self.performance.response_time_ms = response_time
        self.performance.total_requests += 1
        self.performance.last_used = datetime.utcnow()
        
        if not success:
            self.performance.error_count += 1
        
        self.performance.success_rate = (
            (self.performance.total_requests - self.performance.error_count) / 
            self.performance.total_requests
        )

class ContextAwareEngine:
    """Context-aware recommendation engine (Secondary)"""
    
    def __init__(self, data_layer: UnifiedDataLayer):
        self.data_layer = data_layer
        self.name = "ContextAwareEngine"
        self.performance = EnginePerformance(
            engine_name=self.name,
            response_time_ms=0.0,
            success_rate=1.0,
            cache_hit_rate=0.0,
            error_count=0,
            last_used=datetime.utcnow(),
            total_requests=0
        )
    
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get context-aware recommendations"""
        start_time = time.time()
        
        try:
            # Extract context from request
            context = self._extract_context(request)
            
            recommendations = []
            
            for content in content_list:
                # Calculate comprehensive score
                score_components = self._calculate_score_components(content, context)
                
                # Weighted final score with improved weighting for user content and intent alignment
                final_score = (
                    score_components['technology'] * 0.35 +      # Technology match (35%)
                    score_components['semantic'] * 0.25 +        # Semantic similarity (25%)
                    score_components['content_type'] * 0.15 +    # Content type match (15%)
                    score_components['difficulty'] * 0.10 +      # Difficulty alignment (10%)
                    score_components['quality'] * 0.05 +         # Quality score (5%)
                    score_components['intent_alignment'] * 0.10  # Intent alignment (10%)
                )
                
                # Apply user content boost (all content is user's own)
                final_score += 0.1
                
                # Apply relevance score boost
                relevance_score = content.get('relevance_score', 0)
                if relevance_score > 0:
                    final_score = min(final_score + (relevance_score * 0.15), 1.0)
                
                # Generate detailed reason
                reason = self._generate_detailed_reason(content, context, score_components)
                
                # Create result
                result = UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=final_score * 100,
                    reason=reason,
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 6),
                    engine_used=self.name,
                    confidence=score_components['semantic'],
                    metadata={
                        'score_components': score_components,
                        'context_used': context,
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                )
                
                recommendations.append(result)
            
            # Sort and limit
            recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # Filter out low-quality recommendations
            min_score_threshold = 25  # Minimum score to be considered relevant
            filtered_recommendations = [r for r in recommendations if r.score >= min_score_threshold]
            
            # If we don't have enough high-quality recommendations, include some medium quality
            if len(filtered_recommendations) < 3:
                medium_threshold = 15
                medium_quality = [r for r in recommendations if r.score >= medium_threshold and r not in filtered_recommendations]
                filtered_recommendations.extend(medium_quality[:2])  # Add max 2 medium quality
            
            # Limit to requested number
            filtered_recommendations = filtered_recommendations[:request.max_recommendations]
            
            # Update performance
            self._update_performance(start_time, True)
            
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Error in ContextAwareEngine: {e}")
            self._update_performance(start_time, False)
            return []
    
    def _extract_context(self, request: UnifiedRecommendationRequest) -> Dict[str, Any]:
        """Extract context from request with intent analysis enhancement"""
        # Extract technologies
        technologies = [tech.strip() for tech in request.technologies.split(',') if tech.strip()]
        
        # Use intent analysis if available
        intent_analysis = getattr(request, 'intent_analysis', None)
        
        if intent_analysis:
            # Use intent analysis for better context
            technologies.extend(intent_analysis.get('specific_technologies', []))
            technologies = list(set(technologies))  # Remove duplicates
            
            # Determine content type preference based on intent
            content_type = 'general'
            time_constraint = intent_analysis.get('time_constraint', 'deep_dive')
            if time_constraint == 'quick_tutorial':
                content_type = 'tutorial'
            elif time_constraint == 'reference':
                content_type = 'documentation'
            elif 'tutorial' in request.description.lower() or 'learn' in request.description.lower():
                content_type = 'tutorial'
            elif 'documentation' in request.description.lower() or 'api' in request.description.lower():
                content_type = 'documentation'
            elif 'example' in request.description.lower() or 'demo' in request.description.lower():
                content_type = 'example'
            
            # Use intent learning stage for difficulty
            difficulty = intent_analysis.get('learning_stage', 'intermediate')
            
            # Add intent-based context
            context = {
                'technologies': technologies,
                'content_type': content_type,
                'difficulty': difficulty,
                'title': request.title,
                'description': request.description,
                'user_interests': request.user_interests,
                'intent_goal': intent_analysis.get('primary_goal', 'learn'),
                'project_type': intent_analysis.get('project_type', 'general'),
                'urgency_level': intent_analysis.get('urgency_level', 'medium'),
                'complexity_preference': intent_analysis.get('complexity_preference', 'moderate'),
                'focus_areas': intent_analysis.get('focus_areas', [])
            }
        else:
            # Fallback to original logic
            content_type = 'general'
            if 'tutorial' in request.description.lower() or 'learn' in request.description.lower():
                content_type = 'tutorial'
            elif 'documentation' in request.description.lower() or 'api' in request.description.lower():
                content_type = 'documentation'
            elif 'example' in request.description.lower() or 'demo' in request.description.lower():
                content_type = 'example'
            
            difficulty = 'intermediate'
            if 'beginner' in request.description.lower() or 'basic' in request.description.lower():
                difficulty = 'beginner'
            elif 'advanced' in request.description.lower() or 'expert' in request.description.lower():
                difficulty = 'advanced'
            
            context = {
                'technologies': technologies,
                'content_type': content_type,
                'difficulty': difficulty,
                'title': request.title,
                'description': request.description,
                'user_interests': request.user_interests
            }
        
        return context
    
    def _calculate_score_components(self, content: Dict, context: Dict) -> Dict[str, float]:
        """Calculate individual score components with enhanced intent analysis"""
        components = {}
        
        # Ensure technologies fields exist
        content_techs = content.get('technologies', [])
        if not isinstance(content_techs, list):
            content_techs = []
        
        context_techs = context.get('technologies', [])
        if not isinstance(context_techs, list):
            context_techs = []
        
        # Semantic similarity
        request_text = f"{context['title']} {context['description']} {' '.join(context_techs)}"
        content_text = f"{content['title']} {content['extracted_text']} {' '.join(content_techs)}"
        components['semantic'] = self.data_layer.calculate_semantic_similarity(request_text, content_text)
        
        # Technology match with intent enhancement
        tech_overlap = self._calculate_enhanced_technology_overlap(content_techs, context_techs, context)
        components['technology'] = tech_overlap
        
        # Content type match with intent enhancement
        content_type_match = self._calculate_enhanced_content_type_match(content, context)
        components['content_type'] = content_type_match
        
        # Difficulty match with intent enhancement
        difficulty_match = self._calculate_enhanced_difficulty_match(content, context)
        components['difficulty'] = difficulty_match
        
        # Quality score
        quality_score = content.get('quality_score', 6) / 10.0
        components['quality'] = quality_score
        
        # Intent alignment score (new component)
        intent_alignment = self._calculate_intent_alignment(content, context)
        components['intent_alignment'] = intent_alignment
        
        return components
    
    def _calculate_enhanced_technology_overlap(self, content_techs: List[str], context_techs: List[str], context: Dict) -> float:
        """Calculate enhanced technology overlap with intent awareness"""
        if not context_techs:
            return 0.5
        
        # Calculate exact matches
        exact_matches = set(content_techs).intersection(set(context_techs))
        exact_score = len(exact_matches) / len(context_techs)
        
        # Calculate partial matches for technology variations
        partial_matches = 0
        for context_tech in context_techs:
            for content_tech in content_techs:
                if (context_tech in content_tech or content_tech in context_tech) and context_tech != content_tech:
                    partial_matches += 0.5
        
        partial_score = min(partial_matches / len(context_techs), 0.3)
        tech_score = exact_score + partial_score
        
        # Apply intent-based boosting
        intent_goal = context.get('intent_goal', '')
        if intent_goal in ['build', 'implement', 'optimize']:
            # Boost for implementation-focused intents
            tech_score *= 1.2
        elif intent_goal == 'learn':
            # Boost for learning-focused intents
            tech_score *= 1.1
        
        return min(1.0, tech_score)
    
    def _calculate_fast_technology_overlap(self, content_techs: List[str], request_techs: List[str]) -> float:
        """FAST technology overlap calculation for better performance"""
        if not content_techs or not request_techs:
            return 0.0
        
        # OPTIMIZATION: Use set operations for faster calculation
        content_set = set([tech.lower().strip() for tech in content_techs if tech.strip()])
        request_set = set([tech.lower().strip() for tech in request_techs if tech.strip()])
        
        if not content_set or not request_set:
            return 0.0
        
        # OPTIMIZATION: Calculate only exact matches for speed
        exact_matches = len(content_set.intersection(request_set))
        
        # OPTIMIZATION: Simplified scoring without partial matches
        tech_score = exact_matches / len(request_set) if request_set else 0.0
        
        return min(1.0, tech_score)
    
    def _calculate_enhanced_content_type_match(self, content: Dict, context: Dict) -> Dict[str, float]:
        """Calculate enhanced content type match with intent awareness"""
        content_type = content.get('content_type', 'article')
        context_type = context.get('content_type', 'general')
        
        # Base content type match
        if content_type == context_type:
            base_score = 1.0
        elif context_type in ['general', 'mixed'] or content_type in ['general', 'mixed']:
            base_score = 0.7
        else:
            base_score = 0.3
        
        # Apply intent-based adjustments
        intent_goal = context.get('intent_goal', '')
        time_constraint = context.get('time_constraint', 'deep_dive')
        
        if intent_goal == 'learn' and time_constraint == 'quick_tutorial' and content_type == 'tutorial':
            base_score *= 1.2
        elif intent_goal == 'learn' and time_constraint == 'deep_dive' and content_type in ['documentation', 'course']:
            base_score *= 1.2
        elif intent_goal == 'build' and content_type == 'example':
            base_score *= 1.2
        elif intent_goal == 'optimize' and content_type == 'best_practice':
            base_score *= 1.2
        
        return min(1.0, base_score)
    
    def _calculate_enhanced_difficulty_match(self, content: Dict, context: Dict) -> float:
        """Calculate enhanced difficulty match with intent awareness"""
        content_difficulty = content.get('difficulty', 'intermediate')
        context_difficulty = context.get('difficulty', 'intermediate')
        
        # Difficulty mapping
        difficulty_mapping = {
            'beginner': 1,
            'intermediate': 2,
            'advanced': 3
        }
        
        content_level = difficulty_mapping.get(content_difficulty, 2)
        context_level = difficulty_mapping.get(context_difficulty, 2)
        
        # Calculate difficulty alignment
        if content_level == context_level:
            difficulty_score = 1.0
        elif abs(content_level - context_level) == 1:
            difficulty_score = 0.8
        elif abs(content_level - context_level) == 2:
            difficulty_score = 0.4
        else:
            difficulty_score = 0.2
        
        # Apply intent-based adjustments
        intent_goal = context.get('intent_goal', '')
        if intent_goal == 'learn':
            # For learning, prefer slightly challenging content
            if content_level == context_level + 1:
                difficulty_score *= 1.1
            elif content_level == context_level - 1:
                difficulty_score *= 0.9
        
        return min(1.0, difficulty_score)
    
    def _calculate_intent_alignment(self, content: Dict, context: Dict) -> float:
        """Calculate intent alignment score"""
        intent_goal = context.get('intent_goal', '')
        project_type = context.get('project_type', '')
        focus_areas = context.get('focus_areas', [])
        
        if not intent_goal:
            return 0.5
        
        intent_score = 0.0
        factors = 0
        
        # 1. Project type alignment
        if project_type:
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
            if project_type in ['web_app', 'mobile_app', 'api', 'data_science']:
                if any(tech in content_text for tech in [project_type, 'web', 'mobile', 'api', 'data']):
                    intent_score += 1.0
                else:
                    intent_score += 0.3
            factors += 1
        
        # 2. Focus areas alignment
        if focus_areas:
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
            focus_matches = sum(1 for area in focus_areas if area.lower() in content_text)
            if focus_areas:
                intent_score += (focus_matches / len(focus_areas))
            factors += 1
        
        # 3. Intent goal alignment
        if intent_goal == 'learn':
            # Prefer tutorial and documentation content for learning
            content_type = content.get('content_type', 'article')
            if content_type in ['tutorial', 'documentation', 'course']:
                intent_score += 1.0
            else:
                intent_score += 0.5
        elif intent_goal == 'build':
            # Prefer example and tutorial content for building
            content_type = content.get('content_type', 'article')
            if content_type in ['example', 'tutorial', 'project']:
                intent_score += 1.0
            else:
                intent_score += 0.5
        elif intent_goal == 'optimize':
            # Prefer best practice and documentation content for optimization
            content_type = content.get('content_type', 'article')
            if content_type in ['best_practice', 'documentation']:
                intent_score += 1.0
            else:
                intent_score += 0.5
        
        factors += 1
        
        # Return average score
        return intent_score / factors if factors > 0 else 0.5
    
    def _generate_detailed_reason(self, content: Dict, context: Dict, components: Dict[str, float]) -> str:
        """Generate detailed reason with enhanced intent awareness"""
        reasons = []
        
        # Technology match explanation
        if components.get('technology', 0) > 0.6:
            tech_explanation = self._get_tech_explanation(content, context)
            if tech_explanation:
                reasons.append(tech_explanation)
        
        # Intent-based explanation
        intent_goal = context.get('intent_goal', '')
        if intent_goal:
            intent_explanation = self._get_intent_explanation(content, context)
            if intent_explanation:
                reasons.append(intent_explanation)
        
        # Content type benefit
        content_type_benefit = self._get_content_type_benefit(content, context)
        if content_type_benefit:
            reasons.append(content_type_benefit)
        
        # Difficulty alignment note
        difficulty_note = self._get_difficulty_note(content, context)
        if difficulty_note:
            reasons.append(difficulty_note)
        
        # Project type alignment
        project_type = context.get('project_type', '')
        if project_type:
            project_note = self._get_project_type_note(content, context)
            if project_note:
                reasons.append(project_note)
        
        # Relevance strength
        total_score = sum(components.values()) / len(components) if components else 0
        relevance_strength = self._get_relevance_strength(total_score)
        if relevance_strength:
            reasons.append(relevance_strength)
        
        # Combine reasons
        if reasons:
            return " ".join(reasons)
        else:
            return "This content matches your project requirements."
    
    def _get_tech_explanation(self, content: Dict, context: Dict) -> str:
        """Get technology match explanation"""
        content_techs = content.get('technologies', [])
        context_techs = context.get('technologies', [])
        
        if not context_techs or not content_techs:
            return ""
        
        # Find overlapping technologies
        overlap = set(content_techs).intersection(set(context_techs))
        
        if overlap:
            tech_list = ", ".join(sorted(overlap))
            if len(overlap) == 1:
                return f"Directly covers {tech_list} technology that you're working with."
            else:
                return f"Comprehensive coverage of {tech_list} technologies relevant to your project."
        
        return ""
    
    def _get_intent_explanation(self, content: Dict, context: Dict) -> str:
        """Get intent-based explanation"""
        intent_goal = context.get('intent_goal', '')
        project_type = context.get('project_type', '')
        content_type = content.get('content_type', 'article')
        
        if not intent_goal:
            return ""
        
        # Intent mapping
        intent_mapping = {
            'learn': {
                'tutorial': f"Provides structured learning path for {project_type or 'your project'}",
                'documentation': f"Offers comprehensive reference for {project_type or 'your project'}",
                'example': f"Demonstrates practical examples of {project_type or 'your project'}",
                'best_practice': f"Teaches best practices for {project_type or 'your project'}",
                'general': f"Helps you learn about {project_type or 'your project'}"
            },
            'build': {
                'tutorial': f"Guides you through building {project_type or 'your project'}",
                'documentation': f"Provides implementation details for {project_type or 'your project'}",
                'example': f"Shows how to build {project_type or 'your project'}",
                'best_practice': f"Demonstrates proper implementation of {project_type or 'your project'}",
                'general': f"Helps you build {project_type or 'your project'}"
            },
            'optimize': {
                'tutorial': f"Teaches optimization techniques for {project_type or 'your project'}",
                'documentation': f"Provides optimization guidelines for {project_type or 'your project'}",
                'example': f"Demonstrates optimized approaches to {project_type or 'your project'}",
                'best_practice': f"Shows performance best practices for {project_type or 'your project'}",
                'general': f"Helps you optimize {project_type or 'your project'}"
            }
        }
        
        intent_explanations = intent_mapping.get(intent_goal, {})
        explanation = intent_explanations.get(content_type, intent_explanations.get('general', ''))
        
        if explanation:
            # Add learning stage context
            learning_stage = context.get('difficulty', 'intermediate')
            if learning_stage and learning_stage != 'intermediate':
                explanation += f" (suitable for {learning_stage} level)"
            
            return explanation
        
        return ""
    
    def _get_content_type_benefit(self, content: Dict, context: Dict) -> str:
        """Get content type specific benefits with intent awareness"""
        content_type = content.get('content_type', 'article')
        intent_goal = context.get('intent_goal', '')
        time_constraint = context.get('time_constraint', 'deep_dive')
        
        benefits = {
            'tutorial': "Includes step-by-step instructions and explanations.",
            'documentation': "Provides comprehensive technical reference and API details.",
            'example': "Offers practical code examples and real-world scenarios.",
            'troubleshooting': "Focuses on problem-solving and debugging techniques.",
            'best_practice': "Teaches industry standards and proven patterns.",
            'project': "Shows complete project implementation from start to finish."
        }
        
        base_benefit = benefits.get(content_type, "")
        
        # Add intent-specific context
        if intent_goal == 'learn' and time_constraint == 'quick_tutorial':
            base_benefit += " Perfect for quick learning."
        elif intent_goal == 'build' and content_type == 'example':
            base_benefit += " Ideal for implementation reference."
        elif intent_goal == 'optimize' and content_type == 'best_practice':
            base_benefit += " Essential for performance optimization."
        
        return base_benefit
    
    def _get_difficulty_note(self, content: Dict, context: Dict) -> str:
        """Get difficulty alignment explanation with intent awareness"""
        content_difficulty = content.get('difficulty', 'intermediate')
        context_difficulty = context.get('difficulty', 'intermediate')
        
        if content_difficulty == context_difficulty:
            return f"Difficulty level ({content_difficulty}) matches your skill level."
        elif content_difficulty == 'beginner' and context_difficulty in ['intermediate', 'advanced']:
            return "Provides foundational knowledge that builds up to your project complexity."
        elif content_difficulty == 'advanced' and context_difficulty in ['beginner', 'intermediate']:
            return "Offers advanced insights that will help you grow beyond current requirements."
        else:
            return f"Appropriate difficulty level ({content_difficulty}) for your needs."
    
    def _get_project_type_note(self, content: Dict, context: Dict) -> str:
        """Get project type alignment note"""
        project_type = context.get('project_type', '')
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        
        if project_type == 'web_app' and any(tech in content_text for tech in ['react', 'vue', 'angular', 'html', 'css', 'web']):
            return "Specifically addresses web application development needs."
        elif project_type == 'mobile_app' and any(tech in content_text for tech in ['react native', 'flutter', 'ios', 'android', 'mobile']):
            return "Specifically addresses mobile application development needs."
        elif project_type == 'api' and any(tech in content_text for tech in ['api', 'rest', 'graphql', 'backend', 'server']):
            return "Specifically addresses API development needs."
        elif project_type == 'data_science' and any(tech in content_text for tech in ['data', 'ml', 'ai', 'analytics', 'python']):
            return "Specifically addresses data science and ML needs."
        
        return ""
    
    def _get_relevance_strength(self, total_score: float) -> str:
        """Get relevance strength indicator"""
        if total_score >= 0.85:
            return "This is a highly relevant resource for your needs."
        elif total_score >= 0.70:
            return "This resource is very relevant to your project."
        elif total_score >= 0.50:
            return "This content is relevant and worth considering."
        else:
            return "This may be useful as supplementary material."
    
    def _generate_gemini_reasoning(self, content: Dict, context: Dict, components: Dict[str, float]) -> str:
        """Generate reasoning using Gemini AI"""
        try:
            gemini_analyzer = get_cached_gemini_analyzer()
            
            # Prepare user context for Gemini
            user_context = {
                'title': context.get('title', ''),
                'description': context.get('description', ''),
                'technologies': context.get('technologies', []),
                'project_type': context.get('project_type', 'general'),
                'learning_needs': context.get('focus_areas', []),
                'intent_goal': context.get('intent_goal', 'learn')
            }
            
            # Generate reasoning using Gemini
            reason = gemini_analyzer.generate_recommendation_reasoning(content, user_context)
            
            # Add AI insights indicator
            if context.get('intent_goal') or context.get('project_type') or context.get('focus_areas'):
                reason += " Enhanced with AI-powered intent analysis."
            
            return reason
            
        except Exception as e:
            logger.error(f"Gemini reasoning failed: {e}")
            return self._generate_fallback_reason(content, context, components)
    
    def _generate_low_relevance_reason(self, content: Dict, context: Dict, overall_score: float) -> str:
        """Generate reason for low-relevance content using Gemini"""
        try:
            gemini_analyzer = get_cached_gemini_analyzer()
            
            # Create a special prompt for low-relevance content
            prompt = f"""
            This content has low relevance to the user's project. Generate a brief, honest reason explaining why.
            
            Content:
            - Title: {content.get('title', '')}
            - Technologies: {content.get('technologies', [])}
            - Content Type: {content.get('content_type', '')}
            
            User Project:
            - Title: {context.get('title', '')}
            - Technologies: {context.get('technologies', [])}
            - Project Type: {context.get('project_type', '')}
            
            Relevance Score: {overall_score:.2f}
            
            Provide a brief, honest explanation (1 sentence) about why this content might not be very relevant.
            Be direct but helpful.
            """
            
            response = gemini_analyzer._make_gemini_request(prompt)
            if response:
                return response.strip()
            else:
                return f"Limited relevance to your {context.get('project_type', 'project')} (score: {overall_score:.1f})."
                
        except Exception as e:
            logger.error(f"Low relevance reasoning failed: {e}")
            return f"Limited relevance to your {context.get('project_type', 'project')} (score: {overall_score:.1f})."
    
    def _generate_fallback_reason(self, content: Dict, context: Dict, components: Dict[str, float]) -> str:
        """Generate fallback reasoning when Gemini is unavailable"""
        reasons = []
        
        # Technology match
        if components.get('technology', 0) > 0.5:
            tech_list = ', '.join(content.get('technologies', [])[:3])
            reasons.append(f"Directly covers {tech_list} technologies")
        elif components.get('technology', 0) > 0.2:
            reasons.append("Some technology overlap with your project")
        
        # Content type
        if components.get('content_type', 0) > 0.8:
            reasons.append(f"Perfect {content.get('content_type', 'article')} content for your needs")
        elif components.get('content_type', 0) > 0.5:
            reasons.append(f"Good {content.get('content_type', 'article')} material")
        
        # Quality
        if components.get('quality', 0) > 0.8:
            reasons.append("High-quality, well-curated content")
        
        # Semantic relevance
        if components.get('semantic', 0) > 0.7:
            reasons.append("High semantic relevance to your project")
        
        # User content boost
        if content.get('is_user_content', False):
            reasons.append("From your saved content")
        
        if not reasons:
            reasons.append("Quality content from your saved bookmarks")
        
        return ". ".join(reasons) + "."
    
    def _update_performance(self, start_time: float, success: bool):
        """Update performance metrics"""
        response_time = (time.time() - start_time) * 1000
        self.performance.response_time_ms = response_time
        self.performance.total_requests += 1
        self.performance.last_used = datetime.utcnow()
        
        if not success:
            self.performance.error_count += 1
        
        self.performance.success_rate = (
            (self.performance.total_requests - self.performance.error_count) / 
            self.performance.total_requests
        )

class UnifiedRecommendationOrchestrator:
    """Main orchestrator that coordinates all engines"""
    
    def __init__(self):
        self.data_layer = UnifiedDataLayer()
        self.fast_engine = FastSemanticEngine(self.data_layer)
        self.context_engine = ContextAwareEngine(self.data_layer)
        
        # Engine registry
        self.engines = {
            'fast': self.fast_engine,
            'context': self.context_engine
        }
        
        # Performance tracking
        self.performance_history = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("Unified Recommendation Orchestrator initialized")
    
    def get_recommendations(self, request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get recommendations using orchestrated approach with intent analysis - OPTIMIZED FOR PERFORMANCE"""
        start_time = time.time()
        
        try:
            # OPTIMIZATION 1: Check cache first for better performance
            cache_key = self._generate_cache_key(request)
            try:
                cached_result = redis_cache.get_cache(cache_key)
            except Exception as e:
                logger.warning(f"Cache check failed: {e}")
                cached_result = None
            if cached_result:
                logger.info(f"Cache hit for recommendations: {cache_key}")
                # Convert cached data back to UnifiedRecommendationResult objects
                cached_recommendations = []
                for rec_data in cached_result:
                    rec = UnifiedRecommendationResult(
                        id=rec_data['id'],
                        title=rec_data['title'],
                        url=rec_data['url'],
                        score=rec_data['score'],
                        reason=rec_data['reason'],
                        content_type=rec_data['content_type'],
                        difficulty=rec_data['difficulty'],
                        technologies=rec_data['technologies'],
                        key_concepts=rec_data['key_concepts'],
                        quality_score=rec_data['quality_score'],
                        engine_used=rec_data['engine_used'],
                        confidence=rec_data['confidence'],
                        metadata=rec_data['metadata'],
                        cached=True
                    )
                    cached_recommendations.append(rec)
                
                # Update performance metrics
                self.cache_hits += 1
                return cached_recommendations
            
            # OPTIMIZATION 2: Cache miss - proceed with normal processing
            logger.info(f"Cache miss for recommendations: {cache_key}")
            self.cache_misses += 1
            # Perform intent analysis (with caching and fallback)
            user_input = f"{request.title} {request.description} {request.technologies} {request.user_interests}".strip()
            try:
                intent = analyze_user_intent(user_input, request.project_id)
            except Exception as e:
                logger.warning(f"⚠️ Intent analysis failed (likely quota): {e}, using fallback")
                from intent_analysis_engine import get_fallback_intent
                intent = get_fallback_intent(user_input, request.project_id)
            
            # Generate cache key including intent
            cache_key = self._generate_cache_key_with_intent(request, intent)
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.cache_hits += 1
                logger.info(f"Cache hit for request: {request.title[:50]}...")
                return cached_result
            
            self.cache_misses += 1
            
            # Get candidate content
            content_list = self.data_layer.get_candidate_content(request.user_id, request)
            
            if not content_list:
                logger.warning("No candidate content found")
                return []
            
            # Enhance request with intent analysis
            enhanced_request = self._enhance_request_with_intent(request, intent)
            
            # Select and execute engine with enhanced context
            recommendations = self._execute_engine_strategy(enhanced_request, content_list)
            
            # Cache results
            self._cache_result(cache_key, recommendations, request.cache_duration)
            
            # Log performance
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Recommendations generated in {response_time:.2f}ms using {recommendations[0].engine_used if recommendations else 'no engine'} with intent: {intent.primary_goal}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            return []
    
    def _execute_engine_strategy(self, request: UnifiedRecommendationRequest, content_list: List[Dict]) -> List[UnifiedRecommendationResult]:
        """Execute engine selection strategy"""
        
        # Engine selection logic - ContextAwareEngine is now the default
        if request.engine_preference == 'fast':
            return self.fast_engine.get_recommendations(content_list, request)
        elif request.engine_preference == 'context':
            return self.context_engine.get_recommendations(content_list, request)
        else:
            # Default to ContextAwareEngine for better quality (unless explicitly overridden)
            return self.context_engine.get_recommendations(content_list, request)
    
    def _auto_select_engine(self, request: UnifiedRecommendationRequest, content_list: List[Dict]) -> List[UnifiedRecommendationResult]:
        """Auto-select best engine based on request characteristics"""
        
        # ALWAYS use ContextAwareEngine by default for better quality
        # Only use FastSemanticEngine for very simple requests or when explicitly requested
        request_complexity = self._assess_request_complexity(request)
        
        # Use ContextAwareEngine for most requests (better quality)
        if request_complexity == 'simple' and len(request.title) < 20 and len(request.description) < 50:
            # Only use fast engine for very simple requests
            return self.fast_engine.get_recommendations(content_list, request)
        else:
            # Use context engine for everything else (default)
            return self.context_engine.get_recommendations(content_list, request)
    
    def _assess_request_complexity(self, request: UnifiedRecommendationRequest) -> str:
        """Assess request complexity"""
        complexity_score = 0
        
        # Title length
        if len(request.title) > 50:
            complexity_score += 1
        
        # Description length
        if len(request.description) > 100:
            complexity_score += 1
        
        # Number of technologies
        tech_count = len([tech for tech in request.technologies.split(',') if tech.strip()])
        if tech_count > 3:
            complexity_score += 1
        
        # User interests
        if len(request.user_interests) > 50:
            complexity_score += 1
        
        return 'complex' if complexity_score >= 2 else 'simple'
    
    def _generate_cache_key(self, request: UnifiedRecommendationRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        
        # Create unique string from request
        request_str = f"{request.user_id}:{request.title}:{request.description}:{request.technologies}:{request.max_recommendations}:{request.engine_preference}"
        
        # Generate hash
        return f"unified_recommendations:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    def _generate_cache_key_with_intent(self, request: 'UnifiedRecommendationRequest', intent: Any) -> str:
        """Generate cache key including intent analysis"""
        import hashlib
        
        # Create unique string from request and intent
        request_str = f"{request.user_id}:{request.title}:{request.description}:{request.technologies}:{request.max_recommendations}:{request.engine_preference}:{intent.context_hash}"
        
        # Generate hash
        return f"unified_recommendations_intent:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    def _generate_cache_key(self, request: UnifiedRecommendationRequest) -> str:
        """Generate cache key for request - OPTIMIZED VERSION"""
        import hashlib
        
        # OPTIMIZATION: Create shorter, more efficient cache key
        request_str = f"{request.user_id}:{request.title[:50]}:{request.technologies}:{request.max_recommendations}:{request.engine_preference}"
        
        # Generate hash
        return f"unified_recommendations:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    def _enhance_request_with_intent(self, request: 'UnifiedRecommendationRequest', intent: Any) -> 'UnifiedRecommendationRequest':
        """Enhance request with intent analysis results"""
        # Create enhanced request with intent context
        enhanced_request = UnifiedRecommendationRequest(
            user_id=request.user_id,
            title=request.title,
            description=request.description,
            technologies=request.technologies,
            user_interests=request.user_interests,
            project_id=request.project_id,
            max_recommendations=request.max_recommendations,
            engine_preference=request.engine_preference,
            diversity_weight=request.diversity_weight,
            quality_threshold=request.quality_threshold,
            include_global_content=request.include_global_content,
            cache_duration=request.cache_duration
        )
        
        # Add intent metadata to request with enhanced scoring weights
        enhanced_request.intent_analysis = {
            'primary_goal': intent.primary_goal,
            'learning_stage': intent.learning_stage,
            'project_type': intent.project_type,
            'urgency_level': intent.urgency_level,
            'specific_technologies': intent.specific_technologies,
            'complexity_preference': intent.complexity_preference,
            'time_constraint': intent.time_constraint,
            'focus_areas': intent.focus_areas,
            'context_hash': intent.context_hash,
            # Enhanced scoring weights based on intent
            'scoring_weights': {
                'technology_match': self._get_tech_match_weight(intent),
                'content_type_match': self._get_content_type_weight(intent),
                'difficulty_alignment': self._get_difficulty_weight(intent),
                'urgency_boost': self._get_urgency_weight(intent),
                'learning_stage_alignment': self._get_learning_stage_weight(intent)
            }
        }
        
        return enhanced_request
    
    def _get_tech_match_weight(self, intent: Any) -> float:
        """Get technology match weight based on intent"""
        # Higher weight for technology-focused intents
        if intent.primary_goal in ['build', 'implement', 'optimize']:
            return 0.4  # 40% weight for technology matching
        elif intent.primary_goal == 'learn':
            return 0.35  # 35% weight for learning
        else:
            return 0.3  # 30% default weight
    
    def _get_content_type_weight(self, intent: Any) -> float:
        """Get content type match weight based on intent"""
        # Higher weight for specific content type needs
        if intent.time_constraint == 'quick_tutorial':
            return 0.25  # 25% weight for quick content
        elif intent.time_constraint == 'deep_dive':
            return 0.2  # 20% weight for comprehensive content
        else:
            return 0.15  # 15% default weight
    
    def _get_difficulty_weight(self, intent: Any) -> float:
        """Get difficulty alignment weight based on intent"""
        # Higher weight for learning-focused intents
        if intent.primary_goal == 'learn':
            return 0.25  # 25% weight for difficulty matching
        else:
            return 0.15  # 15% default weight
    
    def _get_urgency_weight(self, intent: Any) -> float:
        """Get urgency boost weight based on intent"""
        # Higher weight for urgent requests
        if intent.urgency_level == 'high':
            return 0.2  # 20% weight for urgency
        elif intent.urgency_level == 'medium':
            return 0.1  # 10% weight for medium urgency
        else:
            return 0.05  # 5% weight for low urgency
    
    def _get_learning_stage_weight(self, intent: Any) -> float:
        """Get learning stage alignment weight based on intent"""
        # Higher weight for learning intents
        if intent.primary_goal == 'learn':
            return 0.2  # 20% weight for learning stage
        else:
            return 0.1  # 10% default weight
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[UnifiedRecommendationResult]]:
        """Get cached result"""
        try:
            cached_data = redis_cache.get_cache(cache_key)
            if cached_data:
                # Convert back to UnifiedRecommendationResult objects
                results = []
                for item in cached_data:
                    result = UnifiedRecommendationResult(**item)
                    result.cached = True
                    results.append(result)
                return results
            return None
        except Exception as e:
            logger.error(f"Error getting cached result: {e}")
            return None
    
    def _cache_result(self, cache_key: str, results: List[UnifiedRecommendationResult], ttl: int):
        """Cache result"""
        try:
            # Convert to serializable format
            cache_data = [asdict(result) for result in results]
            redis_cache.set_cache(cache_key, cache_data, ttl)
        except Exception as e:
            logger.error(f"Error caching result: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'engines': {
                name: {
                    'response_time_ms': engine.performance.response_time_ms,
                    'success_rate': engine.performance.success_rate,
                    'total_requests': engine.performance.total_requests,
                    'error_count': engine.performance.error_count,
                    'last_used': engine.performance.last_used.isoformat()
                }
                for name, engine in self.engines.items()
            }
        }

    # ============================================================================
    # ROBUST INTENT ANALYSIS INTEGRATION - Added for reliability and performance
    # ============================================================================

    def get_intent_analysis_robust(self, request: UnifiedRecommendationRequest) -> Optional[Dict]:
        """Get intent analysis with multiple fallback layers"""
        try:
            # Layer 1: Try AI analysis
            user_input = f"{request.title} {request.description} {request.technologies}"
            from intent_analysis_engine import analyze_user_intent
            intent = analyze_user_intent(user_input, request.project_id)
            
            if intent and intent.primary_goal != 'learn':  # Valid analysis
                return {
                    'primary_goal': intent.primary_goal,
                    'learning_stage': intent.learning_stage,
                    'project_type': intent.project_type,
                    'urgency_level': intent.urgency_level,
                    'specific_technologies': intent.specific_technologies,
                    'complexity_preference': intent.complexity_preference,
                    'time_constraint': intent.time_constraint,
                    'focus_areas': intent.focus_areas
                }
        
        except Exception as e:
            logger.warning(f"AI intent analysis failed: {e}")
        
        try:
            # Layer 2: Try project-based analysis
            if request.project_id:
                from models import Project
                project = Project.query.get(request.project_id)
                if project and project.intent_analysis:
                    return json.loads(project.intent_analysis)
        
        except Exception as e:
            logger.warning(f"Project-based analysis failed: {e}")
        
        try:
            # Layer 3: Use fallback analysis
            from intent_analysis_engine import get_fallback_intent
            fallback_intent = get_fallback_intent(
                f"{request.title} {request.description} {request.technologies}"
            )
            return {
                'primary_goal': fallback_intent.primary_goal,
                'learning_stage': fallback_intent.learning_stage,
                'project_type': fallback_intent.project_type,
                'urgency_level': fallback_intent.urgency_level,
                'specific_technologies': fallback_intent.specific_technologies,
                'complexity_preference': fallback_intent.complexity_preference,
                'time_constraint': fallback_intent.time_constraint,
                'focus_areas': fallback_intent.focus_areas
            }
        
        except Exception as e:
            logger.error(f"All intent analysis methods failed: {e}")
            return None

    def get_recommendations_robust(self, request: UnifiedRecommendationRequest):
        """Get recommendations with robust intent analysis"""
        # Get intent analysis with fallbacks
        intent_data = self.get_intent_analysis_robust(request)
        
        if intent_data:
            # Enhance request with intent data
            enhanced_request = self._enhance_request_with_intent(request, intent_data)
            # Get candidate content
            content_list = self.data_layer.get_candidate_content(request.user_id, request)
            return self._execute_engine_strategy(enhanced_request, content_list)
        else:
            # Fallback to basic recommendations without intent
            content_list = self.data_layer.get_candidate_content(request.user_id, request)
            return self._execute_engine_strategy(request, content_list)

# Global orchestrator instance
_orchestrator_instance = None

def get_unified_orchestrator() -> UnifiedRecommendationOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = UnifiedRecommendationOrchestrator()
    return _orchestrator_instance

def get_unified_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Main function to get unified recommendations"""
    try:
        # Create request object
        request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            user_interests=request_data.get('user_interests', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engine_preference=request_data.get('engine_preference'),
            diversity_weight=request_data.get('diversity_weight', 0.3),
            quality_threshold=request_data.get('quality_threshold', 6),
            include_global_content=request_data.get('include_global_content', True)
        )
        
        # Get orchestrator
        orchestrator = get_unified_orchestrator()
        
        # Get recommendations
        results = orchestrator.get_recommendations(request)
        
        # Convert to dictionary format for API response
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error getting unified recommendations: {e}")
        return []

if __name__ == "__main__":
    # Test the orchestrator
    test_request = UnifiedRecommendationRequest(
        user_id=1,
        title="React Learning Project",
        description="Building a modern web application with React",
        technologies="JavaScript, React, Node.js",
        user_interests="Frontend development, state management",
        max_recommendations=5
    )
    
    orchestrator = UnifiedRecommendationOrchestrator()
    results = orchestrator.get_recommendations(test_request)
    
    print(f"Generated {len(results)} recommendations:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Score: {result.score:.2f}")
        print(f"   Engine: {result.engine_used}")
        print(f"   Reason: {result.reason}")
        print(f"   Technologies: {', '.join(result.technologies[:3])}") 
