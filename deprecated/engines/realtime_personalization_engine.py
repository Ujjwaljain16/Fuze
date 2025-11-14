#!/usr/bin/env python3
"""
Real-time Personalization Engine
- Dynamic user profiling based on real-time interactions
- Context-aware personalization for recommendations
- Real-time preference adaptation and learning
- Session-based personalization with immediate updates
- Multi-dimensional personalization (content, difficulty, technology, style)

CRITICAL: Enhances personalization while processing ALL user content!
"""

import time
import logging
from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import numpy as np
import json
import uuid

logger = logging.getLogger(__name__)

@dataclass
class PersonalizationContext:
    """Current personalization context for a user session"""
    user_id: int
    session_id: str
    current_query: str = ""
    current_intent: str = "explore"
    current_domain: str = "general"
    current_technologies: List[str] = field(default_factory=list)
    current_complexity: str = "intermediate"
    time_of_day: str = "day"  # morning, day, evening, night
    device_type: str = "desktop"  # desktop, mobile, tablet
    interaction_speed: str = "normal"  # fast, normal, slow
    focus_areas: List[str] = field(default_factory=list)
    session_duration: float = 0.0
    interactions_count: int = 0
    last_interaction_time: datetime = field(default_factory=datetime.now)

@dataclass
class UserPersonalizationProfile:
    """Comprehensive user personalization profile"""
    user_id: int
    
    # Core preferences (learned over time)
    preferred_content_types: Dict[str, float] = field(default_factory=dict)
    preferred_technologies: Dict[str, float] = field(default_factory=dict)
    preferred_difficulty_levels: Dict[str, float] = field(default_factory=dict)
    preferred_domains: Dict[str, float] = field(default_factory=dict)
    preferred_learning_styles: Dict[str, float] = field(default_factory=dict)
    
    # Behavioral patterns
    interaction_velocity: float = 1.0  # How fast user browses (0.5=slow, 2.0=fast)
    exploration_tendency: float = 0.5  # Tendency to explore new vs familiar (0=exploit, 1=explore)
    depth_vs_breadth: float = 0.5  # Preference for deep vs broad content (0=breadth, 1=depth)
    theoretical_vs_practical: float = 0.5  # Theory vs practical preference (0=practical, 1=theoretical)
    beginner_friendly_bias: float = 0.0  # Bias towards beginner content (-1 to 1)
    
    # Temporal patterns
    activity_times: Dict[str, float] = field(default_factory=dict)  # time_of_day -> activity_level
    session_length_preference: float = 30.0  # Preferred session length in minutes
    
    # Context patterns
    device_usage_patterns: Dict[str, float] = field(default_factory=dict)
    query_patterns: List[str] = field(default_factory=list)
    successful_content_patterns: List[Dict[str, Any]] = field(default_factory=list)
    
    # Real-time adaptations
    current_session_bias: Dict[str, float] = field(default_factory=dict)
    recent_interaction_patterns: deque = field(default_factory=lambda: deque(maxlen=20))
    
    # Meta information
    profile_confidence: float = 0.0  # How confident we are in this profile (0-1)
    last_update: datetime = field(default_factory=datetime.now)
    total_interactions: int = 0
    personalization_enabled: bool = True

@dataclass
class PersonalizationConfiguration:
    """Configuration for real-time personalization"""
    enable_real_time_updates: bool = True
    session_timeout_minutes: int = 30
    min_interactions_for_personalization: int = 3
    personalization_learning_rate: float = 0.1
    context_weight: float = 0.3  # How much current context affects recommendations
    profile_weight: float = 0.7  # How much historical profile affects recommendations
    real_time_boost_factor: float = 0.2  # Boost for real-time preferences
    decay_factor: float = 0.95  # How quickly old preferences decay
    confidence_threshold: float = 0.3  # Minimum confidence for personalization
    max_profile_size: int = 1000  # Maximum number of patterns to store

class RealtimePersonalizationEngine:
    """Real-time personalization engine for dynamic user adaptation"""
    
    def __init__(self, config: Optional[PersonalizationConfiguration] = None):
        self.config = config or PersonalizationConfiguration()
        self.user_profiles = defaultdict(lambda: UserPersonalizationProfile(user_id=0))
        self.active_sessions = {}  # session_id -> PersonalizationContext
        self.personalization_history = defaultdict(list)
        self.content_performance = defaultdict(lambda: defaultdict(float))  # user_id -> content_id -> score
        
        logger.info("✅ Real-time Personalization Engine initialized - adapting while processing ALL content")
    
    def start_personalization_session(self, user_id: int, initial_context: Optional[Dict[str, Any]] = None) -> str:
        """Start a new personalization session"""
        try:
            session_id = str(uuid.uuid4())
            
            # Create session context
            context = PersonalizationContext(
                user_id=user_id,
                session_id=session_id,
                time_of_day=self._get_time_of_day(),
                device_type=initial_context.get('device_type', 'desktop') if initial_context else 'desktop'
            )
            
            # Update with initial context if provided
            if initial_context:
                if 'query' in initial_context:
                    context.current_query = initial_context['query']
                if 'intent' in initial_context:
                    context.current_intent = initial_context['intent']
                if 'technologies' in initial_context:
                    context.current_technologies = initial_context['technologies']
                if 'domain' in initial_context:
                    context.current_domain = initial_context['domain']
            
            self.active_sessions[session_id] = context
            
            # Clean up old sessions
            self._cleanup_old_sessions()
            
            logger.debug(f"Started personalization session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting personalization session: {e}")
            return str(uuid.uuid4())  # Return a session ID anyway
    
    def update_session_context(self, session_id: str, updates: Dict[str, Any]):
        """Update session context with new information"""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found")
                return
            
            context = self.active_sessions[session_id]
            
            # Update context fields
            if 'query' in updates:
                context.current_query = updates['query']
            if 'intent' in updates:
                context.current_intent = updates['intent']
            if 'technologies' in updates:
                context.current_technologies = updates['technologies']
            if 'domain' in updates:
                context.current_domain = updates['domain']
            if 'complexity' in updates:
                context.current_complexity = updates['complexity']
            if 'focus_areas' in updates:
                context.focus_areas = updates['focus_areas']
            
            # Update session metrics
            context.interactions_count += 1
            current_time = datetime.now()
            context.session_duration = (current_time - context.last_interaction_time).total_seconds()
            context.last_interaction_time = current_time
            
            # Determine interaction speed
            if context.session_duration > 0:
                interactions_per_minute = context.interactions_count / (context.session_duration / 60)
                if interactions_per_minute > 10:
                    context.interaction_speed = "fast"
                elif interactions_per_minute < 3:
                    context.interaction_speed = "slow"
                else:
                    context.interaction_speed = "normal"
            
        except Exception as e:
            logger.error(f"Error updating session context: {e}")
    
    def record_interaction(self, session_id: str, interaction_data: Dict[str, Any]):
        """Record user interaction for real-time learning"""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found for interaction recording")
                return
            
            context = self.active_sessions[session_id]
            user_id = context.user_id
            
            # Update session context
            self.update_session_context(session_id, interaction_data)
            
            # Get user profile
            profile = self.user_profiles[user_id]
            
            # Learn from interaction in real-time
            self._learn_from_interaction(profile, context, interaction_data)
            
            # Update content performance
            if 'content_id' in interaction_data and 'rating' in interaction_data:
                content_id = interaction_data['content_id']
                rating = float(interaction_data['rating'])
                self.content_performance[user_id][content_id] = rating
            
            # Store interaction pattern
            interaction_pattern = {
                'timestamp': datetime.now(),
                'interaction_type': interaction_data.get('type', 'unknown'),
                'content_type': interaction_data.get('content_type', 'unknown'),
                'technologies': interaction_data.get('technologies', []),
                'domain': interaction_data.get('domain', 'general'),
                'rating': interaction_data.get('rating', 0),
                'session_context': {
                    'time_of_day': context.time_of_day,
                    'device_type': context.device_type,
                    'interaction_speed': context.interaction_speed
                }
            }
            
            profile.recent_interaction_patterns.append(interaction_pattern)
            profile.total_interactions += 1
            profile.last_update = datetime.now()
            
            # Update profile confidence
            self._update_profile_confidence(profile)
            
            logger.debug(f"Recorded interaction for user {user_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
    
    def get_personalized_recommendations(self, recommendations: List[Dict[str, Any]], 
                                       session_id: str) -> List[Dict[str, Any]]:
        """Apply real-time personalization to recommendations"""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found for personalization")
                return recommendations
            
            context = self.active_sessions[session_id]
            user_id = context.user_id
            profile = self.user_profiles[user_id]
            
            # Check if we have enough data for personalization
            if (profile.total_interactions < self.config.min_interactions_for_personalization or
                profile.profile_confidence < self.config.confidence_threshold):
                logger.debug(f"Insufficient data for personalization (interactions: {profile.total_interactions}, confidence: {profile.profile_confidence})")
                return recommendations
            
            # Apply personalization
            personalized_recs = []
            
            for rec in recommendations:
                personalized_rec = rec.copy()
                
                # Calculate personalization score
                personalization_score = self._calculate_personalization_score(rec, profile, context)
                
                # Apply personalization boost
                original_score = rec.get('score', 0.5)
                personalized_score = (
                    original_score * (1 - self.config.real_time_boost_factor) +
                    personalization_score * self.config.real_time_boost_factor
                )
                
                personalized_rec['score'] = personalized_score
                personalized_rec['personalization_score'] = personalization_score
                personalized_rec['original_score'] = original_score
                personalized_rec['personalized'] = True
                
                # Add personalization metadata
                personalized_rec['personalization_factors'] = self._get_personalization_factors(rec, profile, context)
                
                personalized_recs.append(personalized_rec)
            
            # Sort by personalized score
            personalized_recs.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            logger.debug(f"Applied personalization to {len(personalized_recs)} recommendations for user {user_id}")
            return personalized_recs
            
        except Exception as e:
            logger.error(f"Error applying personalization: {e}")
            return recommendations
    
    def _learn_from_interaction(self, profile: UserPersonalizationProfile, 
                              context: PersonalizationContext, 
                              interaction_data: Dict[str, Any]):
        """Learn from interaction in real-time"""
        learning_rate = self.config.personalization_learning_rate
        
        # Learn content type preferences
        content_type = interaction_data.get('content_type', 'unknown')
        rating = interaction_data.get('rating', 0)
        if content_type != 'unknown' and rating > 0:
            if content_type in profile.preferred_content_types:
                profile.preferred_content_types[content_type] = (
                    profile.preferred_content_types[content_type] * (1 - learning_rate) +
                    (rating / 5.0) * learning_rate
                )
            else:
                profile.preferred_content_types[content_type] = (rating / 5.0) * learning_rate
        
        # Learn technology preferences
        technologies = interaction_data.get('technologies', [])
        if isinstance(technologies, str):
            technologies = [technologies]
        
        for tech in technologies:
            if rating > 0:
                if tech in profile.preferred_technologies:
                    profile.preferred_technologies[tech] = (
                        profile.preferred_technologies[tech] * (1 - learning_rate) +
                        (rating / 5.0) * learning_rate
                    )
                else:
                    profile.preferred_technologies[tech] = (rating / 5.0) * learning_rate
        
        # Learn difficulty preferences
        difficulty = interaction_data.get('difficulty', 'intermediate')
        if rating > 0:
            if difficulty in profile.preferred_difficulty_levels:
                profile.preferred_difficulty_levels[difficulty] = (
                    profile.preferred_difficulty_levels[difficulty] * (1 - learning_rate) +
                    (rating / 5.0) * learning_rate
                )
            else:
                profile.preferred_difficulty_levels[difficulty] = (rating / 5.0) * learning_rate
        
        # Learn domain preferences
        domain = interaction_data.get('domain', context.current_domain)
        if rating > 0:
            if domain in profile.preferred_domains:
                profile.preferred_domains[domain] = (
                    profile.preferred_domains[domain] * (1 - learning_rate) +
                    (rating / 5.0) * learning_rate
                )
            else:
                profile.preferred_domains[domain] = (rating / 5.0) * learning_rate
        
        # Learn behavioral patterns
        interaction_type = interaction_data.get('type', 'view')
        if interaction_type == 'quick_browse':
            profile.interaction_velocity = min(2.0, profile.interaction_velocity + 0.1)
        elif interaction_type == 'detailed_read':
            profile.interaction_velocity = max(0.5, profile.interaction_velocity - 0.05)
        
        # Learn temporal patterns
        time_of_day = context.time_of_day
        if time_of_day in profile.activity_times:
            profile.activity_times[time_of_day] += 0.1
        else:
            profile.activity_times[time_of_day] = 0.1
        
        # Learn device patterns
        device_type = context.device_type
        if device_type in profile.device_usage_patterns:
            profile.device_usage_patterns[device_type] += 0.1
        else:
            profile.device_usage_patterns[device_type] = 0.1
        
        # Apply decay to old preferences
        self._apply_preference_decay(profile)
    
    def _calculate_personalization_score(self, recommendation: Dict[str, Any], 
                                       profile: UserPersonalizationProfile,
                                       context: PersonalizationContext) -> float:
        """Calculate personalization score for a recommendation"""
        score = 0.0
        factors = []
        
        # Content type preference
        content_type = recommendation.get('content_type', 'unknown')
        if content_type in profile.preferred_content_types:
            content_score = profile.preferred_content_types[content_type]
            score += content_score * 0.25
            factors.append(f"content_type:{content_score:.2f}")
        
        # Technology preference
        rec_technologies = recommendation.get('technologies', [])
        if isinstance(rec_technologies, str):
            rec_technologies = [rec_technologies]
        
        tech_scores = []
        for tech in rec_technologies:
            if tech in profile.preferred_technologies:
                tech_scores.append(profile.preferred_technologies[tech])
        
        if tech_scores:
            avg_tech_score = np.mean(tech_scores)
            score += avg_tech_score * 0.3
            factors.append(f"technology:{avg_tech_score:.2f}")
        
        # Difficulty preference
        difficulty = recommendation.get('difficulty_level', 'intermediate')
        if difficulty in profile.preferred_difficulty_levels:
            difficulty_score = profile.preferred_difficulty_levels[difficulty]
            score += difficulty_score * 0.2
            factors.append(f"difficulty:{difficulty_score:.2f}")
        
        # Domain preference
        domain = recommendation.get('domain', 'general')
        if domain in profile.preferred_domains:
            domain_score = profile.preferred_domains[domain]
            score += domain_score * 0.15
            factors.append(f"domain:{domain_score:.2f}")
        
        # Context matching
        context_score = self._calculate_context_score(recommendation, context)
        score += context_score * 0.1
        factors.append(f"context:{context_score:.2f}")
        
        # Normalize score
        score = min(1.0, max(0.0, score))
        
        return score
    
    def _calculate_context_score(self, recommendation: Dict[str, Any], 
                                context: PersonalizationContext) -> float:
        """Calculate how well recommendation matches current context"""
        score = 0.0
        
        # Current technology focus
        rec_technologies = recommendation.get('technologies', [])
        if isinstance(rec_technologies, str):
            rec_technologies = [rec_technologies]
        
        common_techs = set(rec_technologies).intersection(set(context.current_technologies))
        if common_techs:
            score += len(common_techs) / max(len(context.current_technologies), 1) * 0.4
        
        # Current domain focus
        if recommendation.get('domain', 'general') == context.current_domain:
            score += 0.3
        
        # Current intent matching
        rec_intent = recommendation.get('intent_match', 'general')
        if rec_intent == context.current_intent:
            score += 0.3
        
        return min(1.0, score)
    
    def _get_personalization_factors(self, recommendation: Dict[str, Any], 
                                   profile: UserPersonalizationProfile,
                                   context: PersonalizationContext) -> Dict[str, Any]:
        """Get detailed personalization factors for explanation"""
        factors = {}
        
        # Content type match
        content_type = recommendation.get('content_type', 'unknown')
        if content_type in profile.preferred_content_types:
            factors['content_type_preference'] = profile.preferred_content_types[content_type]
        
        # Technology match
        rec_technologies = recommendation.get('technologies', [])
        if isinstance(rec_technologies, str):
            rec_technologies = [rec_technologies]
        
        matching_techs = {}
        for tech in rec_technologies:
            if tech in profile.preferred_technologies:
                matching_techs[tech] = profile.preferred_technologies[tech]
        
        if matching_techs:
            factors['technology_preferences'] = matching_techs
        
        # Context factors
        factors['session_context'] = {
            'time_of_day': context.time_of_day,
            'device_type': context.device_type,
            'interaction_speed': context.interaction_speed,
            'session_duration': context.session_duration
        }
        
        return factors
    
    def _apply_preference_decay(self, profile: UserPersonalizationProfile):
        """Apply decay to preferences to keep them fresh"""
        decay_factor = self.config.decay_factor
        
        # Decay content type preferences
        for content_type in profile.preferred_content_types:
            profile.preferred_content_types[content_type] *= decay_factor
        
        # Decay technology preferences
        for tech in profile.preferred_technologies:
            profile.preferred_technologies[tech] *= decay_factor
        
        # Decay difficulty preferences
        for difficulty in profile.preferred_difficulty_levels:
            profile.preferred_difficulty_levels[difficulty] *= decay_factor
        
        # Decay domain preferences
        for domain in profile.preferred_domains:
            profile.preferred_domains[domain] *= decay_factor
        
        # Remove very low preferences
        min_threshold = 0.01
        profile.preferred_content_types = {k: v for k, v in profile.preferred_content_types.items() if v > min_threshold}
        profile.preferred_technologies = {k: v for k, v in profile.preferred_technologies.items() if v > min_threshold}
        profile.preferred_difficulty_levels = {k: v for k, v in profile.preferred_difficulty_levels.items() if v > min_threshold}
        profile.preferred_domains = {k: v for k, v in profile.preferred_domains.items() if v > min_threshold}
    
    def _update_profile_confidence(self, profile: UserPersonalizationProfile):
        """Update confidence in user profile based on data quantity and consistency"""
        # Base confidence on number of interactions
        interaction_confidence = min(1.0, profile.total_interactions / 50.0)
        
        # Check consistency of recent interactions
        if len(profile.recent_interaction_patterns) >= 5:
            recent_ratings = [p.get('rating', 0) for p in profile.recent_interaction_patterns if p.get('rating', 0) > 0]
            if recent_ratings:
                rating_std = np.std(recent_ratings)
                consistency_confidence = max(0.0, 1.0 - (rating_std / 2.5))  # Lower std = higher confidence
            else:
                consistency_confidence = 0.5
        else:
            consistency_confidence = 0.3
        
        # Combine confidences
        profile.profile_confidence = (interaction_confidence * 0.7 + consistency_confidence * 0.3)
    
    def _get_time_of_day(self) -> str:
        """Get current time of day category"""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "day"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        cutoff_time = datetime.now() - timedelta(minutes=self.config.session_timeout_minutes)
        
        sessions_to_remove = []
        for session_id, context in self.active_sessions.items():
            if context.last_interaction_time < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
        
        if sessions_to_remove:
            logger.debug(f"Cleaned up {len(sessions_to_remove)} inactive sessions")
    
    def get_personalization_analytics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get personalization analytics and insights"""
        try:
            if user_id:
                # User-specific analytics
                profile = self.user_profiles.get(user_id, UserPersonalizationProfile(user_id=user_id))
                
                # Find active session for this user
                active_session = None
                for session_id, context in self.active_sessions.items():
                    if context.user_id == user_id:
                        active_session = context
                        break
                
                return {
                    'user_specific': True,
                    'user_id': user_id,
                    'profile_confidence': profile.profile_confidence,
                    'total_interactions': profile.total_interactions,
                    'personalization_enabled': profile.personalization_enabled,
                    'preferences': {
                        'content_types': dict(profile.preferred_content_types),
                        'technologies': dict(profile.preferred_technologies),
                        'difficulty_levels': dict(profile.preferred_difficulty_levels),
                        'domains': dict(profile.preferred_domains)
                    },
                    'behavioral_patterns': {
                        'interaction_velocity': profile.interaction_velocity,
                        'exploration_tendency': profile.exploration_tendency,
                        'depth_vs_breadth': profile.depth_vs_breadth,
                        'theoretical_vs_practical': profile.theoretical_vs_practical
                    },
                    'temporal_patterns': dict(profile.activity_times),
                    'device_patterns': dict(profile.device_usage_patterns),
                    'active_session': {
                        'has_active_session': active_session is not None,
                        'session_duration': active_session.session_duration if active_session else 0,
                        'interactions_count': active_session.interactions_count if active_session else 0,
                        'current_context': {
                            'intent': active_session.current_intent if active_session else None,
                            'domain': active_session.current_domain if active_session else None,
                            'interaction_speed': active_session.interaction_speed if active_session else None
                        } if active_session else None
                    },
                    'last_update': profile.last_update.isoformat()
                }
            else:
                # Global analytics
                total_users = len(self.user_profiles)
                active_sessions_count = len(self.active_sessions)
                
                if self.user_profiles:
                    avg_confidence = np.mean([p.profile_confidence for p in self.user_profiles.values()])
                    avg_interactions = np.mean([p.total_interactions for p in self.user_profiles.values()])
                    enabled_personalization = sum(1 for p in self.user_profiles.values() if p.personalization_enabled)
                else:
                    avg_confidence = avg_interactions = enabled_personalization = 0
                
                return {
                    'user_specific': False,
                    'total_users_with_profiles': total_users,
                    'active_sessions': active_sessions_count,
                    'average_profile_confidence': avg_confidence,
                    'average_interactions_per_user': avg_interactions,
                    'users_with_personalization_enabled': enabled_personalization,
                    'personalization_config': {
                        'real_time_updates': self.config.enable_real_time_updates,
                        'min_interactions': self.config.min_interactions_for_personalization,
                        'learning_rate': self.config.personalization_learning_rate,
                        'confidence_threshold': self.config.confidence_threshold
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting personalization analytics: {e}")
            return {'error': str(e)}
    
    def update_user_personalization_settings(self, user_id: int, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's personalization settings"""
        try:
            profile = self.user_profiles[user_id]
            
            if 'personalization_enabled' in settings:
                profile.personalization_enabled = settings['personalization_enabled']
            
            if 'exploration_tendency' in settings:
                profile.exploration_tendency = max(0.0, min(1.0, settings['exploration_tendency']))
            
            if 'depth_vs_breadth' in settings:
                profile.depth_vs_breadth = max(0.0, min(1.0, settings['depth_vs_breadth']))
            
            if 'theoretical_vs_practical' in settings:
                profile.theoretical_vs_practical = max(0.0, min(1.0, settings['theoretical_vs_practical']))
            
            profile.last_update = datetime.now()
            
            return {
                'success': True,
                'message': f'Personalization settings updated for user {user_id}',
                'updated_settings': settings
            }
            
        except Exception as e:
            logger.error(f"Error updating personalization settings: {e}")
            return {'error': str(e)}
    
    def get_user_personalization_profile(self, user_id: int) -> Dict[str, Any]:
        """Get detailed user personalization profile"""
        try:
            profile = self.user_profiles[user_id]
            
            return {
                'user_id': user_id,
                'profile_summary': {
                    'confidence': profile.profile_confidence,
                    'total_interactions': profile.total_interactions,
                    'personalization_enabled': profile.personalization_enabled,
                    'last_update': profile.last_update.isoformat()
                },
                'preferences': {
                    'content_types': dict(sorted(profile.preferred_content_types.items(), 
                                                key=lambda x: x[1], reverse=True)),
                    'technologies': dict(sorted(profile.preferred_technologies.items(), 
                                               key=lambda x: x[1], reverse=True)),
                    'difficulty_levels': dict(sorted(profile.preferred_difficulty_levels.items(), 
                                                   key=lambda x: x[1], reverse=True)),
                    'domains': dict(sorted(profile.preferred_domains.items(), 
                                         key=lambda x: x[1], reverse=True))
                },
                'behavioral_patterns': {
                    'interaction_velocity': profile.interaction_velocity,
                    'exploration_tendency': profile.exploration_tendency,
                    'depth_vs_breadth': profile.depth_vs_breadth,
                    'theoretical_vs_practical': profile.theoretical_vs_practical,
                    'beginner_friendly_bias': profile.beginner_friendly_bias
                },
                'temporal_patterns': dict(profile.activity_times),
                'device_patterns': dict(profile.device_usage_patterns),
                'recent_interactions': len(profile.recent_interaction_patterns),
                'content_performance': len(self.content_performance.get(user_id, {}))
            }
            
        except Exception as e:
            logger.error(f"Error getting user personalization profile: {e}")
            return {'error': str(e)}

# Export main classes
__all__ = [
    'RealtimePersonalizationEngine',
    'PersonalizationContext',
    'UserPersonalizationProfile',
    'PersonalizationConfiguration'
]

if __name__ == "__main__":
    print("🎯 Real-time Personalization Engine")
    print("=" * 60)
    print("✅ Dynamic user profiling based on real-time interactions")
    print("✅ Context-aware personalization for recommendations")
    print("✅ Session-based personalization with immediate updates")
    print("✅ Multi-dimensional personalization (content, difficulty, technology)")
    print("✅ Adaptive learning with preference decay")
    print("=" * 60)
    print("🎯 Personalizes recommendations while processing ALL content!")
