#!/usr/bin/env python3
"""
Enhanced Recommendation System - Phase 3: Advanced Features
Contextual Recommendations, Real-time Learning, Advanced Analytics, Global Scaling
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import inside functions to avoid circular imports
# from enhanced_recommendation_engine import (
#     get_enhanced_recommendations, unified_engine, 
#     RecommendationResult, UserProfile, PerformanceMetrics
# )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ContextualData:
    """Contextual information for recommendations"""
    timestamp: datetime
    user_agent: str
    device_type: str
    location: Optional[str]
    time_of_day: str
    day_of_week: str
    session_duration: int
    previous_interactions: List[str]
    current_project: Optional[str]
    learning_session: bool

@dataclass
class UserProfile:
    """Comprehensive user profile"""
    user_id: int
    interests: List[str]
    skill_level: str
    learning_style: str
    technology_preferences: List[str]
    content_preferences: Dict[str, float]
    difficulty_preferences: Dict[str, float]
    interaction_patterns: Dict[str, Any]
    last_updated: datetime

@dataclass
class LearningMetrics:
    """Real-time learning metrics"""
    user_engagement: float
    content_effectiveness: float
    algorithm_performance: Dict[str, float]
    user_satisfaction: float
    learning_progress: float
    adaptation_rate: float

class ContextualAnalyzer:
    """Analyze and incorporate contextual information"""
    
    def __init__(self):
        self.device_patterns = {
            'mobile': ['mobile', 'android', 'ios', 'phone', 'tablet'],
            'desktop': ['desktop', 'windows', 'mac', 'linux'],
            'tablet': ['ipad', 'tablet', 'surface']
        }
        self.time_patterns = {
            'morning': (6, 12),
            'afternoon': (12, 18),
            'evening': (18, 22),
            'night': (22, 6)
        }
        
    def analyze_context(self, request_data: Dict[str, Any], user_id: int) -> ContextualData:
        """Analyze contextual information from request"""
        try:
            # Extract contextual information
            user_agent = request_data.get('user_agent', '')
            timestamp = datetime.now()
            
            # Device type detection
            device_type = self._detect_device_type(user_agent)
            
            # Time-based analysis
            time_of_day = self._get_time_of_day(timestamp)
            day_of_week = timestamp.strftime('%A').lower()
            
            # Session analysis
            session_duration = self._get_session_duration(user_id)
            previous_interactions = self._get_previous_interactions(user_id)
            
            # Project context
            current_project = request_data.get('project_title')
            learning_session = self._is_learning_session(user_id, timestamp)
            
            return ContextualData(
                timestamp=timestamp,
                user_agent=user_agent,
                device_type=device_type,
                location=None,  # Could be enhanced with IP geolocation
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                session_duration=session_duration,
                previous_interactions=previous_interactions,
                current_project=current_project,
                learning_session=learning_session
            )
            
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            return self._get_default_context()
    
    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        user_agent_lower = user_agent.lower()
        
        for device_type, patterns in self.device_patterns.items():
            if any(pattern in user_agent_lower for pattern in patterns):
                return device_type
        
        return 'desktop'  # Default
    
    def _get_time_of_day(self, timestamp: datetime) -> str:
        """Get time of day category"""
        hour = timestamp.hour
        
        for time_category, (start, end) in self.time_patterns.items():
            if start <= hour < end:
                return time_category
        
        return 'night'
    
    def _get_session_duration(self, user_id: int) -> int:
        """Get current session duration in minutes"""
        try:
            # This would integrate with session management
            # For now, return a default value
            return 30
        except Exception:
            return 0
    
    def _get_previous_interactions(self, user_id: int) -> List[str]:
        """Get recent user interactions"""
        try:
            # Import here to avoid circular imports
            from models import Feedback
            
            # Query recent user interactions from database
            recent_interactions = Feedback.query.filter_by(user_id=user_id)\
                .order_by(Feedback.created_at.desc())\
                .limit(10)\
                .all()
            
            return [interaction.feedback_type for interaction in recent_interactions]
        except Exception:
            return []
    
    def _is_learning_session(self, user_id: int, timestamp: datetime) -> bool:
        """Determine if this is part of a learning session"""
        try:
            # Import here to avoid circular imports
            from models import Feedback
            
            # Check if user has been active in the last hour
            one_hour_ago = timestamp - timedelta(hours=1)
            recent_activity = Feedback.query.filter_by(user_id=user_id)\
                .filter(Feedback.created_at >= one_hour_ago)\
                .count()
            
            return recent_activity > 2
        except Exception:
            return False
    
    def _get_default_context(self) -> ContextualData:
        """Get default contextual data"""
        now = datetime.now()
        return ContextualData(
            timestamp=now,
            user_agent='',
            device_type='desktop',
            location=None,
            time_of_day=self._get_time_of_day(now),
            day_of_week=now.strftime('%A').lower(),
            session_duration=0,
            previous_interactions=[],
            current_project=None,
            learning_session=False
        )

class RealTimeLearner:
    """Real-time learning and adaptation system"""
    
    def __init__(self):
        self.user_profiles = {}
        self.algorithm_performance = defaultdict(list)
        self.content_effectiveness = defaultdict(list)
        self.learning_rate = 0.1
        self.adaptation_threshold = 0.05
        
    def update_user_profile(self, user_id: int, interaction_data: Dict[str, Any]):
        """Update user profile based on interaction"""
        try:
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile(
                    user_id=user_id,
                    interests=[],
                    skill_level='beginner',
                    learning_style='visual',
                    technology_preferences=[],
                    content_preferences={'tutorial': 0.5, 'documentation': 0.3, 'example': 0.2},
                    difficulty_preferences={'beginner': 0.4, 'intermediate': 0.4, 'advanced': 0.2},
                    interaction_patterns={},
                    last_updated=datetime.now()
                )
            
            profile = self.user_profiles[user_id]
            
            # Update based on interaction
            feedback_type = interaction_data.get('feedback_type')
            content_id = interaction_data.get('content_id')
            algorithm_used = interaction_data.get('algorithm_used')
            
            if feedback_type == 'relevant':
                self._boost_preferences(profile, interaction_data)
            elif feedback_type == 'not_relevant':
                self._reduce_preferences(profile, interaction_data)
            
            # Update algorithm performance
            if algorithm_used:
                self.algorithm_performance[algorithm_used].append(1.0 if feedback_type == 'relevant' else 0.0)
            
            # Update content effectiveness
            if content_id:
                self.content_effectiveness[content_id].append(1.0 if feedback_type == 'relevant' else 0.0)
            
            profile.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
    
    def _boost_preferences(self, profile: UserProfile, interaction_data: Dict[str, Any]):
        """Boost preferences based on positive interaction"""
        content_type = interaction_data.get('content_type')
        difficulty = interaction_data.get('difficulty')
        technologies = interaction_data.get('technologies', [])
        
        # Update content preferences
        if content_type and content_type in profile.content_preferences:
            profile.content_preferences[content_type] += self.learning_rate
            self._normalize_preferences(profile.content_preferences)
        
        # Update difficulty preferences
        if difficulty and difficulty in profile.difficulty_preferences:
            profile.difficulty_preferences[difficulty] += self.learning_rate
            self._normalize_preferences(profile.difficulty_preferences)
        
        # Update technology preferences
        for tech in technologies:
            if tech not in profile.technology_preferences:
                profile.technology_preferences.append(tech)
    
    def _reduce_preferences(self, profile: UserProfile, interaction_data: Dict[str, Any]):
        """Reduce preferences based on negative interaction"""
        content_type = interaction_data.get('content_type')
        difficulty = interaction_data.get('difficulty')
        
        # Update content preferences
        if content_type and content_type in profile.content_preferences:
            profile.content_preferences[content_type] -= self.learning_rate
            self._normalize_preferences(profile.content_preferences)
        
        # Update difficulty preferences
        if difficulty and difficulty in profile.difficulty_preferences:
            profile.difficulty_preferences[difficulty] -= self.learning_rate
            self._normalize_preferences(profile.difficulty_preferences)
    
    def _normalize_preferences(self, preferences: Dict[str, float]):
        """Normalize preference values to sum to 1.0"""
        total = sum(preferences.values())
        if total > 0:
            for key in preferences:
                preferences[key] = max(0.0, preferences[key] / total)
    
    def get_adapted_parameters(self, user_id: int, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get adapted parameters based on user profile"""
        try:
            if user_id not in self.user_profiles:
                return request_data
            
            profile = self.user_profiles[user_id]
            adapted_data = request_data.copy()
            
            # Adapt content type preferences
            if 'content_type' not in adapted_data or adapted_data['content_type'] == 'all':
                # Select preferred content type
                preferred_type = max(profile.content_preferences.items(), key=lambda x: x[1])[0]
                adapted_data['content_type'] = preferred_type
            
            # Adapt difficulty preferences
            if 'difficulty' not in adapted_data or adapted_data['difficulty'] == 'all':
                # Select preferred difficulty
                preferred_difficulty = max(profile.difficulty_preferences.items(), key=lambda x: x[1])[0]
                adapted_data['difficulty'] = preferred_difficulty
            
            # Add technology preferences
            if profile.technology_preferences:
                existing_techs = adapted_data.get('technologies', '')
                if existing_techs:
                    existing_techs += ', '
                existing_techs += ', '.join(profile.technology_preferences[:3])  # Top 3
                adapted_data['technologies'] = existing_techs
            
            return adapted_data
            
        except Exception as e:
            logger.error(f"Error getting adapted parameters: {e}")
            return request_data
    
    def get_learning_metrics(self, user_id: int) -> LearningMetrics:
        """Get learning metrics for a user"""
        try:
            profile = self.user_profiles.get(user_id)
            if not profile:
                return self._get_default_learning_metrics()
            
            # Calculate engagement based on interaction frequency
            time_since_update = (datetime.now() - profile.last_updated).total_seconds()
            engagement = max(0.0, 1.0 - (time_since_update / 86400))  # Decay over 24 hours
            
            # Calculate content effectiveness
            content_effectiveness = 0.0
            if self.content_effectiveness:
                all_ratings = [rating for ratings in self.content_effectiveness.values() for rating in ratings]
                if all_ratings:
                    content_effectiveness = sum(all_ratings) / len(all_ratings)
            
            # Calculate algorithm performance
            algorithm_performance = {}
            for algo, ratings in self.algorithm_performance.items():
                if ratings:
                    algorithm_performance[algo] = sum(ratings) / len(ratings)
            
            # Calculate user satisfaction
            user_satisfaction = (engagement + content_effectiveness) / 2
            
            # Calculate learning progress
            learning_progress = len(profile.technology_preferences) / 10.0  # Normalize to 0-1
            
            # Calculate adaptation rate
            adaptation_rate = len(profile.interaction_patterns) / 100.0  # Normalize to 0-1
            
            return LearningMetrics(
                user_engagement=engagement,
                content_effectiveness=content_effectiveness,
                algorithm_performance=algorithm_performance,
                user_satisfaction=user_satisfaction,
                learning_progress=learning_progress,
                adaptation_rate=adaptation_rate
            )
            
        except Exception as e:
            logger.error(f"Error getting learning metrics: {e}")
            return self._get_default_learning_metrics()
    
    def _get_default_learning_metrics(self) -> LearningMetrics:
        """Get default learning metrics"""
        return LearningMetrics(
            user_engagement=0.0,
            content_effectiveness=0.0,
            algorithm_performance={},
            user_satisfaction=0.0,
            learning_progress=0.0,
            adaptation_rate=0.0
        )

# Initialize Phase 3 components
contextual_analyzer = ContextualAnalyzer()
real_time_learner = RealTimeLearner()

def get_enhanced_recommendations_phase3(user_id: int, request_data: Dict[str, Any], 
                                      limit: int = 10) -> List[Dict[str, Any]]:
    """Enhanced recommendations with Phase 3 features"""
    try:
        # Import inside function to avoid circular imports
        from enhanced_recommendation_engine import get_enhanced_recommendations
        
        start_time = time.time()
        
        # Initialize components
        contextual_analyzer = ContextualAnalyzer()
        real_time_learner = RealTimeLearner()
        
        # Phase 3: Contextual Analysis
        context = contextual_analyzer.analyze_context(request_data, user_id)
        
        # Phase 3: Real-time Learning Adaptation
        adapted_data = real_time_learner.get_adapted_parameters(user_id, request_data)
        
        # Get base recommendations
        recommendations = get_enhanced_recommendations(user_id, adapted_data, limit)
        
        # Phase 3: Contextual Enhancement
        enhanced_recommendations = []
        for rec in recommendations:
            enhanced_rec = rec.copy()
            
            # Add contextual information
            enhanced_rec['context'] = {
                'device_optimized': context.device_type,
                'time_appropriate': context.time_of_day,
                'session_context': context.learning_session,
                'day_of_week': context.day_of_week
            }
            
            # Add learning insights
            learning_metrics = real_time_learner.get_learning_metrics(user_id)
            enhanced_rec['learning_insights'] = {
                'engagement_score': learning_metrics.user_engagement,
                'content_effectiveness': learning_metrics.content_effectiveness,
                'learning_progress': learning_metrics.learning_progress,
                'user_satisfaction': learning_metrics.user_satisfaction
            }
            
            enhanced_recommendations.append(enhanced_rec)
        
        # Phase 3: Performance tracking
        response_time = (time.time() - start_time) * 1000
        
        logger.info(f"Phase 3 recommendations generated in {response_time:.2f}ms")
        
        return enhanced_recommendations
        
    except Exception as e:
        logger.error(f"Error in Phase 3 enhanced recommendations: {e}")
        # Fallback to Phase 2
        try:
            from enhanced_recommendation_engine import get_enhanced_recommendations
            return get_enhanced_recommendations(user_id, request_data, limit)
        except:
            return []

def record_user_feedback_phase3(user_id: int, recommendation_id: int, 
                               feedback_type: str, feedback_data: Dict[str, Any] = None):
    """Record user feedback with Phase 3 learning"""
    try:
        # Import inside function to avoid circular imports
        from enhanced_recommendation_engine import unified_engine
        
        # Initialize components
        real_time_learner = RealTimeLearner()
        
        # Record feedback in base system
        unified_engine.integrate_user_feedback(user_id, recommendation_id, feedback_type, feedback_data)
        
        # Phase 3: Real-time Learning
        interaction_data = {
            'feedback_type': feedback_type,
            'recommendation_id': recommendation_id,
            'feedback_data': feedback_data or {},
            'timestamp': datetime.now()
        }
        real_time_learner.update_user_profile(user_id, interaction_data)
        
        logger.info(f"Phase 3 feedback recorded for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error recording Phase 3 feedback: {e}")

def get_user_learning_insights(user_id: int) -> Dict[str, Any]:
    """Get user learning insights from Phase 3"""
    try:
        learning_metrics = real_time_learner.get_learning_metrics(user_id)
        
        insights = {
            'learning_metrics': asdict(learning_metrics),
            'user_profile': asdict(real_time_learner.user_profiles.get(user_id, UserProfile(
                user_id=user_id,
                interests=[],
                skill_level='beginner',
                learning_style='visual',
                technology_preferences=[],
                content_preferences={'tutorial': 0.5, 'documentation': 0.3, 'example': 0.2},
                difficulty_preferences={'beginner': 0.4, 'intermediate': 0.4, 'advanced': 0.2},
                interaction_patterns={},
                last_updated=datetime.now()
            ))),
            'phase': 'phase_3_complete'
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"Error getting user learning insights: {e}")
        return {'error': 'Unable to generate insights', 'phase': 'phase_3_error'}

def get_system_health_phase3() -> Dict[str, Any]:
    """Get comprehensive system health with Phase 3 metrics"""
    try:
        # Base system health
        base_health = {
            'enhanced_engine_available': True,
            'phase_1_complete': True,
            'phase_2_complete': True,
            'phase_3_complete': True
        }
        
        # Phase 3: Performance metrics
        performance_metrics = unified_engine.get_performance_metrics()
        
        # Phase 3: Learning system status
        learning_status = {
            'active_users': len(real_time_learner.user_profiles),
            'total_interactions': sum(len(ratings) for ratings in real_time_learner.algorithm_performance.values()),
            'adaptation_rate': sum(
                real_time_learner.get_learning_metrics(user_id).adaptation_rate 
                for user_id in real_time_learner.user_profiles.keys()
            ) / max(1, len(real_time_learner.user_profiles))
        }
        
        comprehensive_health = {
            **base_health,
            'performance_metrics': asdict(performance_metrics),
            'learning_system': learning_status,
            'contextual_analysis': {
                'device_patterns': len(contextual_analyzer.device_patterns),
                'time_patterns': len(contextual_analyzer.time_patterns)
            }
        }
        
        return comprehensive_health
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 system health: {e}")
        return {
            'enhanced_engine_available': True,
            'phase_1_complete': True,
            'phase_2_complete': True,
            'phase_3_complete': False,
            'error': str(e)
        } 