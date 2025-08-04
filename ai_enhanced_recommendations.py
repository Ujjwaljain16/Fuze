#!/usr/bin/env python3
"""
AI-Enhanced Recommendation System
Uses stored analysis data to provide intelligent, personalized recommendations
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis, User
from gemini_utils import GeminiAnalyzer
from multi_user_api_manager import get_user_api_key, record_user_request, check_user_rate_limit

@dataclass
class RecommendationMatch:
    """Represents a recommendation match with detailed scoring"""
    bookmark: SavedContent
    analysis: ContentAnalysis
    match_score: float
    reasoning: str
    learning_path_fit: float
    project_applicability: float
    skill_development: float
    difficulty_match: float
    technology_overlap: float

class AIEnhancedRecommendationEngine:
    """
    AI-Enhanced recommendation engine using stored analysis data
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user_api_key = get_user_api_key(user_id)
        self.gemini_analyzer = GeminiAnalyzer(api_key=self.user_api_key)
        self.logger = logging.getLogger(f"AIRecommendations_{user_id}")
        
        # Scoring weights
        self.weights = {
            'learning_path': 0.25,
            'project_applicability': 0.25,
            'skill_development': 0.20,
            'difficulty_match': 0.15,
            'technology_overlap': 0.15
        }
    
    def get_user_context(self, project_title: str = "", project_description: str = "", 
                        technologies: str = "", learning_goals: str = "") -> Dict:
        """Analyze user context for recommendation matching"""
        try:
            # Check rate limits
            rate_status = check_user_rate_limit(self.user_id)
            if not rate_status['can_make_request']:
                self.logger.warning(f"Rate limited for user {self.user_id}")
                return self._get_fallback_user_context(project_title, project_description, technologies)
            
            # Record request
            record_user_request(self.user_id)
            
            # Analyze user context with Gemini
            context_analysis = self.gemini_analyzer.analyze_user_context(
                title=project_title or "Learning Project",
                description=project_description or learning_goals or "",
                technologies=technologies,
                user_interests=learning_goals
            )
            
            return context_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing user context: {e}")
            return self._get_fallback_user_context(project_title, project_description, technologies)
    
    def _get_fallback_user_context(self, project_title: str, project_description: str, technologies: str) -> Dict:
        """Fallback user context analysis"""
        # Basic technology detection
        detected_techs = []
        text_lower = f"{project_title} {project_description} {technologies}".lower()
        
        if any(tech in text_lower for tech in ['javascript', 'js', 'react', 'node']):
            detected_techs.append('JavaScript')
        if any(tech in text_lower for tech in ['python', 'django', 'flask']):
            detected_techs.append('Python')
        if any(tech in text_lower for tech in ['java', 'jvm', 'spring']):
            detected_techs.append('Java')
        if any(tech in text_lower for tech in ['dsa', 'algorithm', 'data structure']):
            detected_techs.append('DSA')
        
        return {
            "technologies": detected_techs,
            "project_type": "learning" if not project_title else "general",
            "complexity_level": "moderate",
            "development_stage": "learning",
            "learning_needs": detected_techs,
            "technical_requirements": detected_techs,
            "preferred_content_types": ["tutorial", "documentation", "article"],
            "difficulty_preference": "intermediate",
            "focus_areas": detected_techs
        }
    
    def get_analyzed_bookmarks(self, limit: int = 100) -> List[Tuple[SavedContent, ContentAnalysis]]:
        """Get bookmarks with their analysis data"""
        try:
            with app.app_context():
                # Get bookmarks with analysis for the user
                bookmarks_with_analysis = db.session.query(
                    SavedContent, ContentAnalysis
                ).join(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                ).filter(
                    SavedContent.user_id == self.user_id
                ).order_by(
                    SavedContent.saved_at.desc()
                ).limit(limit).all()
                
                return bookmarks_with_analysis
                
        except Exception as e:
            self.logger.error(f"Error getting analyzed bookmarks: {e}")
            return []
    
    def calculate_learning_path_match(self, bookmark_analysis: Dict, user_context: Dict) -> float:
        """Calculate how well the bookmark fits the user's learning path"""
        try:
            bookmark_learning = bookmark_analysis.get('learning_path', {})
            user_learning_needs = user_context.get('learning_needs', [])
            
            if not bookmark_learning or not user_learning_needs:
                return 0.5  # Neutral score
            
            # Check if bookmark is foundational for user's needs
            is_foundational = bookmark_learning.get('is_foundational', False)
            builds_on = bookmark_learning.get('builds_on', [])
            leads_to = bookmark_learning.get('leads_to', [])
            
            # Calculate match based on learning progression
            foundational_bonus = 0.3 if is_foundational else 0
            builds_on_match = len(set(builds_on) & set(user_learning_needs)) / max(len(user_learning_needs), 1)
            leads_to_match = len(set(leads_to) & set(user_learning_needs)) / max(len(user_learning_needs), 1)
            
            return min(1.0, foundational_bonus + (builds_on_match * 0.4) + (leads_to_match * 0.3))
            
        except Exception as e:
            self.logger.error(f"Error calculating learning path match: {e}")
            return 0.5
    
    def calculate_project_applicability(self, bookmark_analysis: Dict, user_context: Dict) -> float:
        """Calculate how applicable the bookmark is to user's project"""
        try:
            bookmark_applicability = bookmark_analysis.get('project_applicability', {})
            user_project_type = user_context.get('project_type', 'general')
            
            if not bookmark_applicability:
                return 0.5
            
            suitable_for = bookmark_applicability.get('suitable_for', [])
            implementation_ready = bookmark_applicability.get('implementation_ready', False)
            code_examples = bookmark_applicability.get('code_examples', False)
            
            # Check if bookmark is suitable for user's project type
            project_match = 1.0 if user_project_type in suitable_for else 0.3
            
            # Bonus for implementation-ready content
            implementation_bonus = 0.2 if implementation_ready else 0
            code_bonus = 0.1 if code_examples else 0
            
            return min(1.0, project_match + implementation_bonus + code_bonus)
            
        except Exception as e:
            self.logger.error(f"Error calculating project applicability: {e}")
            return 0.5
    
    def calculate_skill_development_match(self, bookmark_analysis: Dict, user_context: Dict) -> float:
        """Calculate how well the bookmark develops skills the user needs"""
        try:
            bookmark_skills = bookmark_analysis.get('skill_development', {})
            user_learning_needs = user_context.get('learning_needs', [])
            
            if not bookmark_skills or not user_learning_needs:
                return 0.5
            
            primary_skills = bookmark_skills.get('primary_skills', [])
            secondary_skills = bookmark_skills.get('secondary_skills', [])
            
            all_bookmark_skills = primary_skills + secondary_skills
            
            if not all_bookmark_skills:
                return 0.5
            
            # Calculate skill overlap
            skill_overlap = len(set(all_bookmark_skills) & set(user_learning_needs))
            total_user_needs = len(user_learning_needs)
            
            if total_user_needs == 0:
                return 0.5
            
            # Weight primary skills more heavily
            primary_overlap = len(set(primary_skills) & set(user_learning_needs))
            secondary_overlap = len(set(secondary_skills) & set(user_learning_needs))
            
            primary_score = (primary_overlap / total_user_needs) * 0.7
            secondary_score = (secondary_overlap / total_user_needs) * 0.3
            
            return min(1.0, primary_score + secondary_score)
            
        except Exception as e:
            self.logger.error(f"Error calculating skill development match: {e}")
            return 0.5
    
    def calculate_difficulty_match(self, bookmark_analysis: Dict, user_context: Dict) -> float:
        """Calculate how well the bookmark's difficulty matches user's preference"""
        try:
            bookmark_difficulty = bookmark_analysis.get('difficulty', 'intermediate')
            user_preference = user_context.get('difficulty_preference', 'intermediate')
            
            difficulty_levels = ['beginner', 'intermediate', 'advanced']
            
            try:
                bookmark_index = difficulty_levels.index(bookmark_difficulty.lower())
                user_index = difficulty_levels.index(user_preference.lower())
            except ValueError:
                return 0.5
            
            # Calculate distance between difficulty levels
            distance = abs(bookmark_index - user_index)
            
            if distance == 0:
                return 1.0  # Perfect match
            elif distance == 1:
                return 0.7  # Close match
            else:
                return 0.3  # Far match
            
        except Exception as e:
            self.logger.error(f"Error calculating difficulty match: {e}")
            return 0.5
    
    def calculate_technology_overlap(self, bookmark_analysis: Dict, user_context: Dict) -> float:
        """Calculate technology overlap between bookmark and user needs"""
        try:
            bookmark_techs = bookmark_analysis.get('technologies', [])
            user_techs = user_context.get('technologies', [])
            
            if not bookmark_techs or not user_techs:
                return 0.5
            
            # Calculate Jaccard similarity
            intersection = len(set(bookmark_techs) & set(user_techs))
            union = len(set(bookmark_techs) | set(user_techs))
            
            if union == 0:
                return 0.5
            
            return intersection / union
            
        except Exception as e:
            self.logger.error(f"Error calculating technology overlap: {e}")
            return 0.5
    
    def generate_recommendation_reasoning(self, bookmark: SavedContent, analysis: ContentAnalysis, 
                                        user_context: Dict, match_scores: Dict) -> str:
        """Generate intelligent reasoning for the recommendation"""
        try:
            # Check rate limits
            rate_status = check_user_rate_limit(self.user_id)
            if not rate_status['can_make_request']:
                return self._get_fallback_reasoning(bookmark, analysis, user_context, match_scores)
            
            # Record request
            record_user_request(self.user_id)
            
            # Generate reasoning with Gemini
            reasoning = self.gemini_analyzer.generate_recommendation_reasoning(
                bookmark={
                    'title': bookmark.title,
                    'technologies': analysis.technology_tags.split(', ') if analysis.technology_tags else [],
                    'content_type': analysis.content_type,
                    'difficulty': analysis.difficulty_level,
                    'key_concepts': analysis.key_concepts.split(', ') if analysis.key_concepts else []
                },
                user_context=user_context
            )
            
            return reasoning
            
        except Exception as e:
            self.logger.error(f"Error generating reasoning: {e}")
            return self._get_fallback_reasoning(bookmark, analysis, user_context, match_scores)
    
    def _get_fallback_reasoning(self, bookmark: SavedContent, analysis: ContentAnalysis, 
                               user_context: Dict, match_scores: Dict) -> str:
        """Fallback reasoning when Gemini is unavailable"""
        user_techs = user_context.get('technologies', [])
        bookmark_techs = analysis.technology_tags.split(', ') if analysis.technology_tags else []
        
        common_techs = set(user_techs) & set(bookmark_techs)
        
        if common_techs:
            tech_list = ', '.join(list(common_techs)[:3])
            return f"Relevant for your {user_context.get('project_type', 'project')} using {tech_list}."
        
        content_type = analysis.content_type or 'content'
        difficulty = analysis.difficulty_level or 'intermediate'
        
        return f"Helpful {content_type} at {difficulty} level for your learning goals."
    
    def calculate_overall_match_score(self, match_scores: Dict) -> float:
        """Calculate overall match score using weighted average"""
        try:
            total_score = 0
            total_weight = 0
            
            for component, score in match_scores.items():
                weight = self.weights.get(component, 0)
                total_score += score * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.5
            
            return total_score / total_weight
            
        except Exception as e:
            self.logger.error(f"Error calculating overall match score: {e}")
            return 0.5
    
    def get_recommendations(self, project_title: str = "", project_description: str = "", 
                          technologies: str = "", learning_goals: str = "", 
                          limit: int = 10) -> List[RecommendationMatch]:
        """Get AI-enhanced recommendations based on user context"""
        try:
            self.logger.info(f"Getting recommendations for user {self.user_id}")
            
            # Get user context
            user_context = self.get_user_context(project_title, project_description, technologies, learning_goals)
            
            # Get analyzed bookmarks
            bookmarks_with_analysis = self.get_analyzed_bookmarks(limit=100)
            
            if not bookmarks_with_analysis:
                self.logger.warning(f"No analyzed bookmarks found for user {self.user_id}")
                return []
            
            recommendations = []
            
            for bookmark, analysis in bookmarks_with_analysis:
                try:
                    # Parse analysis data
                    analysis_data = analysis.analysis_data or {}
                    
                    # Calculate individual match scores
                    learning_path_score = self.calculate_learning_path_match(analysis_data, user_context)
                    project_applicability_score = self.calculate_project_applicability(analysis_data, user_context)
                    skill_development_score = self.calculate_skill_development_match(analysis_data, user_context)
                    difficulty_score = self.calculate_difficulty_match(analysis_data, user_context)
                    technology_score = self.calculate_technology_overlap(analysis_data, user_context)
                    
                    match_scores = {
                        'learning_path': learning_path_score,
                        'project_applicability': project_applicability_score,
                        'skill_development': skill_development_score,
                        'difficulty_match': difficulty_score,
                        'technology_overlap': technology_score
                    }
                    
                    # Calculate overall match score
                    overall_score = self.calculate_overall_match_score(match_scores)
                    
                    # Generate reasoning
                    reasoning = self.generate_recommendation_reasoning(
                        bookmark, analysis, user_context, match_scores
                    )
                    
                    # Create recommendation match
                    recommendation = RecommendationMatch(
                        bookmark=bookmark,
                        analysis=analysis,
                        match_score=overall_score,
                        reasoning=reasoning,
                        learning_path_fit=learning_path_score,
                        project_applicability=project_applicability_score,
                        skill_development=skill_development_score,
                        difficulty_match=difficulty_score,
                        technology_overlap=technology_score
                    )
                    
                    recommendations.append(recommendation)
                    
                except Exception as e:
                    self.logger.error(f"Error processing bookmark {bookmark.id}: {e}")
                    continue
            
            # Sort by match score (highest first)
            recommendations.sort(key=lambda x: x.match_score, reverse=True)
            
            # Return top recommendations
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return []
    
    def get_learning_path_recommendations(self, target_skill: str, current_level: str = "beginner") -> List[RecommendationMatch]:
        """Get recommendations for a specific learning path"""
        try:
            # Create learning-focused context
            learning_context = {
                "technologies": [target_skill],
                "project_type": "learning",
                "complexity_level": current_level,
                "development_stage": "learning",
                "learning_needs": [target_skill],
                "difficulty_preference": current_level,
                "focus_areas": [target_skill]
            }
            
            # Get recommendations with learning focus
            recommendations = self.get_recommendations(
                project_title=f"Learning {target_skill}",
                project_description=f"Master {target_skill} from {current_level} level",
                technologies=target_skill,
                learning_goals=target_skill
            )
            
            # Filter for foundational content first
            foundational = [r for r in recommendations if 
                          r.analysis.analysis_data.get('learning_path', {}).get('is_foundational', False)]
            
            # Sort by learning path fit
            foundational.sort(key=lambda x: x.learning_path_fit, reverse=True)
            
            return foundational[:10]
            
        except Exception as e:
            self.logger.error(f"Error getting learning path recommendations: {e}")
            return []

def get_ai_recommendations(user_id: int, project_title: str = "", project_description: str = "", 
                          technologies: str = "", learning_goals: str = "", limit: int = 10) -> List[Dict]:
    """Get AI-enhanced recommendations for a user"""
    try:
        engine = AIEnhancedRecommendationEngine(user_id)
        recommendations = engine.get_recommendations(
            project_title=project_title,
            project_description=project_description,
            technologies=technologies,
            learning_goals=learning_goals,
            limit=limit
        )
        
        # Convert to dictionary format
        result = []
        for rec in recommendations:
            result.append({
                'bookmark_id': rec.bookmark.id,
                'title': rec.bookmark.title,
                'url': rec.bookmark.url,
                'match_score': rec.match_score,
                'reasoning': rec.reasoning,
                'content_type': rec.analysis.content_type,
                'difficulty': rec.analysis.difficulty_level,
                'technologies': rec.analysis.technology_tags.split(', ') if rec.analysis.technology_tags else [],
                'key_concepts': rec.analysis.key_concepts.split(', ') if rec.analysis.key_concepts else [],
                'learning_path_fit': rec.learning_path_fit,
                'project_applicability': rec.project_applicability,
                'skill_development': rec.skill_development,
                'difficulty_match': rec.difficulty_match,
                'technology_overlap': rec.technology_overlap
            })
        
        return result
        
    except Exception as e:
        logging.error(f"Error getting AI recommendations: {e}")
        return []

if __name__ == "__main__":
    # Test the recommendation system
    import argparse
    
    parser = argparse.ArgumentParser(description='Test AI Recommendation System')
    parser.add_argument('--user-id', type=int, required=True, help='User ID')
    parser.add_argument('--project-title', type=str, help='Project title')
    parser.add_argument('--technologies', type=str, help='Technologies')
    parser.add_argument('--limit', type=int, default=5, help='Number of recommendations')
    
    args = parser.parse_args()
    
    recommendations = get_ai_recommendations(
        user_id=args.user_id,
        project_title=args.project_title or "Learning Project",
        technologies=args.technologies or "",
        limit=args.limit
    )
    
    print(f"Found {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   Match Score: {rec['match_score']:.2f}")
        print(f"   Reasoning: {rec['reasoning']}")
        print(f"   Technologies: {', '.join(rec['technologies'])}")
        print(f"   Difficulty: {rec['difficulty']}") 