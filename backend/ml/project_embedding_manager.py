"""
Project Embedding Manager

This module handles the generation, updating, and management of project embeddings
to enable semantic matching between projects and saved content.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np

from models import Project, SavedContent, ContentAnalysis
from utils.embedding_utils import get_embedding

logger = logging.getLogger(__name__)

class ProjectEmbeddingManager:
    """Manages project embeddings for enhanced semantic matching"""
    
    def __init__(self, db_session: Session):
        """Initialize with a database session"""
        if not db_session:
            raise ValueError("Database session is required")
        self.db_session = db_session
    
    def update_project_embeddings(self, project: Project) -> bool:
        """
        Generate or update embeddings for a project
        
        Args:
            project: Project instance to update embeddings for
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"🔄 Updating embeddings for project: {project.title}")
            
            # Prepare text for embeddings
            title = project.title or ""
            description = project.description or ""
            technologies = project.technologies or ""
            
            # Generate individual embeddings
            if technologies.strip():
                project.tech_embedding = get_embedding(technologies)
                logger.debug(f" Generated tech embedding for: {technologies}")
            
            if description.strip():
                project.description_embedding = get_embedding(description)
                logger.debug(f" Generated description embedding")
            
            # Generate combined embedding (most important for matching)
            combined_text = f"{title} {description} {technologies}".strip()
            if combined_text:
                project.combined_embedding = get_embedding(combined_text)
                logger.debug(f" Generated combined embedding")
            
            # Update timestamp
            project.embeddings_updated = datetime.utcnow()
            
            # Commit changes
            self.db_session.commit()
            logger.info(f" Successfully updated embeddings for project: {project.title}")
            return True
            
        except Exception as e:
            logger.error(f" Failed to update project embeddings: {e}")
            self.db_session.rollback()
            return False
    
    def update_all_project_embeddings(self) -> Dict[str, int]:
        """
        Update embeddings for all projects in the database
        
        Returns:
            Dict with success/failure counts
        """
        try:
            projects = self.db_session.query(Project).all()
            logger.info(f"🔄 Updating embeddings for {len(projects)} projects")
            
            success_count = 0
            failure_count = 0
            
            for project in projects:
                if self.update_project_embeddings(project):
                    success_count += 1
                else:
                    failure_count += 1
            
            logger.info(f" Completed embedding updates: {success_count} success, {failure_count} failures")
            return {
                'total': len(projects),
                'success': success_count,
                'failure': failure_count
            }
            
        except Exception as e:
            logger.error(f" Failed to update all project embeddings: {e}")
            return {'total': 0, 'success': 0, 'failure': 1}
    
    def get_enhanced_recommendations(
        self, 
        project: Project, 
        saved_content: List[SavedContent],
        limit: int = 10,
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Get enhanced recommendations using three-layer matching:
        1. Technology overlap (fast)
        2. Semantic similarity (medium)
        3. Content analysis (rich)
        
        Args:
            project: Project to get recommendations for
            saved_content: List of saved content to analyze
            limit: Maximum number of recommendations to return
            min_score: Minimum score threshold
            
        Returns:
            List of recommendation dictionaries with scores
        """
        try:
            if (project.combined_embedding is None or 
                (hasattr(project.combined_embedding, '__len__') and len(project.combined_embedding) == 0)):
                logger.warning(f"Project {project.title} has no embeddings, updating now...")
                if not self.update_project_embeddings(project):
                    logger.error(f"Failed to generate embeddings for project {project.title}")
                    return []
            
            recommendations = []
            
            for content in saved_content:
                # Skip content without embeddings
                if (content.embedding is None or 
                    (hasattr(content.embedding, '__len__') and len(content.embedding) == 0)):
                    continue
                
                # Layer 1: Technology Overlap (Fast)
                tech_score = self._calculate_tech_overlap(
                    project.technologies, 
                    self._get_content_tech_tags(content)
                )
                
                # Layer 2: Semantic Similarity (Medium)
                semantic_score = self._calculate_semantic_similarity(
                    project.combined_embedding, 
                    content.embedding
                )
                
                # Layer 3: Content Analysis (Rich)
                analysis_score = self._calculate_analysis_score(project, content)
                
                # Combined Score (weighted average)
                final_score = (
                    tech_score * 0.4 +      # Technology matching is important
                    semantic_score * 0.4 +   # Semantic similarity is equally important
                    analysis_score * 0.2     # Content analysis provides context
                )
                
                # Only include if above threshold
                if final_score >= min_score:
                    recommendations.append({
                        'content': content,
                        'score': final_score,
                        'tech_match': tech_score,
                        'semantic_match': semantic_score,
                        'analysis_match': analysis_score,
                        'reasoning': self._generate_recommendation_reasoning(
                            tech_score, semantic_score, analysis_score, content
                        )
                    })
            
            # Sort by score and limit results
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f" Failed to get enhanced recommendations: {e}")
            return []
    
    def _calculate_tech_overlap(self, project_tech: str, content_tech: str) -> float:
        """Calculate technology overlap score between project and content"""
        if not project_tech or not content_tech:
            return 0.0
        
        project_tech_set = set(tech.strip().lower() for tech in project_tech.split(','))
        content_tech_set = set(tech.strip().lower() for tech in content_tech.split(','))
        
        if not project_tech_set or not content_tech_set:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(project_tech_set.intersection(content_tech_set))
        union = len(project_tech_set.union(content_tech_set))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _calculate_semantic_similarity(self, project_embedding, content_embedding) -> float:
        """Calculate semantic similarity between project and content embeddings"""
        try:
            if project_embedding is None or content_embedding is None:
                return 0.0
            
            # Convert to numpy arrays if needed
            if hasattr(project_embedding, 'tolist'):
                project_vec = np.array(project_embedding)
            else:
                project_vec = np.array(project_embedding)
            
            if hasattr(content_embedding, 'tolist'):
                content_vec = np.array(content_embedding)
            else:
                content_vec = np.array(content_embedding)
            
            # Calculate cosine similarity
            similarity = np.dot(project_vec, content_vec) / (
                np.linalg.norm(project_vec) * np.linalg.norm(content_vec)
            )
            
            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.warning(f"Failed to calculate semantic similarity: {e}")
            return 0.0
    
    def _calculate_analysis_score(self, project: Project, content: SavedContent) -> float:
        """Calculate content analysis score based on difficulty, type, and concepts"""
        try:
            # Get content analysis if available
            analysis = self.db_session.query(ContentAnalysis).filter_by(
                content_id=content.id
            ).first()
            
            if not analysis:
                return 0.5  # Neutral score if no analysis available
            
            score = 0.0
            factors = 0
            
            # Difficulty level matching (if project has difficulty preference)
            if hasattr(project, 'difficulty_preference') and project.difficulty_preference:
                if analysis.difficulty_level == project.difficulty_preference:
                    score += 1.0
                elif analysis.difficulty_level in ['intermediate']:
                    score += 0.7
                else:
                    score += 0.3
                factors += 1
            
            # Content type relevance
            if analysis.content_type:
                relevant_types = ['tutorial', 'documentation', 'guide', 'article']
                if analysis.content_type.lower() in relevant_types:
                    score += 0.8
                else:
                    score += 0.4
                factors += 1
            
            # Technology relevance (already covered in tech overlap, but boost if high)
            if analysis.technology_tags and project.technologies:
                tech_overlap = self._calculate_tech_overlap(
                    project.technologies, 
                    analysis.technology_tags
                )
                score += tech_overlap * 0.5
                factors += 1
            
            # Relevance score from analysis
            if analysis.relevance_score:
                score += (analysis.relevance_score / 100.0) * 0.3
                factors += 1
            
            return score / factors if factors > 0 else 0.5
            
        except Exception as e:
            logger.warning(f"Failed to calculate analysis score: {e}")
            return 0.5
    
    def _get_content_tech_tags(self, content: SavedContent) -> str:
        """Get technology tags for content from analysis or tags"""
        try:
            # Try to get from content analysis first
            analysis = self.db_session.query(ContentAnalysis).filter_by(
                content_id=content.id
            ).first()
            
            if analysis and analysis.technology_tags:
                return analysis.technology_tags
            
            # Fallback to content tags
            return content.tags or ""
            
        except Exception as e:
            logger.warning(f"Failed to get content tech tags: {e}")
            return ""
    
    def _generate_recommendation_reasoning(
        self, 
        tech_score: float, 
        semantic_score: float, 
        analysis_score: float, 
        content: SavedContent
    ) -> str:
        """Generate human-readable reasoning for recommendation"""
        reasons = []
        
        if tech_score > 0.7:
            reasons.append("Excellent technology match")
        elif tech_score > 0.4:
            reasons.append("Good technology overlap")
        elif tech_score > 0.1:
            reasons.append("Some technology relevance")
        
        if semantic_score > 0.8:
            reasons.append("Very similar content focus")
        elif semantic_score > 0.6:
            reasons.append("Similar learning objectives")
        elif semantic_score > 0.4:
            reasons.append("Moderately related content")
        
        if analysis_score > 0.8:
            reasons.append("Perfect difficulty and type match")
        elif analysis_score > 0.6:
            reasons.append("Good content characteristics")
        
        if not reasons:
            reasons.append("General relevance based on combined factors")
        
        return "; ".join(reasons)
    
    def get_similar_projects(self, project: Project, limit: int = 5) -> List[Dict]:
        """Find similar projects based on embeddings"""
        try:
            if not project.combined_embedding:
                return []
            
            # Find projects with similar combined embeddings
            similar_projects = self.db_session.query(Project).filter(
                Project.id != project.id,
                Project.combined_embedding.isnot(None)
            ).order_by(
                func.cosine_distance(Project.combined_embedding, project.combined_embedding)
            ).limit(limit).all()
            
            results = []
            for similar_project in similar_projects:
                similarity = self._calculate_semantic_similarity(
                    project.combined_embedding,
                    similar_project.combined_embedding
                )
                results.append({
                    'project': similar_project,
                    'similarity': similarity
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar projects: {e}")
            return []
    
    def cleanup_orphaned_embeddings(self) -> int:
        """Remove embeddings for projects that no longer exist"""
        try:
            # This would need to be implemented based on your specific needs
            # For now, just return 0
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned embeddings: {e}")
            return 0
