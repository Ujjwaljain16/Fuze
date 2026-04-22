from typing import List, Dict, Any
import time
from .base import BaseEngine
from ..recommendation.schemas import UnifiedRecommendationResult, UnifiedRecommendationRequest
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

class KeywordEngine(BaseEngine):
    """Keyword-based engine using TF-IDF (formerly partially inside ContextAwareEngine)"""
    
    def __init__(self, data_layer: Any):
        super().__init__(data_layer, "KeywordEngine")
        self.ml_available = False
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self.TfidfVectorizer = TfidfVectorizer
            self.cosine_similarity = cosine_similarity
            self.ml_available = True
        except ImportError:
            logger.info("keyword_engine_ml_unavailable", detail="sklearn missing")

    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get keyword-based recommendations using TF-IDF"""
        start_time = time.time()
        try:
            if not self.ml_available or not content_list:
                self._update_performance(start_time, True)
                return []

            query_text = f"{request.title} {request.description} {request.technologies} {request.user_interests}"
            # Extract content text (limit length for performance)
            content_texts = [f"{c.get('title', '')} {c.get('extracted_text', '')[:500]}" for c in content_list]
            
            all_texts = [query_text] + content_texts
            vectorizer = self.TfidfVectorizer(stop_words='english', max_features=500)
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            query_vec = tfidf_matrix[0:1]
            doc_vecs = tfidf_matrix[1:]
            similarities = self.cosine_similarity(query_vec, doc_vecs)[0]
            
            results = []
            for i, similarity in enumerate(similarities):
                content = content_list[i]
                results.append(UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=float(similarity * 100),
                    reason="Relevant keywords found in the content.",
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 6),
                    engine_used=self.name,
                    confidence=float(similarity),
                    metadata={
                        'tfidf_similarity': float(similarity),
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                ))
            
            results.sort(key=lambda x: x.score, reverse=True)
            self._update_performance(start_time, True)
            logger.info("keyword_engine_complete", count=len(results[:request.max_recommendations]), duration_ms=(time.time()-start_time)*1000)
            return results[:request.max_recommendations]

        except Exception as e:
            logger.error("keyword_engine_error", error=str(e), user_id=request.user_id)
            self._update_performance(start_time, False)
            return []
