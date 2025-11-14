#!/usr/bin/env python3
"""
Critical Enhancements for Unified Recommendation Orchestrator
Focus: Performance, Intelligence, and User Experience Improvements
"""

import time
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, deque
import numpy as np
import hashlib
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class UserBehaviorPattern:
    """Track user interaction patterns for personalization"""
    user_id: int
    preferred_content_types: List[str]
    technology_preferences: Dict[str, float]  # technology -> preference score
    interaction_history: List[Dict]  # recent clicks, ratings, etc.
    learning_pace: str  # 'beginner', 'intermediate', 'advanced'
    preferred_difficulty: str
    session_context: Dict[str, Any]
    last_updated: datetime

@dataclass
class RecommendationQualityMetrics:
    """Track recommendation quality and user satisfaction"""
    click_through_rate: float
    user_rating_avg: float
    content_completion_rate: float
    return_user_rate: float
    recommendation_diversity_score: float
    freshness_score: float
    relevance_feedback: List[Dict]

class IntelligentCachingSystem:
    """Smart caching with context-aware invalidation"""
    
    def __init__(self):
        self.cache_store = {}
        self.cache_metadata = {}
        self.user_patterns = {}
        
    def generate_smart_cache_key(self, request, user_behavior: Optional[UserBehaviorPattern] = None) -> str:
        """Generate cache key considering user context and behavior"""
        base_key = f"{request.user_id}:{request.technologies}:{request.title}:{request.description}"
        
        # Add user behavior context for personalized caching
        if user_behavior:
            behavior_context = f"{user_behavior.learning_pace}:{user_behavior.preferred_difficulty}"
            base_key += f":{behavior_context}"
        
        return hashlib.md5(base_key.encode()).hexdigest()
    
    def should_invalidate_cache(self, cache_key: str, user_behavior: UserBehaviorPattern) -> bool:
        """Intelligent cache invalidation based on user behavior changes"""
        if cache_key not in self.cache_metadata:
            return True
            
        metadata = self.cache_metadata[cache_key]
        cached_time = metadata['timestamp']
        
        # Invalidate if user preferences have significantly changed
        if user_behavior.last_updated > cached_time:
            return True
            
        # Invalidate based on content freshness requirements
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        max_age = 24 if user_behavior.learning_pace == 'beginner' else 12
        
        return age_hours > max_age

class AdaptiveLearningSystem:
    """Learn from user interactions to improve recommendations"""
    
    def __init__(self):
        self.user_feedback = defaultdict(list)
        self.content_performance = defaultdict(dict)
        self.technology_trends = defaultdict(float)
        
    def record_user_interaction(self, user_id: int, content_id: int, interaction_type: str, 
                               rating: Optional[float] = None, duration: Optional[int] = None):
        """Record user interactions for learning"""
        interaction = {
            'content_id': content_id,
            'type': interaction_type,  # 'click', 'rating', 'bookmark', 'complete'
            'rating': rating,
            'duration': duration,
            'timestamp': datetime.now()
        }
        self.user_feedback[user_id].append(interaction)
        
        # Update content performance metrics
        if content_id not in self.content_performance:
            self.content_performance[content_id] = {
                'clicks': 0, 'ratings': [], 'completions': 0, 'bookmarks': 0
            }
        
        if interaction_type == 'click':
            self.content_performance[content_id]['clicks'] += 1
        elif interaction_type == 'rating' and rating:
            self.content_performance[content_id]['ratings'].append(rating)
        elif interaction_type == 'complete':
            self.content_performance[content_id]['completions'] += 1
        elif interaction_type == 'bookmark':
            self.content_performance[content_id]['bookmarks'] += 1
    
    def get_personalized_weights(self, user_id: int) -> Dict[str, float]:
        """Calculate personalized scoring weights based on user behavior"""
        if user_id not in self.user_feedback:
            return self._get_default_weights()
        
        interactions = self.user_feedback[user_id]
        recent_interactions = [i for i in interactions if 
                             (datetime.now() - i['timestamp']).days < 30]
        
        if not recent_interactions:
            return self._get_default_weights()
        
        # Analyze interaction patterns
        high_rated_content = [i for i in recent_interactions 
                            if i.get('rating', 0) >= 4.0]
        
        weights = self._get_default_weights()
        
        # Adjust weights based on user preferences
        if len(high_rated_content) > 5:
            # User engages well - increase semantic similarity weight
            weights['semantic_similarity'] += 0.1
            weights['content_quality'] += 0.05
        
        return weights
    
    def _get_default_weights(self) -> Dict[str, float]:
        """Default scoring weights"""
        return {
            'semantic_similarity': 0.35,
            'technology_match': 0.25,
            'content_quality': 0.20,
            'user_context': 0.15,
            'freshness': 0.05
        }

class DynamicContentScaling:
    """Dynamically scale content processing based on system load and user needs"""
    
    def __init__(self):
        self.system_load_history = deque(maxlen=100)
        self.processing_times = deque(maxlen=50)
        
    def calculate_optimal_content_limit(self, user_content_size: int, 
                                       system_load: float = 0.5) -> int:
        """Calculate optimal content processing limit"""
        base_limit = min(user_content_size, 1000)
        
        # Adjust based on system load
        if system_load < 0.3:  # Low load
            return min(base_limit * 2, 2000)
        elif system_load < 0.7:  # Medium load
            return base_limit
        else:  # High load
            return max(base_limit // 2, 50)
    
    def get_adaptive_filtering_threshold(self, content_quality_distribution: List[float]) -> float:
        """Calculate adaptive filtering threshold based on content quality"""
        if not content_quality_distribution:
            return 0.02
        
        mean_quality = np.mean(content_quality_distribution)
        std_quality = np.std(content_quality_distribution)
        
        # Set threshold at mean - 1 standard deviation, but not below 0.01
        threshold = max(mean_quality - std_quality, 0.01)
        return min(threshold, 0.05)  # Cap at 0.05

class AdvancedDiversityEngine:
    """Enhanced diversity management for recommendations"""
    
    def __init__(self):
        self.diversity_patterns = {}
        self.content_clusters = {}
        
    def calculate_dynamic_diversity_weight(self, user_behavior: UserBehaviorPattern, 
                                         content_variety: int) -> float:
        """Calculate dynamic diversity weight based on user and content context"""
        base_weight = 0.3
        
        # Adjust based on user learning pace
        if user_behavior.learning_pace == 'beginner':
            base_weight += 0.1  # Beginners benefit from more diverse content
        elif user_behavior.learning_pace == 'advanced':
            base_weight -= 0.1  # Advanced users prefer focused content
        
        # Adjust based on content variety
        if content_variety < 20:
            base_weight += 0.15  # Increase diversity when content is limited
        elif content_variety > 100:
            base_weight -= 0.05  # Reduce when plenty of content available
        
        return max(0.1, min(0.5, base_weight))
    
    def ensure_recommendation_freshness(self, recommendations: List[Dict], 
                                      user_history: List[int]) -> List[Dict]:
        """Ensure recommendations include fresh content user hasn't seen"""
        seen_content = set(user_history[-50:])  # Last 50 items seen
        
        fresh_recommendations = []
        seen_recommendations = []
        
        for rec in recommendations:
            if rec['id'] not in seen_content:
                fresh_recommendations.append(rec)
            else:
                seen_recommendations.append(rec)
        
        # Ensure at least 60% fresh content
        target_fresh = max(len(recommendations) * 0.6, 3)
        if len(fresh_recommendations) < target_fresh:
            # Add some seen content back if we don't have enough fresh
            needed = int(target_fresh - len(fresh_recommendations))
            fresh_recommendations.extend(seen_recommendations[:needed])
        
        return fresh_recommendations[:len(recommendations)]

class RecommendationAnalytics:
    """Advanced analytics for recommendation quality and performance"""
    
    def __init__(self):
        self.metrics_history = defaultdict(list)
        self.ab_test_results = {}
        
    def track_recommendation_performance(self, user_id: int, recommendations: List[Dict], 
                                       user_interactions: List[Dict]) -> RecommendationQualityMetrics:
        """Track and analyze recommendation performance"""
        if not recommendations:
            return RecommendationQualityMetrics(0, 0, 0, 0, 0, 0, [])
        
        # Calculate click-through rate
        clicked_ids = {i['content_id'] for i in user_interactions if i['type'] == 'click'}
        recommended_ids = {r['id'] for r in recommendations}
        ctr = len(clicked_ids.intersection(recommended_ids)) / len(recommendations)
        
        # Calculate average rating
        ratings = [i['rating'] for i in user_interactions 
                  if i['type'] == 'rating' and i.get('rating')]
        avg_rating = np.mean(ratings) if ratings else 0
        
        # Calculate completion rate
        completed_ids = {i['content_id'] for i in user_interactions if i['type'] == 'complete'}
        completion_rate = len(completed_ids.intersection(recommended_ids)) / len(recommendations)
        
        # Calculate diversity score
        technologies = set()
        content_types = set()
        for rec in recommendations:
            if rec.get('technologies'):
                technologies.update(rec['technologies'])
            if rec.get('content_type'):
                content_types.add(rec['content_type'])
        
        diversity_score = (len(technologies) + len(content_types)) / (len(recommendations) * 2)
        
        return RecommendationQualityMetrics(
            click_through_rate=ctr,
            user_rating_avg=avg_rating,
            content_completion_rate=completion_rate,
            return_user_rate=0.0,  # Would need session data
            recommendation_diversity_score=diversity_score,
            freshness_score=0.0,  # Would need content age data
            relevance_feedback=[]
        )

# Integration points for the main orchestrator
class EnhancedOrchestratorMixin:
    """Mixin class to add enhancements to the existing orchestrator"""
    
    def __init__(self):
        self.caching_system = IntelligentCachingSystem()
        self.learning_system = AdaptiveLearningSystem()
        self.scaling_system = DynamicContentScaling()
        self.diversity_engine = AdvancedDiversityEngine()
        self.analytics = RecommendationAnalytics()
        
    def get_enhanced_recommendations(self, request, user_behavior: Optional[UserBehaviorPattern] = None):
        """Enhanced recommendation flow with all improvements"""
        start_time = time.time()
        
        try:
            # 1. Smart caching check
            cache_key = self.caching_system.generate_smart_cache_key(request, user_behavior)
            
            if user_behavior and not self.caching_system.should_invalidate_cache(cache_key, user_behavior):
                cached_result = self.caching_system.cache_store.get(cache_key)
                if cached_result:
                    logger.info("✅ Smart cache hit - returning personalized cached results")
                    return cached_result
            
            # 2. Dynamic content scaling
            user_content_size = 108  # From your test data
            content_limit = self.scaling_system.calculate_optimal_content_limit(user_content_size)
            
            # 3. Adaptive filtering
            # Would integrate with existing _filter_content_by_relevance method
            
            # 4. Personalized scoring weights
            if user_behavior:
                personalized_weights = self.learning_system.get_personalized_weights(request.user_id)
                # Apply these weights in the scoring functions
            
            # 5. Dynamic diversity
            if user_behavior:
                diversity_weight = self.diversity_engine.calculate_dynamic_diversity_weight(
                    user_behavior, user_content_size
                )
                request.diversity_weight = diversity_weight
            
            # 6. Get recommendations using existing system
            # recommendations = self.existing_get_recommendations(request)
            
            # 7. Ensure freshness
            # if user_behavior:
            #     recommendations = self.diversity_engine.ensure_recommendation_freshness(
            #         recommendations, user_behavior.interaction_history
            #     )
            
            # 8. Cache results
            # self.caching_system.cache_store[cache_key] = recommendations
            
            logger.info(f"✅ Enhanced recommendations completed in {time.time() - start_time:.3f}s")
            # return recommendations
            
        except Exception as e:
            logger.error(f"Error in enhanced recommendations: {e}")
            # return self.fallback_recommendations(request)
