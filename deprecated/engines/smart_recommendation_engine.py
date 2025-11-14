#!/usr/bin/env python3
"""
Smart Recommendation Engine
Uses stored analysis data for intelligent recommendations
"""

import os
import sys
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Remove circular import - we'll use Flask app context instead
from models import db, SavedContent, ContentAnalysis
from gemini_utils import GeminiAnalyzer
from multi_user_api_manager import get_user_api_key, record_user_request, check_user_rate_limit

@dataclass
class SmartRecommendation:
    bookmark_id: int
    title: str
    url: str
    match_score: float
    reasoning: str
    content_type: str
    difficulty: str
    technologies: List[str]
    key_concepts: List[str]
    learning_path_fit: float
    project_applicability: float
    skill_development: float

class SmartRecommendationEngine:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user_api_key = get_user_api_key(user_id)
        self.gemini_analyzer = GeminiAnalyzer(api_key=self.user_api_key)
        self.logger = logging.getLogger(f"SmartRecommendations_{user_id}")
    
    def get_user_context(self, project_info: Dict) -> Dict:
        """Analyze user context for recommendations"""
        try:
            # Check rate limits
            rate_status = check_user_rate_limit(self.user_id)
            if not rate_status['can_make_request']:
                return self._get_fallback_context(project_info)
            
            record_user_request(self.user_id)
            
            context_analysis = self.gemini_analyzer.analyze_user_context(
                title=project_info.get('title', 'Learning Project'),
                description=project_info.get('description', ''),
                technologies=project_info.get('technologies', ''),
                user_interests=project_info.get('learning_goals', '')
            )
            
            return context_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing user context: {e}")
            return self._get_fallback_context(project_info)
    
    def _get_fallback_context(self, project_info: Dict) -> Dict:
        """Fallback context analysis - use user's actual input"""
        technologies = project_info.get('technologies', '').strip()
        learning_goals = project_info.get('learning_goals', '').strip()
        
        # Use the user's actual input without hardcoding
        detected_techs = [tech.strip() for tech in technologies.split(',') if tech.strip()] if technologies else []
        learning_needs = [goal.strip() for goal in learning_goals.split(',') if goal.strip()] if learning_goals else []
        
        return {
            "technologies": detected_techs,
            "project_type": "learning",
            "learning_needs": learning_needs,
            "difficulty_preference": "intermediate"
        }
    
    def get_analyzed_bookmarks(self) -> List[tuple]:
        """Get high-quality bookmarks with analysis data from all users"""
        try:
            # Use Flask app context without importing app directly
            from flask import current_app
            if current_app:
                with current_app.app_context():
                    return db.session.query(
                        SavedContent, ContentAnalysis
                    ).join(
                        ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                    ).filter(
                        SavedContent.quality_score >= 6,  # Lower threshold to get more content
                        SavedContent.title.notlike('%Test Bookmark%'),  # Only exclude obvious test content
                        SavedContent.title.notlike('%test bookmark%')
                    ).order_by(
                        SavedContent.quality_score.desc(),  # Order by quality first
                        SavedContent.saved_at.desc()
                    ).limit(500).all()  # Get more candidates for better selection
            else:
                # Fallback: use centralized database session
                from database_utils import get_db_session
                
                session = get_db_session()
                if not session:
                    self.logger.error("Could not get database session")
                    return []
                
                return session.query(
                    SavedContent, ContentAnalysis
                ).join(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                ).filter(
                    SavedContent.quality_score >= 6,
                    SavedContent.title.notlike('%Test Bookmark%'),
                    SavedContent.title.notlike('%test bookmark%')
                ).order_by(
                    SavedContent.quality_score.desc(),
                    SavedContent.saved_at.desc()
                ).limit(500).all()
        except Exception as e:
            self.logger.error(f"Error getting analyzed bookmarks: {e}")
            return []
    
    def calculate_match_score(self, analysis_data: Dict, user_context: Dict) -> Dict:
        """Calculate various match scores using embedding-based similarity"""
        try:
            # Import embedding utilities
            from embedding_utils import (
                get_embedding, 
                calculate_cosine_similarity
            )
            
            bookmark_techs = analysis_data.get('technologies', [])
            user_techs = user_context.get('technologies', [])
            
            # Technology overlap with enhanced matching (reduced weight)
            tech_overlap = 0
            if bookmark_techs and user_techs:
                # Normalize technology names for better matching
                normalized_bookmark_techs = [tech.lower().strip() for tech in bookmark_techs]
                normalized_user_techs = [tech.lower().strip() for tech in user_techs]
                
                # Direct matches
                direct_matches = set(normalized_bookmark_techs) & set(normalized_user_techs)
                
                # Simple related matching - if any user tech appears in bookmark techs
                related_matches = 0
                for user_tech in normalized_user_techs:
                    for bookmark_tech in normalized_bookmark_techs:
                        if user_tech in bookmark_tech or bookmark_tech in user_tech:
                            related_matches += 1
                            break
                
                total_matches = len(direct_matches) + related_matches
                union = len(set(normalized_bookmark_techs) | set(normalized_user_techs))
                tech_overlap = total_matches / union if union > 0 else 0
            
            # Semantic similarity using embeddings (major weight)
            semantic_similarity = 0.5  # Default neutral score
            try:
                # Create text representations for embedding
                bookmark_text = f"technologies: {' '.join(bookmark_techs)} content_type: {analysis_data.get('content_type', '')} difficulty: {analysis_data.get('difficulty', '')}"
                user_text = f"technologies: {' '.join(user_techs)} project_type: {user_context.get('project_type', '')} learning_needs: {' '.join(user_context.get('learning_needs', []))}"
                
                # Generate embeddings
                bookmark_embedding = get_embedding(bookmark_text)
                user_embedding = get_embedding(user_text)
                
                # Calculate semantic similarity
                semantic_similarity = calculate_cosine_similarity(bookmark_embedding, user_embedding)
                
            except Exception as embedding_error:
                self.logger.warning(f"Embedding calculation failed: {embedding_error}")
                # Fallback to keyword-based similarity
                semantic_similarity = self._calculate_keyword_similarity(analysis_data, user_context)
            
            # Learning path fit (reduced weight)
            learning_path = analysis_data.get('learning_path', {})
            learning_needs = user_context.get('learning_needs', [])
            learning_fit = 0.5  # Default neutral score
            
            if learning_path and learning_needs:
                builds_on = learning_path.get('builds_on', [])
                leads_to = learning_path.get('leads_to', [])
                
                builds_match = len(set(builds_on) & set(learning_needs)) / max(len(learning_needs), 1)
                leads_match = len(set(leads_to) & set(learning_needs)) / max(len(learning_needs), 1)
                learning_fit = (builds_match * 0.6) + (leads_match * 0.4)
            
            # Project applicability (reduced weight)
            project_applicability = analysis_data.get('project_applicability', {})
            user_project_type = user_context.get('project_type', 'general')
            
            applicability_score = 0.5
            if project_applicability:
                suitable_for = project_applicability.get('suitable_for', [])
                if user_project_type in suitable_for:
                    applicability_score = 0.8
                if project_applicability.get('implementation_ready', False):
                    applicability_score += 0.1
            
            # Skill development (reduced weight)
            skill_dev = analysis_data.get('skill_development', {})
            primary_skills = skill_dev.get('primary_skills', [])
            secondary_skills = skill_dev.get('secondary_skills', [])
            
            skill_match = 0.5
            if learning_needs:
                all_skills = primary_skills + secondary_skills
                if all_skills:
                    skill_overlap = len(set(all_skills) & set(learning_needs))
                    skill_match = skill_overlap / len(learning_needs)
            
            return {
                'semantic_similarity': semantic_similarity,  # Major weight
                'technology_overlap': tech_overlap,  # Reduced weight
                'learning_path_fit': learning_fit,  # Reduced weight
                'project_applicability': applicability_score,  # Reduced weight
                'skill_development': skill_match  # Reduced weight
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating match scores: {e}")
            return {
                'semantic_similarity': 0.5,
                'technology_overlap': 0.5,
                'learning_path_fit': 0.5,
                'project_applicability': 0.5,
                'skill_development': 0.5
            }
    
    def _calculate_keyword_similarity(self, analysis_data: Dict, user_context: Dict) -> float:
        """Fallback keyword-based similarity calculation"""
        try:
            # Combine bookmark keywords
            bookmark_keywords = []
            bookmark_keywords.extend(analysis_data.get('technologies', []))
            bookmark_keywords.extend(analysis_data.get('key_concepts', []))
            
            # Combine user keywords
            user_keywords = []
            user_keywords.extend(user_context.get('technologies', []))
            user_keywords.extend(user_context.get('learning_needs', []))
            
            # Calculate overlap
            if bookmark_keywords and user_keywords:
                overlap = len(set(bookmark_keywords) & set(user_keywords))
                return overlap / len(user_keywords)
            
            return 0.5  # Neutral score if no keywords
            
        except Exception as e:
            self.logger.error(f"Error calculating keyword similarity: {e}")
            return 0.5
    
    def generate_reasoning(self, bookmark: SavedContent, analysis: ContentAnalysis, 
                          user_context: Dict, match_scores: Dict, bookmark_techs: List[str]) -> str:
        """Generate intelligent reasoning for recommendation"""
        try:
            rate_status = check_user_rate_limit(self.user_id)
            if not rate_status['can_make_request']:
                return self._get_fallback_reasoning(bookmark, analysis, user_context, bookmark_techs)
            
            record_user_request(self.user_id)
            
            reasoning = self.gemini_analyzer.generate_recommendation_reasoning(
                bookmark={
                    'title': bookmark.title,
                    'technologies': bookmark_techs,  # Use properly extracted technologies
                    'content_type': analysis.content_type,
                    'difficulty': analysis.difficulty_level,
                    'key_concepts': analysis.key_concepts.split(', ') if analysis.key_concepts else []
                },
                user_context=user_context
            )
            
            return reasoning
            
        except Exception as e:
            self.logger.error(f"Error generating reasoning: {e}")
            return self._get_fallback_reasoning(bookmark, analysis, user_context, bookmark_techs)
    
    def _get_fallback_reasoning(self, bookmark: SavedContent, analysis: ContentAnalysis, user_context: Dict, bookmark_techs: List[str]) -> str:
        """Fallback reasoning"""
        user_techs = user_context.get('technologies', [])
        
        # Use the passed bookmark_techs instead of extracting from analysis
        common_techs = set(user_techs) & set(bookmark_techs)
        
        if common_techs:
            tech_list = ', '.join(list(common_techs)[:3])
            return f"Relevant for your {user_context.get('project_type', 'project')} using {tech_list}."
        
        return f"Helpful {analysis.content_type or 'content'} for your learning goals."
    
    def get_smart_recommendations(self, project_info: Dict, limit: int = 10) -> List[SmartRecommendation]:
        """Get smart recommendations based on project info"""
        try:
            self.logger.info(f"Getting smart recommendations for user {self.user_id}")
            
            # Get user context
            user_context = self.get_user_context(project_info)
            
            # Get analyzed bookmarks
            bookmarks_with_analysis = self.get_analyzed_bookmarks()
            
            if not bookmarks_with_analysis:
                self.logger.warning(f"No analyzed bookmarks found for user {self.user_id}")
                return []
            
            recommendations = []
            
            for bookmark, analysis in bookmarks_with_analysis:
                try:
                    # Get analysis data from both JSON field and separate columns
                    analysis_data = analysis.analysis_data or {}
                    
                    # Extract technologies from both sources
                    bookmark_techs = []
                    if analysis.technology_tags:
                        bookmark_techs.extend([tech.strip() for tech in analysis.technology_tags.split(',')])
                    if analysis_data.get('technologies'):
                        if isinstance(analysis_data['technologies'], list):
                            bookmark_techs.extend(analysis_data['technologies'])
                        else:
                            bookmark_techs.append(str(analysis_data['technologies']))
                    
                    # Also check key concepts for technology mentions
                    if analysis.key_concepts:
                        concepts = [concept.strip() for concept in analysis.key_concepts.split(',')]
                        bookmark_techs.extend(concepts)
                    
                    # Remove duplicates and normalize
                    bookmark_techs = list(set([tech.strip() for tech in bookmark_techs if tech.strip()]))
                    
                    # Update analysis_data with extracted technologies
                    analysis_data['technologies'] = bookmark_techs
                    
                    # Calculate match scores
                    match_scores = self.calculate_match_score(analysis_data, user_context)
                    
                    # Calculate overall score (weighted average with major emphasis on semantic similarity)
                    overall_score = (
                        match_scores['semantic_similarity'] * 0.6 +  # Major weight to semantic similarity
                        match_scores['technology_overlap'] * 0.15 +  # Reduced weight
                        match_scores['learning_path_fit'] * 0.15 +   # Reduced weight
                        match_scores['project_applicability'] * 0.05 + # Reduced weight
                        match_scores['skill_development'] * 0.05     # Reduced weight
                    ) * 100  # Convert to percentage
                    
                    # Only include recommendations with meaningful relevance
                    if overall_score < 10:  # Lower threshold to be more inclusive
                        continue
                    
                    # Generate reasoning
                    reasoning = self.generate_reasoning(bookmark, analysis, user_context, match_scores, bookmark_techs)
                    
                    # Create recommendation
                    recommendation = SmartRecommendation(
                        bookmark_id=bookmark.id,
                        title=bookmark.title,
                        url=bookmark.url,
                        match_score=overall_score,
                        reasoning=reasoning,
                        content_type=analysis.content_type or 'article',
                        difficulty=analysis.difficulty_level or 'intermediate',
                        technologies=bookmark_techs,  # Use properly extracted technologies
                        key_concepts=analysis.key_concepts.split(', ') if analysis.key_concepts else [],
                        learning_path_fit=match_scores['learning_path_fit'] * 100,  # Convert to percentage
                        project_applicability=match_scores['project_applicability'] * 100,  # Convert to percentage
                        skill_development=match_scores['skill_development'] * 100  # Convert to percentage
                    )
                    
                    recommendations.append(recommendation)
                    
                except Exception as e:
                    self.logger.error(f"Error processing bookmark {bookmark.id}: {e}")
                    continue
            
            # Sort by match score and return top recommendations
            recommendations.sort(key=lambda x: x.match_score, reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting smart recommendations: {e}")
            return []

def get_smart_recommendations(user_id: int, project_info: Dict, limit: int = 10) -> List[Dict]:
    """Get smart recommendations for a user"""
    try:
        engine = SmartRecommendationEngine(user_id)
        recommendations = engine.get_smart_recommendations(project_info, limit)
        
        # Convert to dictionary format
        result = []
        for rec in recommendations:
            result.append({
                'bookmark_id': rec.bookmark_id,
                'title': rec.title,
                'url': rec.url,
                'match_score': rec.match_score,
                'reasoning': rec.reasoning,
                'content_type': rec.content_type,
                'difficulty': rec.difficulty,
                'technologies': rec.technologies,
                'key_concepts': rec.key_concepts,
                'learning_path_fit': rec.learning_path_fit,
                'project_applicability': rec.project_applicability,
                'skill_development': rec.skill_development
            })
        
        return result
        
    except Exception as e:
        logging.error(f"Error getting smart recommendations: {e}")
        return []

if __name__ == "__main__":
    # Test the system
    test_project = {
        'title': 'React Learning Project',
        'description': 'Building a modern web application',
        'technologies': 'JavaScript, React, Node.js',
        'learning_goals': 'Master React hooks and state management'
    }
    
    recommendations = get_smart_recommendations(1, test_project, 5)
    
    print(f"Found {len(recommendations)} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   Match Score: {rec['match_score']:.2f}")
        print(f"   Reasoning: {rec['reasoning']}")
        print(f"   Technologies: {', '.join(rec['technologies'])}")
        print(f"   Difficulty: {rec['difficulty']}") 