#!/usr/bin/env python3
"""
Unified Orchestrator Configuration System
Replaces ALL hardcoded values in unified_recommendation_orchestrator.py
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ScoringWeights:
    """Dynamic scoring weights for all recommendation calculations"""
    # User content relevance weights
    user_tech_weight: float = 0.5
    user_text_weight: float = 0.3
    user_quality_weight: float = 0.15
    user_boost: float = 0.05
    user_project_boost: float = 0.1
    
    # Project content relevance weights
    project_tech_weight: float = 0.6
    project_text_weight: float = 0.3
    project_quality_weight: float = 0.1
    project_context_boost: float = 0.05
    project_semantic_weight: float = 0.4
    project_analysis_weight: float = 0.2
    
    # Fast engine scoring weights
    fast_tech_weight: float = 0.5
    fast_similarity_weight: float = 0.4
    fast_quality_weight: float = 0.1
    fast_boost: float = 0.05
    fast_project_boost: float = 0.02
    fast_relevance_boost: float = 0.1
    fast_enhanced_weight: float = 0.4
    
    # Context engine scoring weights
    context_tech_weight: float = 0.35
    context_semantic_weight: float = 0.25
    context_content_type_weight: float = 0.15
    context_difficulty_weight: float = 0.10
    context_quality_weight: float = 0.05
    context_intent_weight: float = 0.10
    context_boost: float = 0.1
    context_relevance_boost: float = 0.15
    
    # Hybrid ensemble weights
    hybrid_fast_weight: float = 0.4
    hybrid_context_weight: float = 0.4
    hybrid_combined_weight: float = 0.2
    hybrid_rank_weight: float = 0.1

@dataclass
class Thresholds:
    """Dynamic thresholds for content filtering and scoring"""
    # Quality score thresholds - LOWERED to include more user content
    quality_exceptional: int = 8  # Lowered from 9 to 8
    quality_high: int = 7  # Lowered from 8 to 7
    quality_good: int = 6  # Lowered from 7 to 6
    quality_acceptable: int = 5  # Lowered from 6 to 5
    quality_minimum: int = 3  # Lowered from 5 to 3
    quality_user_content: int = 2  # Lowered from 3 to 2 - Include more user content
    
    # Overlap ratio thresholds
    overlap_perfect: float = 0.8
    overlap_strong: float = 0.6
    overlap_good: float = 0.4
    overlap_basic: float = 0.2
    
    # Score thresholds
    score_excellent: float = 0.85
    score_good: float = 0.70
    score_acceptable: float = 0.50
    score_minimum: float = 0.05
    score_medium: float = 0.15
    
    # Complexity thresholds
    complexity_simple: int = 2
    complexity_medium: int = 1
    complexity_high: int = 2

@dataclass
class ProcessingLimits:
    """Dynamic processing limits for performance tuning"""
    # Database query limits - INCREASED to allow more content
    db_query_limit_small: int = 500  # Increased from 100 to 500
    db_query_limit_medium: int = 1000  # Increased from 200 to 1000
    db_query_limit_large: int = 2000  # Increased from 500 to 2000
    
    # Content processing limits
    content_batch_size: int = 20  # Increased from 10 to 20
    max_recommendations: int = 30  # Increased from 20 to 30
    text_length_limit: int = 500  # Increased from 200 to 500
    title_length_limit: int = 200  # Increased from 100 to 200
    
    # Retry and timeout settings
    max_retries: int = 3
    retry_delay_base: int = 1
    retry_delay_multiplier: float = 2.0

@dataclass
class BoostFactors:
    """Dynamic boost factors for scoring adjustments"""
    # Technology match boosts
    tech_match_boost_per_match: float = 0.5
    tech_match_max_boost: float = 2.0
    
    # Partial and related match boosts
    partial_match_boost: float = 0.5
    related_match_boost: float = 0.3
    
    # Intent alignment boosts
    intent_strong_boost: float = 0.5
    intent_medium_boost: float = 0.3
    
    # Vector normalization
    vector_normalization_factor: float = 0.1

class UnifiedOrchestratorConfig:
    """Comprehensive configuration system for Unified Orchestrator"""
    
    def __init__(self):
        # Load from environment variables or use defaults
        self.scoring_weights = self._load_scoring_weights()
        self.thresholds = self._load_thresholds()
        self.processing_limits = self._load_processing_limits()
        self.boost_factors = self._load_boost_factors()
        
        # Core orchestrator settings
        self.max_recommendations = int(os.getenv('ORCHESTRATOR_MAX_RECOMMENDATIONS', 20))
        self.quality_threshold = int(os.getenv('ORCHESTRATOR_QUALITY_THRESHOLD', 5))
        self.min_score_threshold = int(os.getenv('ORCHESTRATOR_MIN_SCORE_THRESHOLD', 20))
        self.medium_score_threshold = int(os.getenv('ORCHESTRATOR_MEDIUM_SCORE_THRESHOLD', 15))
        self.diversity_weight = float(os.getenv('ORCHESTRATOR_DIVERSITY_WEIGHT', 0.3))
        self.complexity_threshold = int(os.getenv('ORCHESTRATOR_COMPLEXITY_THRESHOLD', 2))
        self.semantic_boost = float(os.getenv('ORCHESTRATOR_SEMANTIC_BOOST', 0.05))
        self.project_context_boost = float(os.getenv('ORCHESTRATOR_PROJECT_BOOST', 0.02))
        self.quality_boost = float(os.getenv('ORCHESTRATOR_QUALITY_BOOST', 0.1))
        
        # Technology overlap thresholds
        self.technology_overlap_thresholds = {
            'perfect': float(os.getenv('TECH_OVERLAP_PERFECT', 0.8)),
            'strong': float(os.getenv('TECH_OVERLAP_STRONG', 0.6)),
            'good': float(os.getenv('TECH_OVERLAP_GOOD', 0.4)),
            'basic': float(os.getenv('TECH_OVERLAP_BASIC', 0.2))
        }
        
        # Quality score thresholds
        self.quality_score_thresholds = {
            'exceptional': int(os.getenv('QUALITY_EXCEPTIONAL', 9)),
            'high': int(os.getenv('QUALITY_HIGH', 8)),
            'good': int(os.getenv('QUALITY_GOOD', 7)),
            'acceptable': int(os.getenv('QUALITY_ACCEPTABLE', 6)),
            'minimum': int(os.getenv('QUALITY_MINIMUM', 5))
        }
        
        # Ensemble weights
        self.ensemble_weights = {
            'fast_engine': float(os.getenv('ORCHESTRATOR_FAST_WEIGHT', 0.4)),
            'context_engine': float(os.getenv('ORCHESTRATOR_CONTEXT_WEIGHT', 0.4)),
            'combined': float(os.getenv('ORCHESTRATOR_COMBINED_WEIGHT', 0.2))
        }
        
        # Complexity limits
        self.complexity_limits = {
            'title_length': int(os.getenv('COMPLEXITY_TITLE_LENGTH', 50)),
            'description_length': int(os.getenv('COMPLEXITY_DESC_LENGTH', 100)),
            'tech_count': int(os.getenv('COMPLEXITY_TECH_COUNT', 3))
        }
    
    def _load_scoring_weights(self) -> ScoringWeights:
        """Load scoring weights from environment or defaults"""
        return ScoringWeights(
            user_tech_weight=float(os.getenv('WEIGHT_USER_TECH', '0.5')),
            user_text_weight=float(os.getenv('WEIGHT_USER_TEXT', '0.3')),
            user_quality_weight=float(os.getenv('WEIGHT_USER_QUALITY', '0.15')),
            user_boost=float(os.getenv('BOOST_USER', '0.05')),
            user_project_boost=float(os.getenv('BOOST_USER_PROJECT', '0.1')),
            
            project_tech_weight=float(os.getenv('WEIGHT_PROJECT_TECH', '0.6')),
            project_text_weight=float(os.getenv('WEIGHT_PROJECT_TEXT', '0.3')),
            project_quality_weight=float(os.getenv('WEIGHT_PROJECT_QUALITY', '0.1')),
            project_context_boost=float(os.getenv('BOOST_PROJECT_CONTEXT', '0.05')),
            project_semantic_weight=float(os.getenv('WEIGHT_PROJECT_SEMANTIC', '0.4')),
            project_analysis_weight=float(os.getenv('WEIGHT_PROJECT_ANALYSIS', '0.2')),
            
            fast_tech_weight=float(os.getenv('WEIGHT_FAST_TECH', '0.5')),
            fast_similarity_weight=float(os.getenv('WEIGHT_FAST_SIMILARITY', '0.4')),
            fast_quality_weight=float(os.getenv('WEIGHT_FAST_QUALITY', '0.1')),
            fast_boost=float(os.getenv('BOOST_FAST', '0.05')),
            fast_project_boost=float(os.getenv('BOOST_FAST_PROJECT', '0.02')),
            fast_relevance_boost=float(os.getenv('BOOST_FAST_RELEVANCE', '0.1')),
            fast_enhanced_weight=float(os.getenv('WEIGHT_FAST_ENHANCED', '0.4')),
            
            context_tech_weight=float(os.getenv('WEIGHT_CONTEXT_TECH', '0.35')),
            context_semantic_weight=float(os.getenv('WEIGHT_CONTEXT_SEMANTIC', '0.25')),
            context_content_type_weight=float(os.getenv('WEIGHT_CONTEXT_CONTENT_TYPE', '0.15')),
            context_difficulty_weight=float(os.getenv('WEIGHT_CONTEXT_DIFFICULTY', '0.10')),
            context_quality_weight=float(os.getenv('WEIGHT_CONTEXT_QUALITY', '0.05')),
            context_intent_weight=float(os.getenv('WEIGHT_CONTEXT_INTENT', '0.10')),
            context_boost=float(os.getenv('BOOST_CONTEXT', '0.1')),
            context_relevance_boost=float(os.getenv('BOOST_CONTEXT_RELEVANCE', '0.15')),
            
            hybrid_fast_weight=float(os.getenv('WEIGHT_HYBRID_FAST', '0.4')),
            hybrid_context_weight=float(os.getenv('WEIGHT_HYBRID_CONTEXT', '0.4')),
            hybrid_combined_weight=float(os.getenv('WEIGHT_HYBRID_COMBINED', '0.2')),
            hybrid_rank_weight=float(os.getenv('WEIGHT_HYBRID_RANK', '0.1'))
        )
    
    def _load_thresholds(self) -> Thresholds:
        """Load thresholds from environment or defaults"""
        return Thresholds(
            quality_exceptional=int(os.getenv('THRESHOLD_QUALITY_EXCEPTIONAL', '8')),  # Lowered default
            quality_high=int(os.getenv('THRESHOLD_QUALITY_HIGH', '7')),  # Lowered default
            quality_good=int(os.getenv('THRESHOLD_QUALITY_GOOD', '6')),  # Lowered default
            quality_acceptable=int(os.getenv('THRESHOLD_QUALITY_ACCEPTABLE', '5')),  # Lowered default
            quality_minimum=int(os.getenv('THRESHOLD_QUALITY_MINIMUM', '3')),  # Lowered default
            quality_user_content=int(os.getenv('THRESHOLD_QUALITY_USER_CONTENT', '2')),  # Lowered default - Include more user content
            
            overlap_perfect=float(os.getenv('THRESHOLD_OVERLAP_PERFECT', '0.8')),
            overlap_strong=float(os.getenv('THRESHOLD_OVERLAP_STRONG', '0.6')),
            overlap_good=float(os.getenv('THRESHOLD_OVERLAP_GOOD', '0.4')),
            overlap_basic=float(os.getenv('THRESHOLD_OVERLAP_BASIC', '0.2')),
            
            score_excellent=float(os.getenv('THRESHOLD_SCORE_EXCELLENT', '0.85')),
            score_good=float(os.getenv('THRESHOLD_SCORE_GOOD', '0.70')),
            score_acceptable=float(os.getenv('THRESHOLD_SCORE_ACCEPTABLE', '0.50')),
            score_minimum=float(os.getenv('THRESHOLD_SCORE_MINIMUM', '0.05')),
            score_medium=float(os.getenv('THRESHOLD_SCORE_MEDIUM', '0.15')),
            
            complexity_simple=int(os.getenv('THRESHOLD_COMPLEXITY_SIMPLE', '2')),
            complexity_medium=int(os.getenv('THRESHOLD_COMPLEXITY_MEDIUM', '1')),
            complexity_high=int(os.getenv('THRESHOLD_COMPLEXITY_HIGH', '2'))
        )
    
    def _load_processing_limits(self) -> ProcessingLimits:
        """Load processing limits from environment or defaults"""
        return ProcessingLimits(
            db_query_limit_small=int(os.getenv('LIMIT_DB_QUERY_SMALL', '500')),  # Increased default
            db_query_limit_medium=int(os.getenv('LIMIT_DB_QUERY_MEDIUM', '1000')),  # Increased default
            db_query_limit_large=int(os.getenv('LIMIT_DB_QUERY_LARGE', '2000')),  # Increased default
            
            content_batch_size=int(os.getenv('LIMIT_CONTENT_BATCH_SIZE', '20')),  # Increased default
            max_recommendations=int(os.getenv('LIMIT_MAX_RECOMMENDATIONS', '30')),  # Increased default
            text_length_limit=int(os.getenv('LIMIT_TEXT_LENGTH', '500')),  # Increased default
            title_length_limit=int(os.getenv('LIMIT_TITLE_LENGTH', '200')),  # Increased default
            
            max_retries=int(os.getenv('LIMIT_MAX_RETRIES', '3')),
            retry_delay_base=int(os.getenv('LIMIT_RETRY_DELAY_BASE', '1')),
            retry_delay_multiplier=float(os.getenv('LIMIT_RETRY_DELAY_MULTIPLIER', '2.0'))
        )
    
    def _load_boost_factors(self) -> BoostFactors:
        """Load boost factors from environment or defaults"""
        return BoostFactors(
            tech_match_boost_per_match=float(os.getenv('BOOST_TECH_MATCH_PER_MATCH', '0.5')),
            tech_match_max_boost=float(os.getenv('BOOST_TECH_MATCH_MAX', '2.0')),
            
            partial_match_boost=float(os.getenv('BOOST_PARTIAL_MATCH', '0.5')),
            related_match_boost=float(os.getenv('BOOST_RELATED_MATCH', '0.3')),
            
            intent_strong_boost=float(os.getenv('BOOST_INTENT_STRONG', '0.5')),
            intent_medium_boost=float(os.getenv('BOOST_INTENT_MEDIUM', '0.3')),
            
            vector_normalization_factor=float(os.getenv('BOOST_VECTOR_NORMALIZATION', '0.1'))
        )
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get complete configuration summary"""
        return {
            'core_settings': {
                'max_recommendations': self.max_recommendations,
                'quality_threshold': self.quality_threshold,
                'min_score_threshold': self.min_score_threshold,
                'medium_score_threshold': self.medium_score_threshold,
                'diversity_weight': self.diversity_weight,
                'complexity_threshold': self.complexity_threshold,
                'semantic_boost': self.semantic_boost,
                'project_context_boost': self.project_context_boost,
                'quality_boost': self.quality_boost
            },
            'scoring_weights': self.scoring_weights.__dict__,
            'thresholds': self.thresholds.__dict__,
            'processing_limits': self.processing_limits.__dict__,
            'boost_factors': self.boost_factors.__dict__,
            'technology_overlap_thresholds': self.technology_overlap_thresholds,
            'quality_score_thresholds': self.quality_score_thresholds,
            'ensemble_weights': self.ensemble_weights,
            'complexity_limits': self.complexity_limits
        }
    
    def update_config(self, **kwargs):
        """Update configuration dynamically"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                print(f"Updated config: {key} = {value}")
            elif hasattr(self.scoring_weights, key):
                setattr(self.scoring_weights, key, value)
                print(f"Updated scoring weight: {key} = {value}")
            elif hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)
                print(f"Updated threshold: {key} = {value}")
            elif hasattr(self.processing_limits, key):
                setattr(self.processing_limits, key, value)
                print(f"Updated processing limit: {key} = {value}")
            elif hasattr(self.boost_factors, key):
                setattr(self.boost_factors, key, value)
                print(f"Updated boost factor: {key} = {value}")

# Global configuration instance
unified_orchestrator_config = UnifiedOrchestratorConfig()

# Convenience functions for backward compatibility
def get_scoring_weight(weight_name: str, default_value: float = 0.0) -> float:
    """Get scoring weight by name with optional default value"""
    return getattr(unified_orchestrator_config.scoring_weights, weight_name, default_value)

def get_threshold(threshold_name: str) -> Any:
    """Get threshold by name"""
    return getattr(unified_orchestrator_config.thresholds, threshold_name, 0)

def get_processing_limit(limit_name: str) -> int:
    """Get processing limit by name"""
    return getattr(unified_orchestrator_config.processing_limits, limit_name, 100)

def get_boost_factor(boost_name: str) -> float:
    """Get boost factor by name"""
    return getattr(unified_orchestrator_config.boost_factors, boost_name, 0.0)
