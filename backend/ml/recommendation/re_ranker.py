from typing import List, Dict, Any
from .schemas import UnifiedRecommendationResult, UnifiedRecommendationRequest
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

class ReRanker:
    """Handles blending, diversification, and splitting of recommendation results"""
    
    def __init__(self, diversity_weight: float = 0.3):
        self.diversity_weight = diversity_weight

    def blend_results(self, engine_results: Dict[str, List[UnifiedRecommendationResult]], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Blend results from multiple engines with weighting"""
        all_recs = []
        seen_urls = set()
        
        # Priority: context > semantic > keyword
        priority_order = ['ContextEngine', 'SemanticEngine', 'KeywordEngine']
        
        for engine_name in priority_order:
            results = engine_results.get(engine_name, [])
            for res in results:
                if res.url not in seen_urls:
                    all_recs.append(res)
                    seen_urls.add(res.url)
        
        # Sort by score descending
        all_recs.sort(key=lambda x: x.score, reverse=True)
        
        # Apply diversity if weight > 0
        if self.diversity_weight > 0:
            all_recs = self._apply_diversity(all_recs, request)
            
        logger.info("re_ranker_blending_complete", total_candidates=len(all_recs), user_id=request.user_id)
        return all_recs[:request.max_recommendations]

    def _apply_diversity(self, recommendations: List[UnifiedRecommendationResult], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Apply simple diversity filtering based on content_type and technologies"""
        if not recommendations: return []
        
        diverse_recs = []
        type_counts = {}
        tech_counts = {}
        
        # Very simple MMR-like diversification
        for rec in recommendations:
            ctype = rec.content_type
            main_tech = rec.technologies[0] if rec.technologies else 'unknown'
            
            # Penalize if we already have many of the same type/tech
            penalty = (type_counts.get(ctype, 0) * 5) + (tech_counts.get(main_tech, 0) * 3)
            rec.score -= (penalty * self.diversity_weight)
            
            type_counts[ctype] = type_counts.get(ctype, 0) + 1
            tech_counts[main_tech] = tech_counts.get(main_tech, 0) + 1
            diverse_recs.append(rec)
            
        diverse_recs.sort(key=lambda x: x.score, reverse=True)
        return diverse_recs

    def split_multi_topic_content(self, content_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split content covering multiple topics (e.g. LinkedIn posts)"""
        final_list = []
        for content in content_list:
            if self._should_split(content):
                new_splits = self._perform_split(content)
                logger.info("re_ranker_topic_split_triggered", content_id=content.get('id'), splits_count=len(new_splits))
                final_list.extend(new_splits)
            else:
                final_list.append(content)
        return final_list

    def _should_split(self, content: Dict) -> bool:
        return (content.get('content_type') == 'linkedin_post' and 
                len(content.get('technologies', [])) >= 3 and 
                len(content.get('extracted_text', '')) > 1000)

    def _perform_split(self, content: Dict) -> List[Dict]:
        """Perform tech-based splitting"""
        splits = []
        techs = content.get('technologies', [])
        # Group by first 2 techs or similar (simplified for extraction)
        for i, tech in enumerate(techs[:2]):
            split = content.copy()
            split['id'] = f"{content['id']}_split_{i}"
            split['title'] = f"{content['title']} ({tech.capitalize()})"
            split['technologies'] = [tech]
            split['is_split_content'] = True
            splits.append(split)
        return splits if splits else [content]
