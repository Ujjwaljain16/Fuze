from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..recommendation.schemas import UnifiedRecommendationRequest, UnifiedRecommendationResult, EnginePerformance
from datetime import datetime

class BaseEngine(ABC):
    """Abstract base class for all recommendation engines"""
    
    def __init__(self, data_layer: Any, name: str):
        self.data_layer = data_layer
        self.name = name
        self.performance = EnginePerformance(
            engine_name=self.name,
            response_time_ms=0.0,
            success_rate=1.0,
            cache_hit_rate=0.0,
            error_count=0,
            last_used=datetime.utcnow(),
            total_requests=0
        )

    @abstractmethod
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get recommendations from this engine"""
        pass

    def _update_performance(self, start_time: float, success: bool):
        """Update performance metrics"""
        import time
        response_time = (time.time() - start_time) * 1000
        self.performance.response_time_ms = response_time
        self.performance.total_requests += 1
        self.performance.last_used = datetime.utcnow()
        
        if not success:
            self.performance.error_count += 1
        
        if self.performance.total_requests > 0:
            self.performance.success_rate = (
                (self.performance.total_requests - self.performance.error_count) / 
                self.performance.total_requests
            )
