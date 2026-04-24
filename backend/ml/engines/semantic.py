from typing import List, Dict, Any
import time
import numpy as np
from .base import BaseEngine
from ..recommendation.schemas import UnifiedRecommendationResult, UnifiedRecommendationRequest
from core.logging_config import get_logger

logger = get_logger(__name__)

class SemanticEngine(BaseEngine):
    """Semantic similarity engine (formerly FastSemanticEngine)"""
    
    def __init__(self, data_layer: Any):
        super().__init__(data_layer, "SemanticEngine")
    
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get fast semantic recommendations"""
        start_time = time.time()
        try:
            if not content_list:
                # In modular mode, candidates should usually be passed in, 
                # but we keep the fallback fetch if needed.
                content_list = self.data_layer.get_candidate_content(request.user_id, request)
            
            if not content_list: return []

            # Preparation
            request_text = f"{request.title} {request.description} {request.technologies}"
            content_texts = [f"{c.get('title', '')[:100]} {c.get('extracted_text', '')[:200]} {' '.join(c.get('technologies', [])[:5])}" for c in content_list]
            
            similarities = self.data_layer.calculate_batch_similarities(request_text, content_texts)
            
            recommendations_data = []
            request_techs = [t.strip().lower() for t in (request.technologies.split(',') if isinstance(request.technologies, str) else request.technologies) if t.strip()]
            
            for i, content in enumerate(content_list):
                similarity = similarities[i]
                content_techs = content.get('technologies', [])
                tech_overlap = self._calculate_technology_overlap(content_techs, request_techs)
                
                # Scoring: Tech(50%) + Semantic(40%) + Quality(10%) + Boosts
                final_score = (tech_overlap * 0.5) + (similarity * 0.4) + (content.get('quality_score', 6) / 10.0 * 0.1)
                final_score += 0.05 # User content boost
                
                recommendations_data.append({
                    'content': content,
                    'similarity': similarity,
                    'tech_overlap': tech_overlap,
                    'final_score': final_score
                })
            
            recommendations_data.sort(key=lambda x: x['final_score'], reverse=True)
            top_recs = recommendations_data[:request.max_recommendations]

            results = []
            for rec in top_recs:
                content = rec['content']
                results.append(UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=rec['final_score'] * 100,
                    reason=self._generate_fast_reason(content, rec['similarity'], rec['tech_overlap'], request.project_id is not None),
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
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                ))

            self._update_performance(start_time, True)
            logger.info("semantic_engine_complete", count=len(results), duration_ms=(time.time()-start_time)*1000)
            return results
        except Exception as e:
            logger.error("semantic_engine_error", error=str(e), user_id=request.user_id)
            self._update_performance(start_time, False)
            return []

    def _calculate_technology_overlap(self, content_techs: List[str], request_techs: List[str]) -> float:
        """Calculate technology overlap score"""
        if not content_techs or not request_techs: return 0.0
        content_set = set([t.lower().strip() for t in content_techs if t.strip()])
        request_set = set([t.lower().strip() for t in request_techs if t.strip()])
        if not request_set: return 0.0
        matches = len(content_set.intersection(request_set))
        return min(1.0, matches / len(request_set))

    def _generate_fast_reason(self, content: Dict, similarity: float, tech_overlap: float, has_project: bool) -> str:
        reasons = []
        if similarity > 0.6: reasons.append("Strong semantic match")
        if tech_overlap > 0.5: reasons.append("Good technology overlap")
        if content.get('quality_score', 0) >= 8: reasons.append("High quality content")
        if has_project: reasons.append("Project relevant")
        return ". ".join(reasons) if reasons else "Relevant learning content"
