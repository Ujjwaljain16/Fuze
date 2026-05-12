import time
import hashlib
from typing import List, Dict, Any
from dataclasses import asdict

from .recommendation.schemas import UnifiedRecommendationRequest, UnifiedRecommendationResult
from .recommendation.data_layer import UnifiedDataLayer
from .recommendation.re_ranker import ReRanker
from .engines.semantic import SemanticEngine
from .engines.keyword import KeywordEngine
from .engines.context import ContextEngine

from core.logging_config import get_logger

logger = get_logger(__name__)

try:
    from utils.redis_utils import redis_cache
except ImportError:
    redis_cache = None

try:
    from intent_analysis_engine import analyze_user_intent, get_fallback_intent
except ImportError:
    analyze_user_intent = None
    get_fallback_intent = None

class Orchestrator:
    """Strategy-based orchestrator for modular recommendation engines"""
    
    def __init__(self):
        self.data_layer = UnifiedDataLayer()
        self.re_ranker = ReRanker()
        
        # Initialize engines
        self.engines = {
            'SemanticEngine': SemanticEngine(self.data_layer),
            'KeywordEngine': KeywordEngine(self.data_layer),
            'ContextEngine': ContextEngine(self.data_layer)
        }
        
        logger.info("ml_orchestrator_initialized")

    def get_recommendations(self, request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Main orchestrated recommendation pipeline"""
        start_time = time.time()
        
        try:
            # 1. Cache Check
            cache_key = self._generate_cache_key(request)
            if redis_cache:
                cached_data = redis_cache.get_cache(cache_key)
                if cached_data:
                    logger.info("recommendation_cache_hit", cache_key=cache_key)
                    return [UnifiedRecommendationResult(**rec_data) for rec_data in cached_data]

            # 2. Intent Analysis
            intent = self._get_intent(request)
            request.intent_analysis = intent
            
            # 3. Candidate Fetching & Topic Splitting
            candidates = self.data_layer.get_candidate_content(request.user_id, request)
            if not candidates:
                return []
            
            # Split multi-topic content before engine processing
            candidates = self.re_ranker.split_multi_topic_content(candidates)

            # 4. Engine Strategy Execution
            engine_results = {}
            # Decide which engines to run based on preference/intent
            selected_engines = self._select_engines(request)
            
            for eng_name in selected_engines:
                if eng_name in self.engines:
                    engine_results[eng_name] = self.engines[eng_name].get_recommendations(candidates, request)

            # 5. Re-Ranking & Blending
            final_recommendations = self.re_ranker.blend_results(engine_results, request)
            
            # 6. Cache Results
            if redis_cache and final_recommendations:
                cache_data = [asdict(res) for res in final_recommendations]
                redis_cache.set_cache(cache_key, cache_data, request.cache_duration)
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info("recommendations_generated", duration_ms=duration_ms, user_id=request.user_id)
            return final_recommendations

        except Exception as e:
            logger.error("ml_orchestrator_error", error=str(e), user_id=request.user_id)
            return []

    def _get_intent(self, request: UnifiedRecommendationRequest) -> Dict[str, Any]:
        """Layered intent analysis"""
        user_input = f"{request.title} {request.description} {request.technologies}"
        if analyze_user_intent:
            try:
                intent_obj = analyze_user_intent(user_input, request.project_id)
                return intent_obj.__dict__ if hasattr(intent_obj, '__dict__') else intent_obj
            except Exception as e:
                logger.warning("ai_intent_analysis_failed", error=str(e))
        
        if get_fallback_intent:
            return get_fallback_intent(user_input, request.project_id).__dict__
        
        return {}

    def _select_engines(self, request: UnifiedRecommendationRequest) -> List[str]:
        """Simple strategy selection"""
        if request.engine_preference == 'fast':
            return ['SemanticEngine', 'KeywordEngine']
        # Default to all for standard context-aware quality
        return ['ContextEngine', 'SemanticEngine', 'KeywordEngine']

    def _generate_cache_key(self, request: UnifiedRecommendationRequest) -> str:
        data_str = f"{request.user_id}:{request.title}:{request.technologies}:{request.engine_preference}"
        return f"modular_recs:{hashlib.md5(data_str.encode()).hexdigest()}"

    def get_performance_metrics(self) -> Dict[str, Any]:
        return {
            name: eng.performance.__dict__ for name, eng in self.engines.items()
        }

# Global Instance Interface
_orchestrator = None

def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
