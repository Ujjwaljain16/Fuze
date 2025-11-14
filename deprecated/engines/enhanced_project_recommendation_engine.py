"""
Enhanced Project Recommendation Engine

This engine uses project embeddings to provide superior recommendations
by combining technology matching, semantic similarity, and content analysis.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time

from models import db, Project, SavedContent, ContentAnalysis, User
from project_embedding_manager import ProjectEmbeddingManager

logger = logging.getLogger(__name__)

class EnhancedProjectRecommendationEngine:
    """
    Enhanced recommendation engine that leverages project embeddings
    for superior content matching and recommendations.
    """
    
    def __init__(self):
        self.embedding_manager = ProjectEmbeddingManager()
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
    
    def get_project_recommendations(
        self, 
        project_id: int, 
        user_id: int,
        limit: int = 10,
        min_score: float = 0.3,
        use_cache: bool = True
    ) -> Dict:
        """
        Get enhanced recommendations for a specific project
        
        Args:
            project_id: ID of the project to get recommendations for
            user_id: ID of the user requesting recommendations
            limit: Maximum number of recommendations to return
            min_score: Minimum relevance score threshold
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary containing recommendations and metadata
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"project_recs_{project_id}_{user_id}_{limit}_{min_score}"
            if use_cache and cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if time.time() - cached_result['timestamp'] < self.cache_ttl:
                    logger.info(f"📋 Returning cached recommendations for project {project_id}")
                    return cached_result['data']
            
            # Get project and user
            project = Project.query.filter_by(id=project_id, user_id=user_id).first()
            if not project:
                return {
                    'success': False,
                    'error': 'Project not found or access denied',
                    'recommendations': [],
                    'metadata': {}
                }
            
            # Get user's saved content
            saved_content = SavedContent.query.filter_by(user_id=user_id).all()
            if not saved_content:
                return {
                    'success': True,
                    'recommendations': [],
                    'metadata': {
                        'message': 'No saved content available for recommendations',
                        'project_title': project.title,
                        'processing_time': time.time() - start_time
                    }
                }
            
            # Get enhanced recommendations using project embeddings
            recommendations = self.embedding_manager.get_enhanced_recommendations(
                project=project,
                saved_content=saved_content,
                limit=limit,
                min_score=min_score
            )
            
            # Process and format recommendations
            formatted_recommendations = self._format_recommendations(recommendations)
            
            # Generate metadata
            metadata = self._generate_metadata(
                project, recommendations, saved_content, start_time
            )
            
            result = {
                'success': True,
                'recommendations': formatted_recommendations,
                'metadata': metadata
            }
            
            # Cache the result
            if use_cache:
                self.cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get project recommendations: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommendations': [],
                'metadata': {'processing_time': time.time() - start_time}
            }
    
    def get_user_project_recommendations(
        self, 
        user_id: int,
        limit_per_project: int = 5,
        min_score: float = 0.4
    ) -> Dict:
        """
        Get recommendations for all user projects
        
        Args:
            user_id: ID of the user
            limit_per_project: Maximum recommendations per project
            min_score: Minimum relevance score threshold
            
        Returns:
            Dictionary containing recommendations for all projects
        """
        start_time = time.time()
        
        try:
            # Get all user projects
            projects = Project.query.filter_by(user_id=user_id).all()
            if not projects:
                return {
                    'success': True,
                    'projects': [],
                    'metadata': {
                        'message': 'No projects found for user',
                        'processing_time': time.time() - start_time
                    }
                }
            
            # Get user's saved content
            saved_content = SavedContent.query.filter_by(user_id=user_id).all()
            if not saved_content:
                return {
                    'success': True,
                    'projects': [],
                    'metadata': {
                        'message': 'No saved content available',
                        'processing_time': time.time() - start_time
                    }
                }
            
            project_recommendations = {}
            total_recommendations = 0
            
            for project in projects:
                # Get recommendations for this project
                recommendations = self.embedding_manager.get_enhanced_recommendations(
                    project=project,
                    saved_content=saved_content,
                    limit=limit_per_project,
                    min_score=min_score
                )
                
                # Format recommendations
                formatted_recs = self._format_recommendations(recommendations)
                
                project_recommendations[project.id] = {
                    'project': {
                        'id': project.id,
                        'title': project.title,
                        'description': project.description,
                        'technologies': project.technologies
                    },
                    'recommendations': formatted_recs,
                    'count': len(formatted_recs)
                }
                
                total_recommendations += len(formatted_recs)
            
            # Generate metadata
            metadata = {
                'total_projects': len(projects),
                'total_recommendations': total_recommendations,
                'avg_recommendations_per_project': total_recommendations / len(projects) if projects else 0,
                'processing_time': time.time() - start_time,
                'min_score_threshold': min_score
            }
            
            return {
                'success': True,
                'projects': project_recommendations,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get user project recommendations: {e}")
            return {
                'success': False,
                'error': str(e),
                'projects': {},
                'metadata': {'processing_time': time.time() - start_time}
            }
    
    def get_technology_focused_recommendations(
        self,
        user_id: int,
        technology: str,
        limit: int = 10,
        min_score: float = 0.5
    ) -> Dict:
        """
        Get recommendations focused on a specific technology
        
        Args:
            user_id: ID of the user
            technology: Technology to focus on
            limit: Maximum number of recommendations
            min_score: Minimum relevance score threshold
            
        Returns:
            Dictionary containing technology-focused recommendations
        """
        start_time = time.time()
        
        try:
            # Get user's saved content
            saved_content = SavedContent.query.filter_by(user_id=user_id).all()
            if not saved_content:
                return {
                    'success': True,
                    'recommendations': [],
                    'metadata': {
                        'message': 'No saved content available',
                        'technology': technology,
                        'processing_time': time.time() - start_time
                    }
                }
            
            # Filter content by technology
            tech_content = []
            for content in saved_content:
                # Check content analysis first
                analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
                if analysis and analysis.technology_tags:
                    if technology.lower() in analysis.technology_tags.lower():
                        tech_content.append(content)
                        continue
                
                # Fallback to content tags
                if content.tags and technology.lower() in content.tags.lower():
                    tech_content.append(content)
                    continue
                
                # Check extracted text
                if content.extracted_text and technology.lower() in content.extracted_text.lower():
                    tech_content.append(content)
            
            if not tech_content:
                return {
                    'success': True,
                    'recommendations': [],
                    'metadata': {
                        'message': f'No content found for technology: {technology}',
                        'technology': technology,
                        'processing_time': time.time() - start_time
                    }
                }
            
            # Create a virtual project for technology matching
            virtual_project = Project(
                title=f"Technology Focus: {technology}",
                description=f"Learning and development focused on {technology}",
                technologies=technology
            )
            
            # Generate embeddings for virtual project
            self.embedding_manager.update_project_embeddings(virtual_project)
            
            # Get recommendations
            recommendations = self.embedding_manager.get_enhanced_recommendations(
                project=virtual_project,
                saved_content=tech_content,
                limit=limit,
                min_score=min_score
            )
            
            # Format recommendations
            formatted_recommendations = self._format_recommendations(recommendations)
            
            metadata = {
                'technology': technology,
                'total_content_found': len(tech_content),
                'recommendations_returned': len(formatted_recommendations),
                'processing_time': time.time() - start_time,
                'min_score_threshold': min_score
            }
            
            return {
                'success': True,
                'recommendations': formatted_recommendations,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get technology-focused recommendations: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommendations': [],
                'metadata': {
                    'technology': technology,
                    'processing_time': time.time() - start_time
                }
            }
    
    def _format_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Format recommendations for API response"""
        formatted = []
        
        for rec in recommendations:
            content = rec['content']
            
            # Get content analysis if available
            analysis = ContentAnalysis.query.filter_by(content_id=content.id).first()
            
            formatted_rec = {
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'source': content.source,
                'saved_at': content.saved_at.isoformat() if content.saved_at else None,
                'tags': content.tags,
                'category': content.category,
                'notes': content.notes,
                'quality_score': content.quality_score,
                
                # Recommendation scores
                'relevance_score': round(rec['score'], 3),
                'tech_match_score': round(rec['tech_match'], 3),
                'semantic_match_score': round(rec['semantic_match'], 3),
                'analysis_match_score': round(rec['analysis_match'], 3),
                'reasoning': rec['reasoning'],
                
                # Content analysis data
                'content_type': analysis.content_type if analysis else None,
                'difficulty_level': analysis.difficulty_level if analysis else None,
                'technology_tags': analysis.technology_tags if analysis else None,
                'key_concepts': analysis.key_concepts if analysis else None,
                'analysis_relevance_score': analysis.relevance_score if analysis else None
            }
            
            formatted.append(formatted_rec)
        
        return formatted
    
    def _generate_metadata(
        self, 
        project: Project, 
        recommendations: List[Dict], 
        saved_content: List[SavedContent],
        start_time: float
    ) -> Dict:
        """Generate metadata about the recommendation process"""
        
        # Calculate score distribution
        scores = [rec['score'] for rec in recommendations]
        score_distribution = {
            'excellent': len([s for s in scores if s >= 0.8]),
            'good': len([s for s in scores if 0.6 <= s < 0.8]),
            'moderate': len([s for s in scores if 0.4 <= s < 0.6]),
            'low': len([s for s in scores if s < 0.4])
        }
        
        # Calculate average scores by component
        avg_tech_score = sum(rec['tech_match'] for rec in recommendations) / len(recommendations) if recommendations else 0
        avg_semantic_score = sum(rec['semantic_match'] for rec in recommendations) / len(recommendations) if recommendations else 0
        avg_analysis_score = sum(rec['analysis_match'] for rec in recommendations) / len(recommendations) if recommendations else 0
        
        return {
            'project_title': project.title,
            'project_technologies': project.technologies,
            'total_saved_content': len(saved_content),
            'recommendations_returned': len(recommendations),
            'processing_time': round(time.time() - start_time, 3),
            'score_distribution': score_distribution,
            'average_scores': {
                'tech_match': round(avg_tech_score, 3),
                'semantic_match': round(avg_semantic_score, 3),
                'analysis_match': round(avg_analysis_score, 3)
            },
            'embedding_status': {
                'has_tech_embedding': project.tech_embedding is not None,
                'has_description_embedding': project.description_embedding is not None,
                'has_combined_embedding': project.combined_embedding is not None,
                'embeddings_updated': project.embeddings_updated.isoformat() if project.embeddings_updated else None
            }
        }
    
    def clear_cache(self):
        """Clear the recommendation cache"""
        self.cache.clear()
        logger.info("🧹 Recommendation cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        current_time = time.time()
        active_cache_entries = 0
        expired_cache_entries = 0
        
        for cache_key, cache_data in self.cache.items():
            if current_time - cache_data['timestamp'] < self.cache_ttl:
                active_cache_entries += 1
            else:
                expired_cache_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'active_entries': active_cache_entries,
            'expired_entries': expired_cache_entries,
            'cache_ttl_seconds': self.cache_ttl
        }
