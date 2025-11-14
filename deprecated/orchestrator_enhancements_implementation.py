#!/usr/bin/env python3
"""
Orchestrator Enhancements Implementation
- System Load Monitoring (for performance optimization, NOT content limiting)
- User Behavior Tracking (for learning and analytics)
- Adaptive Learning System (for personalization)

CRITICAL: ALL user content is ALWAYS processed - no limits applied!
"""

import time
import psutil
import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import threading
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class SystemLoadMetrics:
    """System performance metrics for optimization (NOT limiting content)"""
    cpu_percent: float
    memory_percent: float
    disk_io_percent: float
    active_requests: int
    avg_response_time_ms: float
    recommendation_queue_size: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class UserBehaviorMetrics:
    """User interaction metrics for learning and personalization"""
    user_id: int
    clicks_count: int = 0
    total_time_spent_seconds: float = 0
    ratings_given: int = 0
    bookmarks_added: int = 0
    avg_rating: float = 0.0
    preferred_content_types: List[str] = field(default_factory=list)
    preferred_technologies: Dict[str, float] = field(default_factory=dict)
    session_count: int = 0
    last_interaction: datetime = field(default_factory=datetime.now)

@dataclass
class RecommendationInteraction:
    """Track user interactions with recommendations"""
    user_id: int
    content_id: int
    recommendation_id: str
    interaction_type: str  # 'click', 'rating', 'bookmark', 'view', 'dismiss'
    interaction_value: Optional[float]  # rating value, time spent, etc.
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class SystemLoadMonitor:
    """Monitor system performance for optimization (NOT for limiting content processing)"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=100)  # Keep last 100 measurements
        self.active_requests = 0
        self.response_times = deque(maxlen=50)  # Last 50 response times
        self.lock = threading.Lock()
        
        logger.info("✅ SystemLoadMonitor initialized - monitors performance for optimization")
    
    def start_request(self) -> str:
        """Mark start of a recommendation request"""
        with self.lock:
            self.active_requests += 1
            request_id = f"req_{int(time.time() * 1000)}_{self.active_requests}"
            return request_id
    
    def end_request(self, request_id: str, response_time_ms: float):
        """Mark end of a recommendation request"""
        with self.lock:
            self.active_requests = max(0, self.active_requests - 1)
            self.response_times.append(response_time_ms)
    
    def get_current_metrics(self) -> SystemLoadMetrics:
        """Get current system performance metrics"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            
            # Calculate average response time
            avg_response_time = np.mean(list(self.response_times)) if self.response_times else 0
            
            metrics = SystemLoadMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_io_percent=min(100, (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024 * 100)),  # Simplified
                active_requests=self.active_requests,
                avg_response_time_ms=avg_response_time,
                recommendation_queue_size=0  # Placeholder for future queue implementation
            )
            
            # Store in history
            self.metrics_history.append(metrics)
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Error getting system metrics: {e}")
            return SystemLoadMetrics(
                cpu_percent=0, memory_percent=0, disk_io_percent=0,
                active_requests=self.active_requests, avg_response_time_ms=0,
                recommendation_queue_size=0
            )
    
    def get_optimization_suggestions(self) -> Dict[str, Any]:
        """Get suggestions for performance optimization (NOT content limiting)"""
        current_metrics = self.get_current_metrics()
        
        suggestions = {
            'enable_caching': False,
            'use_async_processing': False,
            'optimize_database_queries': False,
            'parallel_processing': False,
            'resource_status': 'optimal'
        }
        
        # HIGH CPU - suggest async processing and caching
        if current_metrics.cpu_percent > 80:
            suggestions['enable_caching'] = True
            suggestions['use_async_processing'] = True
            suggestions['resource_status'] = 'high_cpu'
        
        # HIGH MEMORY - suggest database query optimization
        if current_metrics.memory_percent > 85:
            suggestions['optimize_database_queries'] = True
            suggestions['resource_status'] = 'high_memory'
        
        # SLOW RESPONSE TIMES - suggest parallel processing
        if current_metrics.avg_response_time_ms > 5000:  # 5 seconds
            suggestions['parallel_processing'] = True
            suggestions['resource_status'] = 'slow_response'
        
        # MULTIPLE REQUESTS - suggest all optimizations
        if current_metrics.active_requests > 3:
            suggestions.update({
                'enable_caching': True,
                'use_async_processing': True,
                'parallel_processing': True,
                'resource_status': 'high_load'
            })
        
        return suggestions
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights for analytics"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        recent_metrics = list(self.metrics_history)[-10:]  # Last 10 measurements
        
        return {
            'avg_cpu': np.mean([m.cpu_percent for m in recent_metrics]),
            'avg_memory': np.mean([m.memory_percent for m in recent_metrics]),
            'avg_response_time': np.mean([m.avg_response_time_ms for m in recent_metrics]),
            'peak_active_requests': max([m.active_requests for m in recent_metrics]),
            'status': 'optimal' if np.mean([m.cpu_percent for m in recent_metrics]) < 60 else 'high_load',
            'measurements_count': len(recent_metrics)
        }

class UserBehaviorTracker:
    """Track user interactions for learning and personalization"""
    
    def __init__(self):
        self.user_metrics = defaultdict(lambda: UserBehaviorMetrics(user_id=0))
        self.interactions = defaultdict(list)  # user_id -> List[RecommendationInteraction]
        self.session_data = defaultdict(dict)  # session_id -> session data
        self.lock = threading.Lock()
        
        logger.info("✅ UserBehaviorTracker initialized - tracking for learning and personalization")
    
    def record_interaction(self, user_id: int, content_id: int, interaction_type: str, 
                          interaction_value: Optional[float] = None, session_id: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record user interaction with content"""
        try:
            with self.lock:
                # Create interaction record
                interaction = RecommendationInteraction(
                    user_id=user_id,
                    content_id=content_id,
                    recommendation_id=f"rec_{user_id}_{content_id}_{int(time.time())}",
                    interaction_type=interaction_type,
                    interaction_value=interaction_value,
                    session_id=session_id,
                    metadata=metadata or {}
                )
                
                # Store interaction
                self.interactions[user_id].append(interaction)
                
                # Update user metrics
                self._update_user_metrics(user_id, interaction)
                
                # Keep only last 1000 interactions per user
                if len(self.interactions[user_id]) > 1000:
                    self.interactions[user_id] = self.interactions[user_id][-1000:]
                
                logger.debug(f"Recorded {interaction_type} interaction for user {user_id} on content {content_id}")
                return interaction.recommendation_id
                
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
            return ""
    
    def _update_user_metrics(self, user_id: int, interaction: RecommendationInteraction):
        """Update user behavior metrics based on interaction"""
        metrics = self.user_metrics[user_id]
        metrics.user_id = user_id
        metrics.last_interaction = interaction.timestamp
        
        if interaction.interaction_type == 'click':
            metrics.clicks_count += 1
        elif interaction.interaction_type == 'rating' and interaction.interaction_value:
            metrics.ratings_given += 1
            # Update average rating
            total_rating = metrics.avg_rating * (metrics.ratings_given - 1) + interaction.interaction_value
            metrics.avg_rating = total_rating / metrics.ratings_given
        elif interaction.interaction_type == 'bookmark':
            metrics.bookmarks_added += 1
        elif interaction.interaction_type == 'view' and interaction.interaction_value:
            metrics.total_time_spent_seconds += interaction.interaction_value
        
        # Update preferred content types and technologies from metadata
        if 'content_type' in interaction.metadata:
            content_type = interaction.metadata['content_type']
            if content_type not in metrics.preferred_content_types:
                metrics.preferred_content_types.append(content_type)
        
        if 'technologies' in interaction.metadata:
            for tech in interaction.metadata['technologies']:
                if tech in metrics.preferred_technologies:
                    metrics.preferred_technologies[tech] += 0.1
                else:
                    metrics.preferred_technologies[tech] = 1.0
    
    def get_user_behavior_metrics(self, user_id: int) -> UserBehaviorMetrics:
        """Get comprehensive behavior metrics for a user"""
        return self.user_metrics[user_id]
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences for personalization"""
        metrics = self.user_metrics[user_id]
        recent_interactions = self.interactions[user_id][-50:]  # Last 50 interactions
        
        # Analyze recent interaction patterns
        interaction_types = defaultdict(int)
        recent_technologies = defaultdict(float)
        recent_content_types = defaultdict(int)
        
        for interaction in recent_interactions:
            interaction_types[interaction.interaction_type] += 1
            if 'technologies' in interaction.metadata:
                for tech in interaction.metadata['technologies']:
                    recent_technologies[tech] += 1.0
            if 'content_type' in interaction.metadata:
                recent_content_types[interaction.metadata['content_type']] += 1
        
        return {
            'user_id': user_id,
            'engagement_level': min(100, metrics.clicks_count + metrics.ratings_given * 5 + metrics.bookmarks_added * 3),
            'preferred_technologies': dict(sorted(recent_technologies.items(), key=lambda x: x[1], reverse=True)[:10]),
            'preferred_content_types': dict(sorted(recent_content_types.items(), key=lambda x: x[1], reverse=True)),
            'interaction_patterns': dict(interaction_types),
            'avg_rating': metrics.avg_rating,
            'total_interactions': len(self.interactions[user_id]),
            'last_interaction': metrics.last_interaction.isoformat(),
            'behavioral_signals': {
                'high_engagement': metrics.clicks_count > 20,
                'rates_content': metrics.ratings_given > 5,
                'bookmarks_actively': metrics.bookmarks_added > 3,
                'consistent_user': len(self.interactions[user_id]) > 10
            }
        }
    
    def get_recommendation_analytics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get analytics data for recommendations"""
        if user_id:
            interactions = self.interactions[user_id]
            metrics = self.user_metrics[user_id]
            
            return {
                'user_specific': True,
                'user_id': user_id,
                'total_interactions': len(interactions),
                'clicks': metrics.clicks_count,
                'ratings': metrics.ratings_given,
                'bookmarks': metrics.bookmarks_added,
                'avg_rating': metrics.avg_rating,
                'time_spent_hours': metrics.total_time_spent_seconds / 3600,
                'engagement_score': self._calculate_engagement_score(metrics)
            }
        else:
            # Global analytics
            total_users = len(self.user_metrics)
            total_interactions = sum(len(interactions) for interactions in self.interactions.values())
            
            return {
                'user_specific': False,
                'total_users': total_users,
                'total_interactions': total_interactions,
                'avg_interactions_per_user': total_interactions / max(1, total_users),
                'active_users_last_day': self._get_active_users_count(hours=24),
                'most_common_interactions': self._get_most_common_interactions()
            }
    
    def _calculate_engagement_score(self, metrics: UserBehaviorMetrics) -> float:
        """Calculate user engagement score (0-100)"""
        score = 0
        score += min(30, metrics.clicks_count * 1.5)  # Up to 30 points for clicks
        score += min(25, metrics.ratings_given * 5)   # Up to 25 points for ratings
        score += min(20, metrics.bookmarks_added * 7) # Up to 20 points for bookmarks
        score += min(15, metrics.avg_rating * 3)      # Up to 15 points for high ratings
        score += min(10, metrics.session_count * 2)   # Up to 10 points for sessions
        
        return min(100, score)
    
    def _get_active_users_count(self, hours: int) -> int:
        """Get count of users active in last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return sum(1 for metrics in self.user_metrics.values() 
                  if metrics.last_interaction > cutoff_time)
    
    def _get_most_common_interactions(self) -> Dict[str, int]:
        """Get most common interaction types across all users"""
        interaction_counts = defaultdict(int)
        for user_interactions in self.interactions.values():
            for interaction in user_interactions:
                interaction_counts[interaction.interaction_type] += 1
        
        return dict(sorted(interaction_counts.items(), key=lambda x: x[1], reverse=True))

class AdaptiveLearningSystem:
    """Learn from user behavior to improve recommendations (while processing ALL content)"""
    
    def __init__(self):
        self.user_learning_profiles = defaultdict(dict)
        self.content_performance = defaultdict(dict)
        self.global_patterns = defaultdict(float)
        self.lock = threading.Lock()
        
        logger.info("✅ AdaptiveLearningSystem initialized - learns while processing ALL user content")
    
    def learn_from_interaction(self, user_id: int, content_id: int, interaction_type: str, 
                              interaction_value: Optional[float] = None, 
                              content_metadata: Optional[Dict[str, Any]] = None):
        """Learn from user interaction to improve future recommendations"""
        try:
            with self.lock:
                # Update user learning profile
                self._update_user_learning_profile(user_id, content_id, interaction_type, 
                                                 interaction_value, content_metadata)
                
                # Update content performance metrics
                self._update_content_performance(content_id, interaction_type, interaction_value)
                
                # Update global patterns
                self._update_global_patterns(interaction_type, content_metadata)
                
                logger.debug(f"Learning updated for user {user_id} interaction with content {content_id}")
                
        except Exception as e:
            logger.error(f"Error in adaptive learning: {e}")
    
    def _update_user_learning_profile(self, user_id: int, content_id: int, interaction_type: str,
                                    interaction_value: Optional[float], content_metadata: Optional[Dict[str, Any]]):
        """Update user's learning profile based on interaction"""
        profile = self.user_learning_profiles[user_id]
        
        # Initialize profile if needed
        if 'technology_preferences' not in profile:
            profile['technology_preferences'] = defaultdict(float)
            profile['content_type_preferences'] = defaultdict(float)
            profile['difficulty_preferences'] = defaultdict(float)
            profile['scoring_weights'] = {
                'semantic_similarity': 0.25,
                'technology_relevance': 0.25,
                'content_quality': 0.20,
                'context_awareness': 0.20,
                'intent_alignment': 0.10
            }
            profile['interaction_count'] = 0
        
        profile['interaction_count'] += 1
        
        # Learn from content metadata
        if content_metadata:
            # Update technology preferences
            if 'technologies' in content_metadata:
                weight = self._get_interaction_weight(interaction_type, interaction_value)
                for tech in content_metadata['technologies']:
                    profile['technology_preferences'][tech] += weight
            
            # Update content type preferences
            if 'content_type' in content_metadata:
                content_type = content_metadata['content_type']
                weight = self._get_interaction_weight(interaction_type, interaction_value)
                profile['content_type_preferences'][content_type] += weight
            
            # Update difficulty preferences
            if 'difficulty' in content_metadata:
                difficulty = content_metadata['difficulty']
                weight = self._get_interaction_weight(interaction_type, interaction_value)
                profile['difficulty_preferences'][difficulty] += weight
        
        # Adapt scoring weights based on interaction patterns
        self._adapt_scoring_weights(profile, interaction_type, interaction_value)
    
    def _get_interaction_weight(self, interaction_type: str, interaction_value: Optional[float]) -> float:
        """Get learning weight based on interaction type and value"""
        base_weights = {
            'click': 0.1,
            'view': 0.2,
            'rating': 0.5,
            'bookmark': 0.8,
            'share': 0.6,
            'dismiss': -0.3
        }
        
        weight = base_weights.get(interaction_type, 0.1)
        
        # Adjust by interaction value (e.g., rating score, time spent)
        if interaction_value is not None:
            if interaction_type == 'rating':
                # Rating scale 1-5, adjust weight accordingly
                weight *= (interaction_value / 5.0)
            elif interaction_type == 'view':
                # Time spent viewing (normalize to reasonable time)
                weight *= min(2.0, interaction_value / 60.0)  # 60 seconds = 1x weight
        
        return weight
    
    def _adapt_scoring_weights(self, profile: Dict[str, Any], interaction_type: str, interaction_value: Optional[float]):
        """Adapt scoring weights based on user interaction patterns"""
        weights = profile['scoring_weights']
        learning_rate = 0.01  # Small learning rate for gradual adaptation
        
        # Positive interactions: slightly increase weights that led to this content
        if interaction_type in ['rating', 'bookmark', 'share'] and (interaction_value is None or interaction_value > 3):
            # Increase semantic similarity weight if user consistently engages with semantically similar content
            weights['semantic_similarity'] = min(0.4, weights['semantic_similarity'] + learning_rate)
            
        # Negative interactions: slightly decrease weights
        elif interaction_type in ['dismiss'] or (interaction_type == 'rating' and interaction_value and interaction_value < 3):
            # Decrease the weight that might have led to poor recommendation
            weights['content_quality'] = max(0.1, weights['content_quality'] - learning_rate)
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] = weights[key] / total_weight
    
    def _update_content_performance(self, content_id: int, interaction_type: str, interaction_value: Optional[float]):
        """Update content performance metrics"""
        if content_id not in self.content_performance:
            self.content_performance[content_id] = {
                'clicks': 0, 'views': 0, 'ratings': [], 'bookmarks': 0, 
                'shares': 0, 'dismissals': 0, 'total_interactions': 0
            }
        
        perf = self.content_performance[content_id]
        perf['total_interactions'] += 1
        
        if interaction_type == 'click':
            perf['clicks'] += 1
        elif interaction_type == 'view':
            perf['views'] += 1
        elif interaction_type == 'rating' and interaction_value:
            perf['ratings'].append(interaction_value)
        elif interaction_type == 'bookmark':
            perf['bookmarks'] += 1
        elif interaction_type == 'share':
            perf['shares'] += 1
        elif interaction_type == 'dismiss':
            perf['dismissals'] += 1
    
    def _update_global_patterns(self, interaction_type: str, content_metadata: Optional[Dict[str, Any]]):
        """Update global interaction patterns"""
        self.global_patterns[f'interaction_{interaction_type}'] += 1
        
        if content_metadata:
            if 'content_type' in content_metadata:
                self.global_patterns[f'content_type_{content_metadata["content_type"]}'] += 1
            if 'technologies' in content_metadata:
                for tech in content_metadata['technologies']:
                    self.global_patterns[f'technology_{tech}'] += 1
    
    def get_personalized_scoring_weights(self, user_id: int) -> Dict[str, float]:
        """Get personalized scoring weights for a user"""
        profile = self.user_learning_profiles.get(user_id, {})
        
        if 'scoring_weights' in profile and profile['interaction_count'] >= 10:
            # Use learned weights if user has enough interactions
            return profile['scoring_weights'].copy()
        else:
            # Use default weights for new users
            return {
                'semantic_similarity': 0.25,
                'technology_relevance': 0.25,
                'content_quality': 0.20,
                'context_awareness': 0.20,
                'intent_alignment': 0.10
            }
    
    def get_user_technology_preferences(self, user_id: int) -> Dict[str, float]:
        """Get user's technology preferences for boosting relevant content"""
        profile = self.user_learning_profiles.get(user_id, {})
        return dict(profile.get('technology_preferences', {}))
    
    def get_content_performance_score(self, content_id: int) -> float:
        """Get performance score for content (0.0 to 1.0)"""
        perf = self.content_performance.get(content_id, {})
        
        if not perf or perf.get('total_interactions', 0) == 0:
            return 0.5  # Neutral score for new content
        
        # Calculate performance score based on positive interactions
        positive_score = 0
        total_interactions = perf['total_interactions']
        
        # Clicks contribute positively
        positive_score += (perf.get('clicks', 0) / total_interactions) * 0.2
        
        # Views contribute positively
        positive_score += (perf.get('views', 0) / total_interactions) * 0.1
        
        # High ratings contribute significantly
        ratings = perf.get('ratings', [])
        if ratings:
            avg_rating = np.mean(ratings)
            positive_score += (avg_rating / 5.0) * 0.4  # Normalize 1-5 rating to 0-1
        
        # Bookmarks contribute highly
        positive_score += (perf.get('bookmarks', 0) / total_interactions) * 0.3
        
        # Dismissals reduce score
        dismissals = perf.get('dismissals', 0)
        negative_score = (dismissals / total_interactions) * 0.3
        
        final_score = max(0.0, min(1.0, positive_score - negative_score))
        return final_score
    
    def get_learning_insights(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get insights from the learning system"""
        if user_id:
            profile = self.user_learning_profiles.get(user_id, {})
            return {
                'user_specific': True,
                'user_id': user_id,
                'interaction_count': profile.get('interaction_count', 0),
                'personalized_weights': self.get_personalized_scoring_weights(user_id),
                'technology_preferences': dict(profile.get('technology_preferences', {})),
                'content_type_preferences': dict(profile.get('content_type_preferences', {})),
                'has_learned_preferences': profile.get('interaction_count', 0) >= 10
            }
        else:
            return {
                'user_specific': False,
                'total_users_with_profiles': len(self.user_learning_profiles),
                'total_content_tracked': len(self.content_performance),
                'global_patterns': dict(self.global_patterns),
                'avg_interactions_per_user': np.mean([p.get('interaction_count', 0) for p in self.user_learning_profiles.values()]) if self.user_learning_profiles else 0
            }

# Export the main classes for integration
__all__ = [
    'SystemLoadMonitor',
    'UserBehaviorTracker', 
    'AdaptiveLearningSystem',
    'SystemLoadMetrics',
    'UserBehaviorMetrics',
    'RecommendationInteraction'
]

if __name__ == "__main__":
    print("🚀 Orchestrator Enhancements Implementation")
    print("=" * 60)
    print("✅ SystemLoadMonitor - Performance optimization (no content limits)")
    print("✅ UserBehaviorTracker - Learning from user interactions")
    print("✅ AdaptiveLearningSystem - Personalized recommendations")
    print("=" * 60)
    print("🎯 ALL USER CONTENT IS ALWAYS PROCESSED - NO LIMITS APPLIED!")
