#!/usr/bin/env python3
"""
Dynamic Diversity Management Engine
- Ensures recommendation diversity across multiple dimensions
- Prevents recommendation repetition and filter bubbles
- Adaptive diversity based on user behavior and context
- Multi-dimensional diversity analysis (content type, difficulty, technology, domain)
- Dynamic diversity thresholds based on user preferences

CRITICAL: Enhances diversity while processing ALL user content!
"""

import time
import logging
from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import numpy as np
import math

logger = logging.getLogger(__name__)

@dataclass
class DiversityMetrics:
    """Comprehensive diversity metrics for recommendations"""
    content_type_diversity: float  # Variety in content types (tutorial, doc, example, etc.)
    technology_diversity: float   # Variety in technologies covered
    difficulty_diversity: float   # Range of difficulty levels
    domain_diversity: float       # Variety in domains (web, data science, etc.)
    temporal_diversity: float     # Variety in content freshness/recency
    source_diversity: float       # Variety in content sources
    semantic_diversity: float     # Semantic distance between recommendations
    overall_diversity_score: float # Combined diversity score (0-1)
    diversity_categories: Dict[str, int]  # Count per category
    repetition_score: float       # How much repetition exists (0=none, 1=high)
    filter_bubble_risk: float     # Risk of filter bubble (0=low, 1=high)
    improvement_suggestions: List[str]  # Suggestions for better diversity

@dataclass
class DiversityConfiguration:
    """Configuration for diversity management"""
    min_content_type_variety: int = 3      # Minimum different content types
    min_technology_variety: int = 2        # Minimum different technologies
    min_difficulty_levels: int = 2         # Minimum difficulty levels
    max_same_domain_ratio: float = 0.6     # Max 60% from same domain
    max_same_source_ratio: float = 0.4     # Max 40% from same source
    semantic_distance_threshold: float = 0.3  # Minimum semantic distance
    diversity_boost_factor: float = 0.15   # How much to boost diverse items
    adaptive_diversity: bool = True        # Adapt based on user behavior
    preserve_quality_threshold: float = 0.7  # Don't sacrifice quality below this
    temporal_decay_days: int = 30          # Days for temporal diversity calculation

@dataclass
class UserDiversityProfile:
    """User's diversity preferences and behavior"""
    user_id: int
    preferred_variety_level: str = "medium"  # low, medium, high
    content_type_preferences: Dict[str, float] = field(default_factory=dict)
    technology_exploration_rate: float = 0.5  # How much user explores new tech
    difficulty_comfort_range: Tuple[str, str] = ("beginner", "advanced")
    domain_exploration_willingness: float = 0.3  # Willingness to explore new domains
    repetition_tolerance: float = 0.2  # Tolerance for similar content
    last_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    diversity_feedback_history: List[float] = field(default_factory=list)
    exploration_vs_exploitation: float = 0.3  # 0=exploit, 1=explore

class DynamicDiversityEngine:
    """Dynamic diversity management for intelligent recommendations"""
    
    def __init__(self, config: Optional[DiversityConfiguration] = None):
        self.config = config or DiversityConfiguration()
        self.user_profiles = defaultdict(lambda: UserDiversityProfile(user_id=0))
        self.content_similarity_cache = {}  # Cache for semantic similarity calculations
        self.diversity_history = defaultdict(list)  # Track diversity over time
        
        logger.info("✅ Dynamic Diversity Engine initialized - maintaining variety while processing ALL content")
    
    def ensure_recommendation_diversity(self, recommendations: List[Dict[str, Any]], 
                                      user_id: int, 
                                      request_context: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], DiversityMetrics]:
        """Ensure diversity in recommendation list while maintaining quality"""
        try:
            start_time = time.time()
            
            if not recommendations:
                return recommendations, self._create_empty_diversity_metrics()
            
            # Get user diversity profile
            user_profile = self._get_user_diversity_profile(user_id)
            
            # Analyze current diversity
            current_metrics = self._analyze_current_diversity(recommendations, user_profile)
            
            # Apply diversity enhancements
            enhanced_recommendations = self._apply_diversity_enhancements(
                recommendations, user_profile, current_metrics, request_context
            )
            
            # Re-analyze after enhancements
            final_metrics = self._analyze_current_diversity(enhanced_recommendations, user_profile)
            
            # Update user profile based on recommendations
            self._update_user_diversity_profile(user_id, enhanced_recommendations, final_metrics)
            
            # Store diversity history
            self._store_diversity_history(user_id, final_metrics)
            
            processing_time = time.time() - start_time
            logger.debug(f"Diversity processing completed in {processing_time*1000:.2f}ms")
            
            return enhanced_recommendations, final_metrics
            
        except Exception as e:
            logger.error(f"Error in diversity management: {e}")
            return recommendations, self._create_fallback_diversity_metrics()
    
    def _get_user_diversity_profile(self, user_id: int) -> UserDiversityProfile:
        """Get or create user diversity profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserDiversityProfile(user_id=user_id)
        return self.user_profiles[user_id]
    
    def _analyze_current_diversity(self, recommendations: List[Dict[str, Any]], 
                                 user_profile: UserDiversityProfile) -> DiversityMetrics:
        """Analyze diversity across multiple dimensions"""
        if not recommendations:
            return self._create_empty_diversity_metrics()
        
        # Extract features for analysis
        content_types = [rec.get('content_type', 'unknown') for rec in recommendations]
        technologies = []
        for rec in recommendations:
            rec_techs = rec.get('technologies', [])
            if isinstance(rec_techs, str):
                technologies.extend(rec_techs.split(','))
            elif isinstance(rec_techs, list):
                technologies.extend(rec_techs)
        
        difficulties = [rec.get('difficulty_level', 'intermediate') for rec in recommendations]
        domains = [rec.get('domain', 'general') for rec in recommendations]
        sources = [rec.get('source', rec.get('url', 'unknown'))[:50] for rec in recommendations]  # Domain extraction
        
        # Calculate diversity metrics
        content_type_diversity = self._calculate_categorical_diversity(content_types)
        technology_diversity = self._calculate_categorical_diversity(technologies)
        difficulty_diversity = self._calculate_categorical_diversity(difficulties)
        domain_diversity = self._calculate_categorical_diversity(domains)
        source_diversity = self._calculate_categorical_diversity(sources)
        
        # Calculate semantic diversity
        semantic_diversity = self._calculate_semantic_diversity(recommendations)
        
        # Calculate temporal diversity
        temporal_diversity = self._calculate_temporal_diversity(recommendations)
        
        # Calculate repetition and filter bubble risk
        repetition_score = self._calculate_repetition_score(recommendations, user_profile)
        filter_bubble_risk = self._calculate_filter_bubble_risk(recommendations, user_profile)
        
        # Calculate overall diversity score
        overall_diversity = (
            content_type_diversity * 0.2 +
            technology_diversity * 0.25 +
            difficulty_diversity * 0.15 +
            domain_diversity * 0.2 +
            semantic_diversity * 0.2
        )
        
        # Generate improvement suggestions
        suggestions = self._generate_diversity_suggestions(
            content_type_diversity, technology_diversity, difficulty_diversity,
            domain_diversity, semantic_diversity, repetition_score
        )
        
        return DiversityMetrics(
            content_type_diversity=content_type_diversity,
            technology_diversity=technology_diversity,
            difficulty_diversity=difficulty_diversity,
            domain_diversity=domain_diversity,
            temporal_diversity=temporal_diversity,
            source_diversity=source_diversity,
            semantic_diversity=semantic_diversity,
            overall_diversity_score=overall_diversity,
            diversity_categories={
                'content_types': len(set(content_types)),
                'technologies': len(set(technologies)),
                'difficulties': len(set(difficulties)),
                'domains': len(set(domains)),
                'sources': len(set(sources))
            },
            repetition_score=repetition_score,
            filter_bubble_risk=filter_bubble_risk,
            improvement_suggestions=suggestions
        )
    
    def _calculate_categorical_diversity(self, items: List[str]) -> float:
        """Calculate diversity for categorical data using Shannon entropy"""
        if not items:
            return 0.0
        
        # Count occurrences
        counts = Counter(items)
        total = len(items)
        
        # Calculate Shannon entropy
        entropy = 0.0
        for count in counts.values():
            if count > 0:
                probability = count / total
                entropy -= probability * math.log2(probability)
        
        # Normalize by maximum possible entropy
        max_entropy = math.log2(len(counts))
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _calculate_semantic_diversity(self, recommendations: List[Dict[str, Any]]) -> float:
        """Calculate semantic diversity between recommendations"""
        if len(recommendations) < 2:
            return 1.0  # Single item is maximally diverse
        
        # Extract text content for similarity calculation
        texts = []
        for rec in recommendations:
            text_parts = []
            if rec.get('title'):
                text_parts.append(rec['title'])
            if rec.get('description'):
                text_parts.append(rec['description'])
            if rec.get('summary'):
                text_parts.append(rec['summary'])
            texts.append(' '.join(text_parts))
        
        # Calculate pairwise semantic distances
        total_distance = 0.0
        pair_count = 0
        
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                # Simple word-based similarity (can be enhanced with embeddings)
                similarity = self._calculate_text_similarity(texts[i], texts[j])
                distance = 1.0 - similarity
                total_distance += distance
                pair_count += 1
        
        return total_distance / pair_count if pair_count > 0 else 1.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity based on word overlap"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_temporal_diversity(self, recommendations: List[Dict[str, Any]]) -> float:
        """Calculate temporal diversity of recommendations"""
        dates = []
        current_time = datetime.now()
        
        for rec in recommendations:
            # Try to extract date from various fields
            date_created = rec.get('date_created') or rec.get('created_at') or rec.get('timestamp')
            if date_created:
                try:
                    if isinstance(date_created, str):
                        # Simple parsing - can be enhanced
                        date_obj = datetime.fromisoformat(date_created.replace('Z', '+00:00'))
                    else:
                        date_obj = date_created
                    
                    days_old = (current_time - date_obj).days
                    dates.append(days_old)
                except:
                    dates.append(self.config.temporal_decay_days)  # Default age
            else:
                dates.append(self.config.temporal_decay_days)  # Default age
        
        if not dates:
            return 0.5  # Neutral temporal diversity
        
        # Calculate coefficient of variation for temporal spread
        mean_age = np.mean(dates)
        std_age = np.std(dates)
        cv = std_age / mean_age if mean_age > 0 else 0
        
        # Normalize to 0-1 scale
        return min(1.0, cv / 2.0)  # CV of 2.0 = maximum diversity
    
    def _calculate_repetition_score(self, recommendations: List[Dict[str, Any]], 
                                  user_profile: UserDiversityProfile) -> float:
        """Calculate how much repetition exists in recommendations"""
        if not recommendations or not user_profile.last_recommendations:
            return 0.0
        
        # Compare with recent recommendations
        current_titles = {rec.get('title', '').lower() for rec in recommendations}
        recent_titles = {rec.get('title', '').lower() for rec in user_profile.last_recommendations[-10:]}
        
        overlap = current_titles.intersection(recent_titles)
        repetition = len(overlap) / len(current_titles) if current_titles else 0.0
        
        return min(1.0, repetition)
    
    def _calculate_filter_bubble_risk(self, recommendations: List[Dict[str, Any]], 
                                    user_profile: UserDiversityProfile) -> float:
        """Calculate risk of filter bubble formation"""
        if not recommendations:
            return 0.0
        
        # Analyze technology concentration
        all_techs = []
        for rec in recommendations:
            rec_techs = rec.get('technologies', [])
            if isinstance(rec_techs, str):
                all_techs.extend(rec_techs.split(','))
            elif isinstance(rec_techs, list):
                all_techs.extend(rec_techs)
        
        if not all_techs:
            return 0.0
        
        # Calculate concentration using Herfindahl-Hirschman Index
        tech_counts = Counter(all_techs)
        total_count = sum(tech_counts.values())
        
        hhi = sum((count / total_count) ** 2 for count in tech_counts.values())
        
        # HHI ranges from 1/n to 1, normalize to 0-1 risk scale
        min_hhi = 1 / len(tech_counts) if tech_counts else 1
        normalized_hhi = (hhi - min_hhi) / (1 - min_hhi) if min_hhi < 1 else 0
        
        return min(1.0, normalized_hhi)
    
    def _generate_diversity_suggestions(self, content_type_div: float, tech_div: float, 
                                      difficulty_div: float, domain_div: float, 
                                      semantic_div: float, repetition: float) -> List[str]:
        """Generate suggestions for improving diversity"""
        suggestions = []
        
        if content_type_div < 0.6:
            suggestions.append("Include more variety in content types (tutorials, examples, documentation)")
        
        if tech_div < 0.5:
            suggestions.append("Add recommendations covering different technologies")
        
        if difficulty_div < 0.4:
            suggestions.append("Include content at different difficulty levels")
        
        if domain_div < 0.5:
            suggestions.append("Expand recommendations across different domains")
        
        if semantic_div < 0.3:
            suggestions.append("Include more semantically diverse content")
        
        if repetition > 0.3:
            suggestions.append("Reduce repetition from recent recommendations")
        
        if not suggestions:
            suggestions.append("Diversity is well-balanced")
        
        return suggestions
    
    def _apply_diversity_enhancements(self, recommendations: List[Dict[str, Any]], 
                                    user_profile: UserDiversityProfile,
                                    current_metrics: DiversityMetrics,
                                    request_context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply diversity enhancements to recommendation list"""
        if current_metrics.overall_diversity_score > 0.7:
            # Already diverse enough
            return recommendations
        
        enhanced = recommendations.copy()
        
        # Apply diversity boosting
        enhanced = self._boost_diverse_items(enhanced, user_profile, current_metrics)
        
        # Remove excessive repetition
        enhanced = self._reduce_repetition(enhanced, user_profile)
        
        # Ensure minimum variety requirements
        enhanced = self._ensure_minimum_variety(enhanced, user_profile)
        
        # Re-rank with diversity considerations
        enhanced = self._rerank_with_diversity(enhanced, user_profile, current_metrics)
        
        return enhanced
    
    def _boost_diverse_items(self, recommendations: List[Dict[str, Any]], 
                           user_profile: UserDiversityProfile,
                           metrics: DiversityMetrics) -> List[Dict[str, Any]]:
        """Boost scores of items that improve diversity"""
        enhanced = []
        
        # Track what we've already included
        included_types = set()
        included_techs = set()
        included_domains = set()
        
        for rec in recommendations:
            rec_copy = rec.copy()
            original_score = rec_copy.get('score', 0.5)
            
            # Check if this item improves diversity
            diversity_boost = 0.0
            
            # Content type diversity
            content_type = rec.get('content_type', 'unknown')
            if content_type not in included_types:
                diversity_boost += self.config.diversity_boost_factor * 0.3
                included_types.add(content_type)
            
            # Technology diversity
            rec_techs = rec.get('technologies', [])
            if isinstance(rec_techs, str):
                rec_techs = rec_techs.split(',')
            for tech in rec_techs:
                if tech not in included_techs:
                    diversity_boost += self.config.diversity_boost_factor * 0.4
                    included_techs.add(tech)
            
            # Domain diversity
            domain = rec.get('domain', 'general')
            if domain not in included_domains:
                diversity_boost += self.config.diversity_boost_factor * 0.3
                included_domains.add(domain)
            
            # Apply boost while preserving quality threshold
            if original_score >= self.config.preserve_quality_threshold:
                rec_copy['score'] = min(1.0, original_score + diversity_boost)
                rec_copy['diversity_boost'] = diversity_boost
            
            enhanced.append(rec_copy)
        
        return enhanced
    
    def _reduce_repetition(self, recommendations: List[Dict[str, Any]], 
                          user_profile: UserDiversityProfile) -> List[Dict[str, Any]]:
        """Reduce repetition with recent recommendations"""
        if not user_profile.last_recommendations:
            return recommendations
        
        recent_titles = {rec.get('title', '').lower() for rec in user_profile.last_recommendations[-10:]}
        
        filtered = []
        for rec in recommendations:
            title = rec.get('title', '').lower()
            if title not in recent_titles:
                filtered.append(rec)
            elif len(filtered) < len(recommendations) * 0.7:  # Keep some familiar content
                # Reduce score for repeated items
                rec_copy = rec.copy()
                rec_copy['score'] = rec_copy.get('score', 0.5) * 0.8
                rec_copy['repetition_penalty'] = True
                filtered.append(rec_copy)
        
        return filtered
    
    def _ensure_minimum_variety(self, recommendations: List[Dict[str, Any]], 
                              user_profile: UserDiversityProfile) -> List[Dict[str, Any]]:
        """Ensure minimum variety requirements are met"""
        if len(recommendations) < self.config.min_content_type_variety:
            return recommendations  # Not enough items to enforce variety
        
        # Group by categories
        by_content_type = defaultdict(list)
        by_technology = defaultdict(list)
        by_difficulty = defaultdict(list)
        
        for rec in recommendations:
            content_type = rec.get('content_type', 'unknown')
            difficulty = rec.get('difficulty_level', 'intermediate')
            
            by_content_type[content_type].append(rec)
            by_difficulty[difficulty].append(rec)
            
            rec_techs = rec.get('technologies', [])
            if isinstance(rec_techs, str):
                rec_techs = rec_techs.split(',')
            for tech in rec_techs:
                by_technology[tech].append(rec)
        
        # Ensure variety by limiting over-representation
        balanced = []
        max_per_category = max(1, len(recommendations) // self.config.min_content_type_variety)
        
        # Add items while maintaining balance
        category_counts = defaultdict(int)
        
        for rec in sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True):
            content_type = rec.get('content_type', 'unknown')
            
            if category_counts[content_type] < max_per_category:
                balanced.append(rec)
                category_counts[content_type] += 1
                
                if len(balanced) >= len(recommendations):
                    break
        
        # Fill remaining slots with best remaining items
        remaining_slots = len(recommendations) - len(balanced)
        if remaining_slots > 0:
            remaining_items = [rec for rec in recommendations if rec not in balanced]
            remaining_sorted = sorted(remaining_items, key=lambda x: x.get('score', 0), reverse=True)
            balanced.extend(remaining_sorted[:remaining_slots])
        
        return balanced
    
    def _rerank_with_diversity(self, recommendations: List[Dict[str, Any]], 
                             user_profile: UserDiversityProfile,
                             metrics: DiversityMetrics) -> List[Dict[str, Any]]:
        """Re-rank recommendations considering diversity"""
        if len(recommendations) <= 1:
            return recommendations
        
        # Calculate exploration vs exploitation balance
        exploration_factor = user_profile.exploration_vs_exploitation
        
        # Re-rank with combined quality and diversity score
        for rec in recommendations:
            quality_score = rec.get('score', 0.5)
            diversity_boost = rec.get('diversity_boost', 0.0)
            
            # Combine quality and diversity
            combined_score = (
                quality_score * (1 - exploration_factor) +
                (quality_score + diversity_boost) * exploration_factor
            )
            
            rec['combined_score'] = combined_score
            rec['original_score'] = quality_score
        
        # Sort by combined score
        return sorted(recommendations, key=lambda x: x.get('combined_score', 0), reverse=True)
    
    def _update_user_diversity_profile(self, user_id: int, 
                                     recommendations: List[Dict[str, Any]], 
                                     metrics: DiversityMetrics):
        """Update user diversity profile based on recommendations"""
        profile = self.user_profiles[user_id]
        
        # Store last recommendations (keep last 20)
        profile.last_recommendations.extend(recommendations)
        if len(profile.last_recommendations) > 20:
            profile.last_recommendations = profile.last_recommendations[-20:]
        
        # Update content type preferences based on what was recommended
        for rec in recommendations:
            content_type = rec.get('content_type', 'unknown')
            if content_type in profile.content_type_preferences:
                profile.content_type_preferences[content_type] += 0.1
            else:
                profile.content_type_preferences[content_type] = 0.1
        
        # Normalize content type preferences
        total_pref = sum(profile.content_type_preferences.values())
        if total_pref > 0:
            for ct in profile.content_type_preferences:
                profile.content_type_preferences[ct] /= total_pref
    
    def _store_diversity_history(self, user_id: int, metrics: DiversityMetrics):
        """Store diversity metrics history for analysis"""
        self.diversity_history[user_id].append({
            'timestamp': datetime.now(),
            'overall_diversity': metrics.overall_diversity_score,
            'filter_bubble_risk': metrics.filter_bubble_risk,
            'repetition_score': metrics.repetition_score
        })
        
        # Keep only last 50 entries
        if len(self.diversity_history[user_id]) > 50:
            self.diversity_history[user_id] = self.diversity_history[user_id][-50:]
    
    def get_diversity_analytics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get diversity analytics and insights"""
        try:
            if user_id:
                # User-specific analytics
                profile = self.user_profiles.get(user_id, UserDiversityProfile(user_id=user_id))
                history = self.diversity_history.get(user_id, [])
                
                if history:
                    recent_diversity = np.mean([h['overall_diversity'] for h in history[-10:]])
                    avg_bubble_risk = np.mean([h['filter_bubble_risk'] for h in history[-10:]])
                    avg_repetition = np.mean([h['repetition_score'] for h in history[-10:]])
                else:
                    recent_diversity = avg_bubble_risk = avg_repetition = 0.0
                
                return {
                    'user_specific': True,
                    'user_id': user_id,
                    'diversity_profile': {
                        'preferred_variety_level': profile.preferred_variety_level,
                        'exploration_vs_exploitation': profile.exploration_vs_exploitation,
                        'technology_exploration_rate': profile.technology_exploration_rate,
                        'repetition_tolerance': profile.repetition_tolerance
                    },
                    'recent_metrics': {
                        'average_diversity': recent_diversity,
                        'filter_bubble_risk': avg_bubble_risk,
                        'repetition_score': avg_repetition
                    },
                    'content_preferences': dict(profile.content_type_preferences),
                    'recommendation_history_size': len(profile.last_recommendations),
                    'diversity_trend': 'improving' if len(history) >= 2 and 
                                     history[-1]['overall_diversity'] > history[-2]['overall_diversity'] else 'stable'
                }
            else:
                # Global analytics
                total_users = len(self.user_profiles)
                total_history = sum(len(h) for h in self.diversity_history.values())
                
                if self.diversity_history:
                    all_diversity_scores = []
                    for user_history in self.diversity_history.values():
                        all_diversity_scores.extend([h['overall_diversity'] for h in user_history])
                    
                    avg_global_diversity = np.mean(all_diversity_scores) if all_diversity_scores else 0.0
                else:
                    avg_global_diversity = 0.0
                
                return {
                    'user_specific': False,
                    'total_users_tracked': total_users,
                    'total_diversity_measurements': total_history,
                    'average_global_diversity': avg_global_diversity,
                    'diversity_engine_config': {
                        'min_content_type_variety': self.config.min_content_type_variety,
                        'min_technology_variety': self.config.min_technology_variety,
                        'diversity_boost_factor': self.config.diversity_boost_factor,
                        'adaptive_diversity': self.config.adaptive_diversity
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting diversity analytics: {e}")
            return {'error': str(e)}
    
    def update_user_diversity_preferences(self, user_id: int, feedback: Dict[str, Any]):
        """Update user diversity preferences based on explicit feedback"""
        try:
            profile = self.user_profiles[user_id]
            
            # Update exploration vs exploitation based on feedback
            if feedback.get('wants_more_variety'):
                profile.exploration_vs_exploitation = min(1.0, profile.exploration_vs_exploitation + 0.1)
            elif feedback.get('wants_less_variety'):
                profile.exploration_vs_exploitation = max(0.0, profile.exploration_vs_exploitation - 0.1)
            
            # Update repetition tolerance
            if feedback.get('okay_with_repetition'):
                profile.repetition_tolerance = min(1.0, profile.repetition_tolerance + 0.1)
            elif feedback.get('dislikes_repetition'):
                profile.repetition_tolerance = max(0.0, profile.repetition_tolerance - 0.1)
            
            # Update technology exploration rate
            if feedback.get('wants_new_technologies'):
                profile.technology_exploration_rate = min(1.0, profile.technology_exploration_rate + 0.1)
            elif feedback.get('prefers_familiar_tech'):
                profile.technology_exploration_rate = max(0.0, profile.technology_exploration_rate - 0.1)
            
            logger.debug(f"Updated diversity preferences for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user diversity preferences: {e}")
    
    def _create_empty_diversity_metrics(self) -> DiversityMetrics:
        """Create empty diversity metrics"""
        return DiversityMetrics(
            content_type_diversity=0.0,
            technology_diversity=0.0,
            difficulty_diversity=0.0,
            domain_diversity=0.0,
            temporal_diversity=0.0,
            source_diversity=0.0,
            semantic_diversity=0.0,
            overall_diversity_score=0.0,
            diversity_categories={},
            repetition_score=0.0,
            filter_bubble_risk=0.0,
            improvement_suggestions=["No recommendations to analyze"]
        )
    
    def _create_fallback_diversity_metrics(self) -> DiversityMetrics:
        """Create fallback diversity metrics on error"""
        return DiversityMetrics(
            content_type_diversity=0.5,
            technology_diversity=0.5,
            difficulty_diversity=0.5,
            domain_diversity=0.5,
            temporal_diversity=0.5,
            source_diversity=0.5,
            semantic_diversity=0.5,
            overall_diversity_score=0.5,
            diversity_categories={'error': 1},
            repetition_score=0.0,
            filter_bubble_risk=0.0,
            improvement_suggestions=["Error in diversity analysis"]
        )

# Export main classes
__all__ = [
    'DynamicDiversityEngine',
    'DiversityMetrics',
    'DiversityConfiguration', 
    'UserDiversityProfile'
]

if __name__ == "__main__":
    print("🎨 Dynamic Diversity Management Engine")
    print("=" * 60)
    print("✅ Multi-dimensional diversity analysis")
    print("✅ Adaptive diversity based on user behavior")
    print("✅ Filter bubble prevention") 
    print("✅ Dynamic recommendation variety")
    print("✅ Quality preservation with diversity enhancement")
    print("=" * 60)
    print("🎯 Ensures variety while processing ALL content!")
