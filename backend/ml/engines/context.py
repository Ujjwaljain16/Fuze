from typing import List, Dict, Any
import time
import numpy as np
from .base import BaseEngine
from ..recommendation.schemas import UnifiedRecommendationResult, UnifiedRecommendationRequest
from core.logging_config import get_logger

logger = get_logger(__name__)

class ContextEngine(BaseEngine):
    """Context-aware recommendation engine (formerly ContextAwareEngine)"""
    
    def __init__(self, data_layer: Any):
        super().__init__(data_layer, "ContextEngine")
    
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get context-aware recommendations"""
        start_time = time.time()
        try:
            if not content_list:
                content_list = self.data_layer.get_candidate_content(request.user_id, request)
            if not content_list: return []

            # Extract context
            context = self._extract_context(request)
            
            # Precompute semantic scores using DB embeddings
            semantic_scores = {}
            query_text = f"{context['title']} {context['description']} {' '.join(context.get('technologies', []))}"
            query_embedding = self.data_layer.generate_embedding(query_text)
            
            if query_embedding is not None:
                for content in content_list:
                    c_emb = content.get('embedding')
                    if c_emb is not None and len(c_emb) > 0:
                        sim = float(np.dot(query_embedding, c_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(c_emb)))
                        semantic_scores[content['id']] = sim
                    else:
                        semantic_scores[content['id']] = 0.5
            
            recommendations = []
            for content in content_list:
                sem_sim = semantic_scores.get(content['id'], 0.5)
                
                # Component scoring
                comp = self._calculate_score_components(content, context, sem_sim)
                
                # Weighted final score
                final_score = (
                    comp['semantic'] * 0.55 +
                    comp['technology'] * 0.20 +
                    comp['content_type'] * 0.08 +
                    comp['quality'] * 0.01 +
                    comp.get('intent_alignment', 0.5) * 0.16
                )
                
                # DIMINISHING RETURNS SOFT CAP
                if final_score > 0.8:
                    final_score = 0.8 + (final_score - 0.8) * 0.15
                
                final_score = min(final_score, 1.0)

                results = UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=round(final_score * 100, 1),
                    reason=self._generate_detailed_reason(content, context, comp),
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 6),
                    engine_used=self.name,
                    confidence=comp['semantic'],
                    metadata={
                        'score_components': comp,
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                )
                recommendations.append(results)

            recommendations.sort(key=lambda x: x.score, reverse=True)
            self._update_performance(start_time, True)
            logger.info("context_engine_complete", count=len(recommendations[:request.max_recommendations]), duration_ms=(time.time()-start_time)*1000)
            return recommendations[:request.max_recommendations]

        except Exception as e:
            logger.error("context_engine_error", error=str(e), user_id=request.user_id)
            self._update_performance(start_time, False)
            return []

    def _extract_context(self, request: UnifiedRecommendationRequest) -> Dict[str, Any]:
        intent = request.intent_analysis or {}
        techs = [t.strip() for t in (request.technologies.split(',') if isinstance(request.technologies, str) else request.technologies) if t.strip()]
        
        return {
            'technologies': list(set(techs + intent.get('specific_technologies', []))),
            'content_type': intent.get('time_constraint', 'general'),
            'difficulty': intent.get('learning_stage', 'intermediate'),
            'title': request.title,
            'description': request.description,
            'intent_goal': intent.get('primary_goal', 'learn'),
            'focus_areas': intent.get('focus_areas', [])
        }

    def _calculate_score_components(self, content: Dict, context: Dict, sem_sim: float) -> Dict[str, float]:
        content_techs = [t.lower() for t in content.get('technologies', [])]
        context_techs = [t.lower() for t in context.get('technologies', [])]
        
        tech_overlap = 0.0
        if context_techs:
            matches = set(content_techs).intersection(set(context_techs))
            tech_overlap = len(matches) / len(context_techs)

        # Intent alignment
        intent_alignment = 0.5
        if context.get('intent_goal') == 'learn' and content.get('content_type') in ['tutorial', 'documentation']:
            intent_alignment = 1.0

        return {
            'semantic': sem_sim,
            'technology': tech_overlap,
            'content_type': 1.0 if content.get('content_type') == context.get('content_type') else 0.5,
            'quality': content.get('quality_score', 6) / 10.0,
            'intent_alignment': intent_alignment
        }

    def _generate_detailed_reason(self, content: Dict, context: Dict, comp: Dict) -> str:
        reasons = []
        if comp['semantic'] > 0.7: reasons.append("Strong conceptual relevance")
        if comp['technology'] > 0.5: reasons.append("Excellent technology match")
        if content.get('is_user_content'): reasons.append("From your saved bookmarks")
        return " ".join(reasons) if reasons else "Matches your current context."
