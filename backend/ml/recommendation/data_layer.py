import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from core.logging_config import get_logger

logger = get_logger(__name__)

# Core imports with fallbacks
try:
    from models import db, SavedContent, ContentAnalysis, Project
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("ml_data_layer_models_missing")

try:
    from utils.redis_utils import redis_cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from universal_semantic_matcher import UniversalSemanticMatcher
    UNIVERSAL_MATCHER_AVAILABLE = True
except ImportError:
    UNIVERSAL_MATCHER_AVAILABLE = False

from .schemas import UnifiedRecommendationRequest

class UnifiedDataLayer:
    """Standardized data layer for all engines"""
    
    def __init__(self):
        self._embedding_model = None  # Private - use property to access
        self._embedding_model_initialized = False
        
        # Initialize universal semantic matcher if available
        self.universal_matcher = None
        if UNIVERSAL_MATCHER_AVAILABLE:
            try:
                self.universal_matcher = UniversalSemanticMatcher()
                if not (self.universal_matcher and hasattr(self.universal_matcher, 'embedding_model') and self.universal_matcher.embedding_model is not None):
                    logger.warning("ml_data_layer_matcher_content_none")
            except Exception as e:
                logger.warning("ml_data_layer_matcher_init_failed", error=str(e))
    
    @property
    def embedding_model(self):
        """Lazy-load embedding model - only loads when accessed"""
        if not self._embedding_model_initialized:
            self._init_embedding_model()
            self._embedding_model_initialized = True
        return self._embedding_model
    
    def _init_embedding_model(self):
        """Initialize embedding model with fallback for network issues - LAZY LOADED"""
        try:
            from utils.embedding_utils import get_embedding_model
            self._embedding_model = get_embedding_model()
            if self._embedding_model is not None:
                logger.info("ml_data_layer_embedding_model_loaded", method="global")
                return
            
            # Fallback local initialization
            import torch
            from sentence_transformers import SentenceTransformer
            try:
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("ml_data_layer_embedding_model_loaded", method="local")
            except Exception as network_error:
                logger.warning("ml_data_layer_embedding_model_network_error", error=str(network_error))
                self._embedding_model = None
                
        except Exception as e:
            logger.error("ml_data_layer_embedding_model_init_failed", error=str(e))
            self._embedding_model = None

    def get_db_session(self):
        """Get database session with retry logic and error handling"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if not MODELS_AVAILABLE: raise ImportError("Models not available")
                from models import db
                if db.session.is_active:
                    return db.session
                else:
                    return db.create_scoped_session()
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("ml_data_layer_db_connection_failed", attempt=attempt+1, error=str(e))
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("ml_data_layer_db_session_exhausted", error=str(e))
                    raise
        return None

    def normalize_content_data(self, content: Any, analysis: Optional[Any] = None) -> Dict[str, Any]:
        """Normalize content data to unified format"""
        try:
            technologies = []
            if analysis:
                if analysis.technology_tags:
                    technologies.extend([tech.strip() for tech in analysis.technology_tags.split(',') if tech.strip()])
                if analysis.analysis_data:
                    analysis_techs = analysis.analysis_data.get('technologies', [])
                    if isinstance(analysis_techs, list):
                        technologies.extend(analysis_techs)
                    elif isinstance(analysis_techs, str):
                        technologies.extend([tech.strip() for tech in analysis_techs.split(',') if tech.strip()])

            if content.tags:
                technologies.extend([tech.strip() for tech in content.tags.split(',') if tech.strip()])
            
            technologies = list(set([tech.lower().strip() for tech in technologies if tech.strip()]))
            
            key_concepts = []
            if analysis:
                if analysis.key_concepts:
                    key_concepts = [concept.strip() for concept in analysis.key_concepts.split(',') if concept.strip()]
                if analysis.analysis_data:
                    json_concepts = analysis.analysis_data.get('key_concepts', [])
                    if isinstance(json_concepts, list):
                        key_concepts.extend(json_concepts)
                    key_concepts = list(set(key_concepts))
            
            content_type = 'article'
            if analysis:
                content_type = analysis.analysis_data.get('content_type', analysis.content_type or 'article') if analysis.analysis_data else (analysis.content_type or 'article')
            
            difficulty = 'intermediate'
            if analysis:
                difficulty = analysis.analysis_data.get('difficulty', analysis.difficulty_level or 'intermediate') if analysis.analysis_data else (analysis.difficulty_level or 'intermediate')
            
            return {
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
        except Exception as e:
            logger.error("ml_data_layer_normalize_error", error=str(e))
            return {
                'id': getattr(content, 'id', None),
                'title': getattr(content, 'title', ''),
                'url': getattr(content, 'url', ''),
                'extracted_text': getattr(content, 'extracted_text', '') or '',
                'technologies': [],
                'key_concepts': [],
                'content_type': 'article',
                'difficulty': 'intermediate',
                'quality_score': getattr(content, 'quality_score', 6) or 6,
                'saved_at': getattr(content, 'saved_at', datetime.utcnow()),
                'tags': getattr(content, 'tags', '') or '',
                'analysis_data': {},
                'embedding': getattr(content, 'embedding', None),
                'relevance_score': 0
            }

    def get_candidate_content(self, user_id: int, request: UnifiedRecommendationRequest) -> List[Dict[str, Any]]:
        """Get candidate content in unified format"""
        try:
            from utils.database_utils import get_db_session, with_db_session
            
            @with_db_session
            def get_content(session):
                return self._get_content_from_db_with_session(user_id, request, session)
            
            return get_content()
        except Exception as e:
            logger.error("ml_data_layer_candidate_fetch_failed_outer", error=str(e))
            return []
    
    def _get_content_from_db_with_session(self, user_id: int, request: UnifiedRecommendationRequest, session) -> List[Dict[str, Any]]:
        """Get content from database using provided session - OPTIMIZED FOR PERFORMANCE"""
        try:
            from models import SavedContent, ContentAnalysis
            
            query = session.query(SavedContent, ContentAnalysis).outerjoin(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            ).filter(
                SavedContent.user_id == user_id,
                SavedContent.quality_score >= 1,
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                SavedContent.title.isnot(None),
                SavedContent.title != ''
            ).filter(
                ~SavedContent.title.like('%Test Bookmark%'),
                ~SavedContent.title.like('%test bookmark%'),
                ~SavedContent.title.like('%Dictionary%'),
                ~SavedContent.title.like('%dictionary%')
            )
            
            user_content = query.order_by(
                SavedContent.quality_score.desc(),
                SavedContent.saved_at.desc()
            ).all()
            
            content_list = [self.normalize_content_data(content, analysis) for content, analysis in user_content]
            logger.info("ml_data_layer_candidate_fetch_success", count=len(content_list), user_id=user_id)
            return content_list
            
        except Exception as e:
            logger.error("ml_data_layer_db_fetch_failed", user_id=user_id, error=str(e))
            return []

    def _encode_with_circuit_breaker(self, texts: List[str], **kwargs):
        """Helper to invoke embedding encoding wrapped in a circuit breaker"""
        import pybreaker
        if not hasattr(self.__class__, '_ml_breaker'):
            self.__class__._ml_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30)
            
        from utils.embedding_utils import embed_async
        @self.__class__._ml_breaker
        def _do_encode():
            return embed_async(texts)
            
        return _do_encode()

    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text"""
        if not self.embedding_model or not text:
            return None
        try:
            import pybreaker
            result = self._encode_with_circuit_breaker([text])
            return result[0]
        except pybreaker.CircuitBreakerError:
            logger.error("ml_circuit_breaker_open")
            return None
        except Exception as e:
            logger.error("ml_embedding_generation_failed", error=str(e))
            return None
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        emb1 = self.generate_embedding(text1)
        emb2 = self.generate_embedding(text2)
        if emb1 is None or emb2 is None: return 0.5
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def calculate_batch_similarities(self, request_text: str, content_texts: List[str]) -> List[float]:
        """Calculate semantic similarities for multiple content texts in batch"""
        try:
            if self.universal_matcher:
                try:
                    return [self.universal_matcher.calculate_semantic_similarity(request_text, ct) for ct in content_texts]
                except Exception as e:
                    logger.warning("ml_data_layer_universal_matcher_failed", error=str(e))
            
            if not self.embedding_model:
                return [0.5] * len(content_texts)
            
            all_texts = [request_text] + content_texts
            import pybreaker
            try:
                embeddings = self._encode_with_circuit_breaker(all_texts)
            except pybreaker.CircuitBreakerError:
                return [0.5] * len(content_texts)
            
            request_emb = np.array(embeddings[0])
            content_embs = np.array(embeddings[1:])
            
            if len(content_embs) > 0:
                request_norm = np.linalg.norm(request_emb)
                content_norms = np.linalg.norm(content_embs, axis=1)
                valid_norms = content_norms > 0
                similarities = np.zeros(len(content_embs))
                if request_norm > 0:
                    similarities[valid_norms] = np.dot(content_embs[valid_norms], request_emb) / (content_norms[valid_norms] * request_norm)
                return similarities.tolist()
            return []
        except Exception as e:
            logger.error("ml_batch_similarity_failed", error=str(e))
            return [0.5] * len(content_texts)
