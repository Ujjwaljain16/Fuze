from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class UnifiedRecommendationRequest:
    """Standardized recommendation request format"""
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    user_interests: str = ""
    project_id: Optional[int] = None
    task_id: Optional[int] = None      # Current task context for better recommendations
    subtask_id: Optional[int] = None   # Current subtask context for better recommendations
    max_recommendations: int = 10
    engine_preference: Optional[str] = "context"  # Default to 'context' for better quality
    diversity_weight: float = 0.3
    quality_threshold: int = 6
    include_global_content: bool = True
    cache_duration: int = 1800  # 30 minutes
    intent_analysis: Optional[Dict[str, Any]] = None # Added for modular intent processing

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
    basic_summary: str = ""
    context_summary: str = ""
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
