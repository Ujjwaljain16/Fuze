#!/usr/bin/env python3
"""
Adaptive Scoring Engine for Dynamic Recommendation Scoring
Implements context-aware weights and intelligent penalties
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import math

logger = logging.getLogger(__name__)

class ContextType(Enum):
    """Different types of recommendation contexts"""
    LEARNING = "learning"
    PROJECT = "project"
    TASK = "task"
    GENERAL = "general"
    RESEARCH = "research"
    PRACTICE = "practice"

class UserIntent(Enum):
    """User intent types for adaptive scoring"""
    LEARN_NEW = "learn_new"
    IMPROVE_SKILLS = "improve_skills"
    SOLVE_PROBLEM = "solve_problem"
    BUILD_PROJECT = "build_project"
    RESEARCH_TOPIC = "research_topic"
    PRACTICE_CONCEPTS = "practice_concepts"

class AdaptiveScoringEngine:
    """
    Adaptive scoring engine with dynamic weights and context-aware penalties
    """
    
    def __init__(self):
        # Base weights for different scoring components
        self.base_weights = {
            'tech_match': 0.35,
            'content_relevance': 0.25,
            'difficulty_alignment': 0.15,
            'intent_alignment': 0.15,
            'semantic_similarity': 0.10
        }
        
        # Context-specific weight adjustments
        self.context_adjustments = {
            ContextType.LEARNING: {
                'difficulty_alignment': 0.25,  # Increase difficulty importance for learning
                'tech_match': 0.25,           # Reduce tech match for learning
                'content_relevance': 0.20,    # Slightly reduce content relevance
                'intent_alignment': 0.20,     # Increase intent alignment
                'semantic_similarity': 0.10   # Keep semantic similarity
            },
            ContextType.PROJECT: {
                'tech_match': 0.40,           # Increase tech match for projects
                'content_relevance': 0.30,    # Increase content relevance
                'difficulty_alignment': 0.10, # Reduce difficulty importance
                'intent_alignment': 0.15,     # Keep intent alignment
                'semantic_similarity': 0.05   # Reduce semantic similarity
            },
            ContextType.TASK: {
                'tech_match': 0.45,           # High tech match for tasks
                'content_relevance': 0.25,    # Good content relevance
                'difficulty_alignment': 0.10, # Lower difficulty importance
                'intent_alignment': 0.15,     # Keep intent alignment
                'semantic_similarity': 0.05   # Lower semantic similarity
            },
            ContextType.RESEARCH: {
                'semantic_similarity': 0.35,  # High semantic similarity for research
                'content_relevance': 0.30,    # High content relevance
                'tech_match': 0.20,           # Lower tech match
                'difficulty_alignment': 0.10, # Lower difficulty importance
                'intent_alignment': 0.05      # Lower intent alignment
            },
            ContextType.PRACTICE: {
                'difficulty_alignment': 0.30, # High difficulty alignment for practice
                'tech_match': 0.25,           # Good tech match
                'content_relevance': 0.20,    # Good content relevance
                'intent_alignment': 0.15,     # Keep intent alignment
                'semantic_similarity': 0.10   # Keep semantic similarity
            }
        }
        
        # Skill level adjustments
        self.skill_level_adjustments = {
            'beginner': {
                'difficulty_alignment': 1.2,  # Increase difficulty importance for beginners
                'tech_match': 0.8,           # Reduce tech match importance
                'content_relevance': 1.1,    # Slightly increase content relevance
                'intent_alignment': 1.1,     # Slightly increase intent alignment
                'semantic_similarity': 0.9   # Slightly reduce semantic similarity
            },
            'intermediate': {
                'difficulty_alignment': 1.0,  # Normal weights for intermediates
                'tech_match': 1.0,
                'content_relevance': 1.0,
                'intent_alignment': 1.0,
                'semantic_similarity': 1.0
            },
            'advanced': {
                'difficulty_alignment': 0.8,  # Reduce difficulty importance for advanced users
                'tech_match': 1.2,           # Increase tech match importance
                'content_relevance': 0.9,    # Slightly reduce content relevance
                'intent_alignment': 0.9,     # Slightly reduce intent alignment
                'semantic_similarity': 1.1   # Increase semantic similarity
            }
        }
        
        # Penalty thresholds
        self.penalty_thresholds = {
            'tech_match': 0.1,      # Very low tech match
            'semantic_similarity': 0.2,  # Very low semantic similarity
            'content_relevance': 0.15,   # Very low content relevance
            'difficulty_alignment': 0.2,  # Very low difficulty alignment
            'intent_alignment': 0.15     # Very low intent alignment
        }
        
        # Penalty multipliers
        self.penalty_multipliers = {
            'irrelevant_content': 0.5,    # 50% penalty for irrelevant content
            'skill_mismatch': 0.7,        # 30% penalty for skill mismatch
            'context_mismatch': 0.8,      # 20% penalty for context mismatch
            'quality_penalty': 0.9        # 10% penalty for low quality
        }
    
    def calculate_adaptive_score(self, bookmark: Dict, context: Dict) -> Dict[str, Any]:
        """
        Calculate adaptive recommendation score with dynamic weights and penalties
        
        Args:
            bookmark: Content bookmark with analysis data
            context: User context including intent, skill level, etc.
            
        Returns:
            Dict containing scores, weights, penalties, and final score
        """
        try:
            # Determine context type and user intent
            context_type = self._determine_context_type(context)
            user_intent = self._determine_user_intent(context)
            user_skill_level = context.get('skill_level', 'intermediate')
            
            # Get dynamic weights based on context and user profile
            dynamic_weights = self._get_dynamic_weights(context_type, user_intent, user_skill_level)
            
            # Calculate individual component scores
            component_scores = self._calculate_component_scores(bookmark, context)
            
            # Apply weights to component scores
            weighted_scores = self._apply_weights(component_scores, dynamic_weights)
            
            # Calculate total score
            total_score = sum(weighted_scores.values())
            
            # Apply penalties for irrelevant content
            penalties = self._calculate_penalties(component_scores, context)
            final_score = self._apply_penalties(total_score, penalties)
            
            return {
                'final_score': final_score,
                'component_scores': component_scores,
                'weighted_scores': weighted_scores,
                'dynamic_weights': dynamic_weights,
                'penalties': penalties,
                'context_type': context_type.value,
                'user_intent': user_intent.value,
                'reasoning': self._generate_adaptive_reasoning(component_scores, penalties, context_type, user_intent)
            }
            
        except Exception as e:
            logger.error(f"Error in adaptive scoring: {e}")
            return {
                'final_score': 0.0,
                'component_scores': {},
                'weighted_scores': {},
                'dynamic_weights': self.base_weights,
                'penalties': {},
                'context_type': 'general',
                'user_intent': 'general',
                'reasoning': f"Scoring error: {str(e)}"
            }
    
    def _determine_context_type(self, context: Dict) -> ContextType:
        """Determine the context type based on user input and profile"""
        # Check for explicit context type
        if context.get('context_type'):
            try:
                return ContextType(context['context_type'])
            except ValueError:
                pass
        
        # Infer from user input
        user_input = context.get('user_input', {})
        project_id = context.get('project_id')
        task_id = context.get('task_id')
        learning_goals = context.get('learning_goals', '')
        
        if project_id or 'project' in str(user_input).lower():
            return ContextType.PROJECT
        elif task_id or 'task' in str(user_input).lower():
            return ContextType.TASK
        elif learning_goals or 'learn' in str(user_input).lower():
            return ContextType.LEARNING
        elif 'research' in str(user_input).lower():
            return ContextType.RESEARCH
        elif 'practice' in str(user_input).lower():
            return ContextType.PRACTICE
        else:
            return ContextType.GENERAL
    
    def _determine_user_intent(self, context: Dict) -> UserIntent:
        """Determine user intent based on context"""
        user_input = context.get('user_input', {})
        learning_goals = context.get('learning_goals', '')
        project_description = context.get('project_description', '')
        
        # Check for explicit intent
        if context.get('user_intent'):
            try:
                return UserIntent(context['user_intent'])
            except ValueError:
                pass
        
        # Infer from context
        text = f"{user_input} {learning_goals} {project_description}".lower()
        
        if any(word in text for word in ['learn', 'study', 'understand', 'tutorial']):
            return UserIntent.LEARN_NEW
        elif any(word in text for word in ['improve', 'enhance', 'better', 'skill']):
            return UserIntent.IMPROVE_SKILLS
        elif any(word in text for word in ['solve', 'fix', 'problem', 'issue', 'error']):
            return UserIntent.SOLVE_PROBLEM
        elif any(word in text for word in ['build', 'create', 'develop', 'project']):
            return UserIntent.BUILD_PROJECT
        elif any(word in text for word in ['research', 'explore', 'investigate']):
            return UserIntent.RESEARCH_TOPIC
        elif any(word in text for word in ['practice', 'exercise', 'drill']):
            return UserIntent.PRACTICE_CONCEPTS
        else:
            return UserIntent.LEARN_NEW  # Default intent
    
    def _get_dynamic_weights(self, context_type: ContextType, user_intent: UserIntent, skill_level: str) -> Dict[str, float]:
        """Get dynamic weights based on context, intent, and skill level"""
        # Start with base weights
        weights = self.base_weights.copy()
        
        # Apply context-specific adjustments
        if context_type in self.context_adjustments:
            context_weights = self.context_adjustments[context_type]
            for component, weight in context_weights.items():
                weights[component] = weight
        
        # Apply skill level adjustments
        if skill_level in self.skill_level_adjustments:
            skill_adjustments = self.skill_level_adjustments[skill_level]
            for component, adjustment in skill_adjustments.items():
                if component in weights:
                    weights[component] *= adjustment
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        return weights
    
    def _calculate_component_scores(self, bookmark: Dict, context: Dict) -> Dict[str, float]:
        """Calculate individual component scores"""
        scores = {}
        
        # Technology match score
        scores['tech_match'] = self._calculate_technology_match(bookmark, context)
        
        # Content relevance score
        scores['content_relevance'] = self._calculate_content_relevance(bookmark, context)
        
        # Difficulty alignment score
        scores['difficulty_alignment'] = self._calculate_difficulty_alignment(bookmark, context)
        
        # Intent alignment score
        scores['intent_alignment'] = self._calculate_intent_alignment(bookmark, context)
        
        # Semantic similarity score
        scores['semantic_similarity'] = self._calculate_semantic_similarity(bookmark, context)
        
        return scores
    
    def _calculate_technology_match(self, bookmark: Dict, context: Dict) -> float:
        """Calculate technology match score"""
        try:
            bookmark_techs = set(bookmark.get('technology_tags', []))
            context_techs = set(context.get('technologies', []))
            
            if not context_techs:
                return 0.5  # Neutral score if no context technologies
            
            if not bookmark_techs:
                return 0.3  # Lower score if no bookmark technologies
            
            overlap = len(bookmark_techs.intersection(context_techs))
            return min(1.0, overlap / len(context_techs))
            
        except Exception as e:
            logger.warning(f"Error calculating technology match: {e}")
            return 0.5
    
    def _calculate_content_relevance(self, bookmark: Dict, context: Dict) -> float:
        """Calculate content relevance score"""
        try:
            # Check content type alignment
            bookmark_type = bookmark.get('content_type', 'general')
            context_type = context.get('content_type', 'general')
            
            if bookmark_type == context_type:
                return 1.0
            elif bookmark_type in ['general', 'article'] and context_type in ['general', 'article']:
                return 0.8
            else:
                return 0.4
            
        except Exception as e:
            logger.warning(f"Error calculating content relevance: {e}")
            return 0.5
    
    def _calculate_difficulty_alignment(self, bookmark: Dict, context: Dict) -> float:
        """Calculate difficulty alignment score"""
        try:
            bookmark_difficulty = bookmark.get('difficulty_level', 'intermediate')
            user_skill_level = context.get('skill_level', 'intermediate')
            
            # Skill level to difficulty mapping
            skill_to_difficulty = {
                'beginner': 'beginner',
                'intermediate': 'intermediate', 
                'advanced': 'advanced'
            }
            
            preferred_difficulty = skill_to_difficulty.get(user_skill_level, 'intermediate')
            
            if bookmark_difficulty == preferred_difficulty:
                return 1.0
            elif bookmark_difficulty == 'intermediate' and preferred_difficulty in ['beginner', 'advanced']:
                return 0.8
            elif bookmark_difficulty == 'beginner' and preferred_difficulty == 'advanced':
                return 0.6
            elif bookmark_difficulty == 'advanced' and preferred_difficulty == 'beginner':
                return 0.4
            else:
                return 0.5
                
        except Exception as e:
            logger.warning(f"Error calculating difficulty alignment: {e}")
            return 0.5
    
    def _calculate_intent_alignment(self, bookmark: Dict, context: Dict) -> float:
        """Calculate intent alignment score"""
        try:
            user_intent = self._determine_user_intent(context)
            bookmark_type = bookmark.get('content_type', 'general')
            
            # Intent to content type mapping
            intent_mapping = {
                UserIntent.LEARN_NEW: ['tutorial', 'course', 'guide', 'documentation'],
                UserIntent.IMPROVE_SKILLS: ['practice', 'exercise', 'challenge', 'project'],
                UserIntent.SOLVE_PROBLEM: ['solution', 'fix', 'debug', 'troubleshooting'],
                UserIntent.BUILD_PROJECT: ['project', 'tutorial', 'example', 'template'],
                UserIntent.RESEARCH_TOPIC: ['article', 'research', 'paper', 'documentation'],
                UserIntent.PRACTICE_CONCEPTS: ['practice', 'exercise', 'quiz', 'challenge']
            }
            
            preferred_types = intent_mapping.get(user_intent, ['general'])
            
            if bookmark_type in preferred_types:
                return 1.0
            elif bookmark_type == 'general':
                return 0.7
            else:
                return 0.4
                
        except Exception as e:
            logger.warning(f"Error calculating intent alignment: {e}")
            return 0.5
    
    def _calculate_semantic_similarity(self, bookmark: Dict, context: Dict) -> float:
        """Calculate semantic similarity score"""
        try:
            # This would typically use embeddings, but for now we'll use keyword matching
            bookmark_text = f"{bookmark.get('title', '')} {bookmark.get('notes', '')}"
            context_text = f"{context.get('learning_goals', '')} {context.get('project_description', '')}"
            
            if not context_text.strip():
                return 0.5
            
            # Simple keyword overlap as fallback
            bookmark_words = set(bookmark_text.lower().split())
            context_words = set(context_text.lower().split())
            
            if not context_words:
                return 0.5
            
            overlap = len(bookmark_words.intersection(context_words))
            return min(1.0, overlap / len(context_words))
            
        except Exception as e:
            logger.warning(f"Error calculating semantic similarity: {e}")
            return 0.5
    
    def _apply_weights(self, component_scores: Dict[str, float], weights: Dict[str, float]) -> Dict[str, float]:
        """Apply weights to component scores"""
        weighted_scores = {}
        for component, score in component_scores.items():
            weight = weights.get(component, 0.0)
            weighted_scores[component] = score * weight
        return weighted_scores
    
    def _calculate_penalties(self, component_scores: Dict[str, float], context: Dict) -> Dict[str, float]:
        """Calculate penalties for low-scoring components"""
        penalties = {}
        
        # Check for irrelevant content
        if (component_scores.get('tech_match', 0) < self.penalty_thresholds['tech_match'] and 
            component_scores.get('semantic_similarity', 0) < self.penalty_thresholds['semantic_similarity']):
            penalties['irrelevant_content'] = self.penalty_multipliers['irrelevant_content']
        
        # Check for skill mismatch
        if component_scores.get('difficulty_alignment', 0) < self.penalty_thresholds['difficulty_alignment']:
            penalties['skill_mismatch'] = self.penalty_multipliers['skill_mismatch']
        
        # Check for context mismatch
        if component_scores.get('intent_alignment', 0) < self.penalty_thresholds['intent_alignment']:
            penalties['context_mismatch'] = self.penalty_multipliers['context_mismatch']
        
        # Check for low quality
        if component_scores.get('content_relevance', 0) < self.penalty_thresholds['content_relevance']:
            penalties['quality_penalty'] = self.penalty_multipliers['quality_penalty']
        
        return penalties
    
    def _apply_penalties(self, total_score: float, penalties: Dict[str, float]) -> float:
        """Apply penalties to total score"""
        final_score = total_score
        
        for penalty_type, multiplier in penalties.items():
            final_score *= multiplier
        
        return max(0.0, min(1.0, final_score))
    
    def _generate_adaptive_reasoning(self, component_scores: Dict[str, float], penalties: Dict[str, float], 
                                   context_type: ContextType, user_intent: UserIntent) -> str:
        """Generate reasoning for the adaptive score"""
        reasoning_parts = []
        
        # Add context information
        reasoning_parts.append(f"Context: {context_type.value}, Intent: {user_intent.value}")
        
        # Add component score insights
        for component, score in component_scores.items():
            if score > 0.7:
                reasoning_parts.append(f"Strong {component.replace('_', ' ')}")
            elif score < 0.3:
                reasoning_parts.append(f"Weak {component.replace('_', ' ')}")
        
        # Add penalty information
        if penalties:
            penalty_reasons = []
            if 'irrelevant_content' in penalties:
                penalty_reasons.append("low relevance")
            if 'skill_mismatch' in penalties:
                penalty_reasons.append("skill level mismatch")
            if 'context_mismatch' in penalties:
                penalty_reasons.append("context mismatch")
            if 'quality_penalty' in penalties:
                penalty_reasons.append("low quality")
            
            if penalty_reasons:
                reasoning_parts.append(f"Penalties applied for: {', '.join(penalty_reasons)}")
        
        return " | ".join(reasoning_parts)

# Global instance
adaptive_scoring_engine = AdaptiveScoringEngine() 