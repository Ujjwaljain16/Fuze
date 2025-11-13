"""
User Feedback Learning System
==============================
Tracks user interactions and learns preferences over time.
Self-improving recommendation system!

Features:
- Track clicks, saves, dismissals
- Learn user preferences
- Personalized scoring weights
- Adaptive recommendations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class UserFeedbackLearner:
    """Learns from user feedback to improve recommendations"""
    
    def __init__(self):
        self.feedback_cache = {}  # In-memory cache for fast access
        logger.info("User Feedback Learner initialized")
    
    # ============================================================================
    # FEEDBACK TRACKING
    # ============================================================================
    
    def record_feedback(self, user_id: int, content_id: int, recommendation_id: Optional[int],
                       feedback_type: str, context: Dict = None) -> bool:
        """
        Record user feedback on a recommendation
        
        Args:
            user_id: User ID
            content_id: Content ID
            recommendation_id: Recommendation session ID (optional)
            feedback_type: 'clicked', 'saved', 'dismissed', 'not_relevant', 'helpful', 'completed'
            context: Additional context (project_id, query, etc.)
        
        Returns:
            Success status
        """
        try:
            from models import db, UserFeedback
            from flask import current_app
            
            # Create feedback record
            feedback = UserFeedback(
                user_id=user_id,
                content_id=content_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                context_data=context or {},
                timestamp=datetime.utcnow()
            )
            
            db.session.add(feedback)
            db.session.commit()
            
            # Clear cache for this user to force recomputation
            cache_key = f"user_prefs_{user_id}"
            if cache_key in self.feedback_cache:
                del self.feedback_cache[cache_key]
            
            logger.info(f"Recorded {feedback_type} feedback for user {user_id}, content {content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
            return False
    
    # ============================================================================
    # PREFERENCE LEARNING
    # ============================================================================
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        Learn user preferences from feedback history
        
        Returns:
            {
                'preferred_content_types': {'tutorial': 0.8, 'article': 0.5},
                'preferred_difficulties': {'intermediate': 0.9, 'advanced': 0.3},
                'preferred_technologies': {'python': 0.9, 'javascript': 0.7},
                'weight_adjustments': {'technology': 1.2, 'semantic': 0.8},
                'quality_threshold': 7,
                'interaction_count': 50
            }
        """
        cache_key = f"user_prefs_{user_id}"
        
        # Check cache
        if cache_key in self.feedback_cache:
            cached = self.feedback_cache[cache_key]
            if (datetime.utcnow() - cached['timestamp']).seconds < 300:  # 5 min cache
                return cached['preferences']
        
        try:
            from models import db, UserFeedback, SavedContent, ContentAnalysis
            from sqlalchemy import func
            
            # Get feedback history (last 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            feedback_query = db.session.query(
                UserFeedback, SavedContent, ContentAnalysis
            ).join(
                SavedContent, UserFeedback.content_id == SavedContent.id
            ).outerjoin(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            ).filter(
                UserFeedback.user_id == user_id,
                UserFeedback.timestamp >= cutoff_date
            ).all()
            
            # Analyze feedback patterns
            preferences = self._analyze_feedback_patterns(feedback_query)
            
            # Cache results
            self.feedback_cache[cache_key] = {
                'preferences': preferences,
                'timestamp': datetime.utcnow()
            }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return self._get_default_preferences()
    
    def _analyze_feedback_patterns(self, feedback_data: List) -> Dict:
        """Analyze feedback data to extract preferences"""
        
        # Counters for different preferences
        content_type_scores = defaultdict(lambda: {'positive': 0, 'negative': 0})
        difficulty_scores = defaultdict(lambda: {'positive': 0, 'negative': 0})
        tech_scores = defaultdict(lambda: {'positive': 0, 'negative': 0})
        quality_scores = []
        
        total_interactions = len(feedback_data)
        
        for feedback, content, analysis in feedback_data:
            # Determine if positive or negative feedback
            is_positive = feedback.feedback_type in ['clicked', 'saved', 'helpful', 'completed']
            is_negative = feedback.feedback_type in ['dismissed', 'not_relevant']
            
            score_key = 'positive' if is_positive else 'negative' if is_negative else None
            
            if score_key and analysis:
                # Content type preferences
                if analysis.content_type:
                    content_type_scores[analysis.content_type][score_key] += 1
                
                # Difficulty preferences
                if analysis.difficulty_level:
                    difficulty_scores[analysis.difficulty_level][score_key] += 1
                
                # Technology preferences
                if analysis.technology_tags:
                    techs = [t.strip() for t in analysis.technology_tags.split(',')]
                    for tech in techs:
                        if tech:
                            tech_scores[tech.lower()][score_key] += 1
                
                # Quality tracking
                if is_positive and content.quality_score:
                    quality_scores.append(content.quality_score)
        
        # Calculate preference scores (0-1 scale)
        preferred_content_types = self._calculate_preference_scores(content_type_scores)
        preferred_difficulties = self._calculate_preference_scores(difficulty_scores)
        preferred_technologies = self._calculate_preference_scores(tech_scores)
        
        # Calculate weight adjustments based on what matters most to user
        weight_adjustments = self._calculate_weight_adjustments(
            content_type_scores, difficulty_scores, tech_scores
        )
        
        # Average quality of content user engages with
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 6
        quality_threshold = max(3, int(avg_quality * 0.8))  # 80% of their average
        
        return {
            'preferred_content_types': preferred_content_types,
            'preferred_difficulties': preferred_difficulties,
            'preferred_technologies': preferred_technologies,
            'weight_adjustments': weight_adjustments,
            'quality_threshold': quality_threshold,
            'interaction_count': total_interactions,
            'avg_quality_engaged': avg_quality
        }
    
    def _calculate_preference_scores(self, score_dict: Dict) -> Dict[str, float]:
        """Calculate preference scores from positive/negative counts"""
        preferences = {}
        
        for item, scores in score_dict.items():
            positive = scores['positive']
            negative = scores['negative']
            total = positive + negative
            
            if total > 0:
                # Score = (positive - negative) / total, normalized to 0-1
                score = (positive - negative) / total
                score = (score + 1) / 2  # Normalize to 0-1
                preferences[item] = score
        
        return preferences
    
    def _calculate_weight_adjustments(self, content_scores, difficulty_scores, 
                                     tech_scores) -> Dict[str, float]:
        """Calculate how much to adjust scoring weights based on user behavior"""
        
        # Count how much user cares about each dimension
        content_importance = sum(s['positive'] + s['negative'] 
                               for s in content_scores.values())
        difficulty_importance = sum(s['positive'] + s['negative'] 
                                  for s in difficulty_scores.values())
        tech_importance = sum(s['positive'] + s['negative'] 
                            for s in tech_scores.values())
        
        total = content_importance + difficulty_importance + tech_importance
        
        if total == 0:
            return {'technology': 1.0, 'semantic': 1.0, 'content_type': 1.0, 'difficulty': 1.0}
        
        # Normalize to 0.8-1.2 range (boost what matters, reduce what doesn't)
        adjustments = {
            'technology': 0.8 + (tech_importance / total) * 0.8,
            'content_type': 0.8 + (content_importance / total) * 0.8,
            'difficulty': 0.8 + (difficulty_importance / total) * 0.8,
            'semantic': 1.0  # Keep semantic constant as baseline
        }
        
        return adjustments
    
    def _get_default_preferences(self) -> Dict:
        """Default preferences for new users"""
        return {
            'preferred_content_types': {},
            'preferred_difficulties': {},
            'preferred_technologies': {},
            'weight_adjustments': {
                'technology': 1.0,
                'semantic': 1.0,
                'content_type': 1.0,
                'difficulty': 1.0
            },
            'quality_threshold': 5,
            'interaction_count': 0,
            'avg_quality_engaged': 6
        }
    
    # ============================================================================
    # APPLY PERSONALIZATION
    # ============================================================================
    
    def apply_personalization(self, recommendations: List[Dict], 
                            user_preferences: Dict) -> List[Dict]:
        """
        Apply learned preferences to boost/demote recommendations
        
        Args:
            recommendations: List of recommendation dicts with scores
            user_preferences: User preferences from get_user_preferences()
        
        Returns:
            Adjusted recommendations
        """
        if user_preferences['interaction_count'] < 5:
            # Not enough data, return as-is
            return recommendations
        
        adjusted_recs = []
        
        for rec in recommendations:
            # Start with original score
            adjusted_score = rec.get('score', 0.5)
            
            # Content type preference
            content_type = rec.get('content_type', '').lower()
            if content_type in user_preferences['preferred_content_types']:
                content_pref = user_preferences['preferred_content_types'][content_type]
                # Boost/demote by up to ±15%
                adjusted_score *= (0.85 + content_pref * 0.3)
            
            # Difficulty preference
            difficulty = rec.get('difficulty', '').lower()
            if difficulty in user_preferences['preferred_difficulties']:
                diff_pref = user_preferences['preferred_difficulties'][difficulty]
                # Boost/demote by up to ±10%
                adjusted_score *= (0.90 + diff_pref * 0.2)
            
            # Technology preference
            technologies = rec.get('technologies', [])
            if technologies:
                tech_boost = 0
                matched_techs = 0
                
                for tech in technologies:
                    tech_lower = tech.lower()
                    if tech_lower in user_preferences['preferred_technologies']:
                        tech_pref = user_preferences['preferred_technologies'][tech_lower]
                        tech_boost += tech_pref
                        matched_techs += 1
                
                if matched_techs > 0:
                    avg_tech_pref = tech_boost / matched_techs
                    # Boost by up to +20%
                    adjusted_score *= (1.0 + avg_tech_pref * 0.2)
            
            # Cap at 1.0
            adjusted_score = min(1.0, adjusted_score)
            
            # Update recommendation
            rec_copy = rec.copy()
            rec_copy['score'] = adjusted_score
            rec_copy['original_score'] = rec.get('score', 0.5)
            rec_copy['personalized'] = True
            
            adjusted_recs.append(rec_copy)
        
        # Re-sort by adjusted scores
        adjusted_recs.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Applied personalization to {len(adjusted_recs)} recommendations")
        return adjusted_recs
    
    # ============================================================================
    # STATISTICS & INSIGHTS
    # ============================================================================
    
    def get_user_insights(self, user_id: int) -> Dict:
        """Get insights about user's learning patterns"""
        try:
            preferences = self.get_user_preferences(user_id)
            
            # Find top preferences
            top_content_types = sorted(
                preferences['preferred_content_types'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            top_technologies = sorted(
                preferences['preferred_technologies'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            insights = {
                'total_interactions': preferences['interaction_count'],
                'favorite_content_types': [ct for ct, _ in top_content_types],
                'favorite_technologies': [tech for tech, _ in top_technologies],
                'preferred_difficulty': max(
                    preferences['preferred_difficulties'].items(),
                    key=lambda x: x[1],
                    default=('intermediate', 0.5)
                )[0] if preferences['preferred_difficulties'] else 'intermediate',
                'quality_bar': preferences['quality_threshold'],
                'learning_style': self._infer_learning_style(preferences)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting user insights: {e}")
            return {}
    
    def _infer_learning_style(self, preferences: Dict) -> str:
        """Infer user's learning style from preferences"""
        content_prefs = preferences['preferred_content_types']
        
        if content_prefs.get('tutorial', 0) > 0.7:
            return "hands-on learner (prefers tutorials)"
        elif content_prefs.get('documentation', 0) > 0.7:
            return "reference-oriented (prefers docs)"
        elif content_prefs.get('video', 0) > 0.7:
            return "visual learner (prefers videos)"
        elif content_prefs.get('article', 0) > 0.7:
            return "reading learner (prefers articles)"
        else:
            return "balanced learner"


# Global instance
_feedback_learner = None

def get_feedback_learner() -> UserFeedbackLearner:
    """Get or create global feedback learner instance"""
    global _feedback_learner
    if _feedback_learner is None:
        _feedback_learner = UserFeedbackLearner()
    return _feedback_learner

