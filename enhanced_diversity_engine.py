#!/usr/bin/env python3
"""
Enhanced Diversity Engine for True Recommendation Diversity
Implements embedding-based similarity clustering and novelty detection
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import logging
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import heapq

logger = logging.getLogger(__name__)

class EnhancedDiversityEngine:
    """
    Enhanced diversity engine that implements true diversity scoring:
    - Embedding-based similarity clustering
    - Novelty detection
    - Content type balancing
    - Technology diversity
    - Difficulty level distribution
    """
    
    def __init__(self):
        # Initialize embedding model for semantic similarity
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_available = True
            logger.info("Embedding model loaded successfully for diversity analysis")
        except Exception as e:
            self.embedding_model = None
            self.embedding_available = False
            logger.warning(f"Embedding model not available, falling back to basic diversity: {e}")
        
        # Diversity configuration
        self.diversity_config = {
            'max_similarity_threshold': 0.85,  # Maximum similarity between recommendations
            'min_diversity_score': 0.3,        # Minimum diversity score to include
            'content_type_balance': {
                'max_per_type': 3,             # Maximum recommendations per content type
                'preferred_distribution': {     # Preferred distribution of content types
                    'tutorial': 0.3,
                    'documentation': 0.2,
                    'example': 0.2,
                    'troubleshooting': 0.15,
                    'best_practice': 0.15
                }
            },
            'technology_diversity': {
                'max_per_tech': 2,             # Maximum recommendations per technology
                'preferred_tech_mix': 0.7      # Preferred ratio of different technologies
            },
            'difficulty_distribution': {
                'beginner': 0.3,
                'intermediate': 0.4,
                'advanced': 0.3
            }
        }
    
    def get_diverse_recommendations(self, bookmarks: List[Dict], context: Dict, 
                                  max_recommendations: int = 10) -> List[Dict]:
        """
        Get truly diverse recommendations using embedding-based similarity clustering
        """
        try:
            if not bookmarks:
                return []
            
            # Step 1: Get base recommendations (more than needed for diversity selection)
            candidates = self._get_base_candidates(bookmarks, context, max_recommendations * 3)
            
            if not candidates:
                return []
            
            # Step 2: Calculate embeddings for similarity analysis
            embeddings = self._calculate_embeddings(candidates)
            
            if embeddings is None:
                # Fallback to basic diversity if embeddings fail
                return self._get_basic_diverse_recommendations(candidates, max_recommendations)
            
            # Step 3: Calculate similarity matrix
            similarity_matrix = cosine_similarity(embeddings)
            
            # Step 4: Apply diversity selection algorithm
            diverse_recommendations = self._select_diverse_recommendations(
                candidates, similarity_matrix, max_recommendations
            )
            
            # Step 5: Balance content types and technologies
            balanced_recommendations = self._balance_recommendations(
                diverse_recommendations, max_recommendations
            )
            
            # Step 6: Add diversity metadata
            for rec in balanced_recommendations:
                rec['diversity_metadata'] = self._calculate_diversity_metadata(
                    rec, balanced_recommendations, similarity_matrix
                )
            
            return balanced_recommendations
            
        except Exception as e:
            logger.error(f"Error in enhanced diversity selection: {e}")
            return self._get_fallback_recommendations(bookmarks, max_recommendations)
    
    def _get_base_candidates(self, bookmarks: List[Dict], context: Dict, 
                           max_candidates: int) -> List[Dict]:
        """Get base candidates with scores"""
        # Sort by relevance score (assuming bookmarks have scores)
        scored_bookmarks = []
        
        for bookmark in bookmarks:
            # Calculate or get existing score
            score = bookmark.get('score', 0.0)
            if isinstance(score, dict):
                score = score.get('total_score', 0.0)
            
            scored_bookmarks.append({
                **bookmark,
                'base_score': score
            })
        
        # Sort by score and take top candidates
        scored_bookmarks.sort(key=lambda x: x['base_score'], reverse=True)
        return scored_bookmarks[:max_candidates]
    
    def _calculate_embeddings(self, candidates: List[Dict]) -> Optional[np.ndarray]:
        """Calculate embeddings for all candidates"""
        if not self.embedding_available:
            return None
        
        try:
            texts = []
            for candidate in candidates:
                # Create text representation for embedding
                title = candidate.get('title', '')
                notes = candidate.get('notes', '')
                extracted_text = candidate.get('extracted_text', '')
                
                # Combine text with technology tags for better representation
                tech_tags = candidate.get('technology_tags', [])
                tech_text = ' '.join(tech_tags) if tech_tags else ''
                
                full_text = f"{title} {notes} {extracted_text} {tech_text}".strip()
                texts.append(full_text)
            
            # Calculate embeddings
            embeddings = self.embedding_model.encode(texts)
            return embeddings
            
        except Exception as e:
            logger.warning(f"Error calculating embeddings: {e}")
            return None
    
    def _select_diverse_recommendations(self, candidates: List[Dict], 
                                      similarity_matrix: np.ndarray, 
                                      max_recommendations: int) -> List[Dict]:
        """Select diverse recommendations using similarity matrix"""
        selected = []
        selected_indices = set()
        
        # Start with highest scoring candidate
        if candidates:
            selected.append(candidates[0])
            selected_indices.add(0)
        
        # Iteratively select most diverse candidates
        for i in range(1, max_recommendations):
            if len(selected) >= max_recommendations:
                break
            
            # Calculate diversity scores for remaining candidates
            diversity_scores = []
            
            for j in range(len(candidates)):
                if j in selected_indices:
                    diversity_scores.append(-1)  # Already selected
                    continue
                
                # Calculate minimum similarity to already selected items
                similarities_to_selected = [similarity_matrix[j][k] for k in selected_indices]
                min_similarity = min(similarities_to_selected) if similarities_to_selected else 1.0
                
                # Diversity score is inverse of similarity (lower similarity = higher diversity)
                diversity_score = 1.0 - min_similarity
                
                # Combine with base score (weighted average)
                base_score = candidates[j].get('base_score', 0.0)
                combined_score = (diversity_score * 0.6) + (base_score * 0.4)
                
                diversity_scores.append(combined_score)
            
            # Select candidate with highest diversity score
            if diversity_scores:
                best_index = max(range(len(diversity_scores)), key=lambda i: diversity_scores[i])
                if diversity_scores[best_index] > 0:
                    selected.append(candidates[best_index])
                    selected_indices.add(best_index)
        
        return selected
    
    def _balance_recommendations(self, recommendations: List[Dict], 
                               max_recommendations: int) -> List[Dict]:
        """Balance recommendations by content type, technology, and difficulty"""
        if not recommendations:
            return []
        
        # Group by content type
        content_type_groups = defaultdict(list)
        for rec in recommendations:
            content_type = rec.get('content_type', 'general')
            content_type_groups[content_type].append(rec)
        
        # Apply content type balancing
        balanced = []
        max_per_type = self.diversity_config['content_type_balance']['max_per_type']
        
        for content_type, recs in content_type_groups.items():
            # Take top recommendations from each type (up to max_per_type)
            top_recs = sorted(recs, key=lambda x: x.get('base_score', 0.0), reverse=True)
            balanced.extend(top_recs[:max_per_type])
        
        # Sort by base score and take top max_recommendations
        balanced.sort(key=lambda x: x.get('base_score', 0.0), reverse=True)
        return balanced[:max_recommendations]
    
    def _calculate_diversity_metadata(self, recommendation: Dict, 
                                    all_recommendations: List[Dict], 
                                    similarity_matrix: np.ndarray) -> Dict:
        """Calculate diversity metadata for a recommendation"""
        try:
            # Find index of this recommendation in the original list
            rec_index = None
            for i, rec in enumerate(all_recommendations):
                if rec.get('id') == recommendation.get('id'):
                    rec_index = i
                    break
            
            if rec_index is None:
                return {'diversity_score': 0.0, 'similarity_to_others': 1.0}
            
            # Calculate average similarity to other recommendations
            similarities = []
            for j, other_rec in enumerate(all_recommendations):
                if i != j and rec_index < len(similarity_matrix) and j < len(similarity_matrix[rec_index]):
                    similarities.append(similarity_matrix[rec_index][j])
            
            avg_similarity = np.mean(similarities) if similarities else 1.0
            diversity_score = 1.0 - avg_similarity
            
            return {
                'diversity_score': diversity_score,
                'similarity_to_others': avg_similarity,
                'content_type': recommendation.get('content_type', 'general'),
                'technology_tags': recommendation.get('technology_tags', []),
                'difficulty': recommendation.get('difficulty', 'intermediate')
            }
            
        except Exception as e:
            logger.warning(f"Error calculating diversity metadata: {e}")
            return {'diversity_score': 0.0, 'similarity_to_others': 1.0}
    
    def _get_basic_diverse_recommendations(self, candidates: List[Dict], 
                                         max_recommendations: int) -> List[Dict]:
        """Fallback to basic diversity when embeddings are not available"""
        if not candidates:
            return []
        
        # Simple diversity: avoid too many from same content type
        content_type_counts = {}
        diverse_recommendations = []
        
        for candidate in candidates:
            content_type = candidate.get('content_type', 'general')
            
            if content_type_counts.get(content_type, 0) < 3:  # Max 3 of same type
                diverse_recommendations.append(candidate)
                content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
            
            if len(diverse_recommendations) >= max_recommendations:
                break
        
        return diverse_recommendations
    
    def _get_fallback_recommendations(self, bookmarks: List[Dict], 
                                    max_recommendations: int) -> List[Dict]:
        """Complete fallback when diversity selection fails"""
        if not bookmarks:
            return []
        
        # Sort by score and return top recommendations
        scored_bookmarks = []
        for bookmark in bookmarks:
            score = bookmark.get('score', 0.0)
            if isinstance(score, dict):
                score = score.get('total_score', 0.0)
            scored_bookmarks.append({**bookmark, 'base_score': score})
        
        scored_bookmarks.sort(key=lambda x: x['base_score'], reverse=True)
        return scored_bookmarks[:max_recommendations]
    
    def calculate_diversity_score(self, recommendations: List[Dict]) -> float:
        """Calculate overall diversity score for a set of recommendations"""
        if not recommendations or len(recommendations) < 2:
            return 0.0
        
        try:
            # Calculate embeddings if available
            embeddings = self._calculate_embeddings(recommendations)
            
            if embeddings is not None:
                # Calculate similarity matrix
                similarity_matrix = cosine_similarity(embeddings)
                
                # Calculate average similarity (excluding self-similarity)
                total_similarity = 0
                count = 0
                
                for i in range(len(similarity_matrix)):
                    for j in range(i + 1, len(similarity_matrix[i])):
                        total_similarity += similarity_matrix[i][j]
                        count += 1
                
                avg_similarity = total_similarity / count if count > 0 else 1.0
                diversity_score = 1.0 - avg_similarity
                
                return diversity_score
            
            else:
                # Fallback: calculate diversity based on content types
                content_types = [rec.get('content_type', 'general') for rec in recommendations]
                unique_types = len(set(content_types))
                total_types = len(content_types)
                
                return unique_types / total_types if total_types > 0 else 0.0
                
        except Exception as e:
            logger.warning(f"Error calculating diversity score: {e}")
            return 0.0
    
    def analyze_diversity_distribution(self, recommendations: List[Dict]) -> Dict:
        """Analyze the diversity distribution of recommendations"""
        if not recommendations:
            return {}
        
        try:
            analysis = {
                'total_recommendations': len(recommendations),
                'content_type_distribution': {},
                'technology_distribution': {},
                'difficulty_distribution': {},
                'diversity_score': self.calculate_diversity_score(recommendations)
            }
            
            # Content type distribution
            content_types = [rec.get('content_type', 'general') for rec in recommendations]
            for content_type in set(content_types):
                analysis['content_type_distribution'][content_type] = content_types.count(content_type)
            
            # Technology distribution
            all_technologies = []
            for rec in recommendations:
                tech_tags = rec.get('technology_tags', [])
                if isinstance(tech_tags, str):
                    tech_tags = [tag.strip() for tag in tech_tags.split(',')]
                all_technologies.extend(tech_tags)
            
            for tech in set(all_technologies):
                if tech:  # Skip empty strings
                    analysis['technology_distribution'][tech] = all_technologies.count(tech)
            
            # Difficulty distribution
            difficulties = [rec.get('difficulty', 'intermediate') for rec in recommendations]
            for difficulty in set(difficulties):
                analysis['difficulty_distribution'][difficulty] = difficulties.count(difficulty)
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Error analyzing diversity distribution: {e}")
            return {}

# Global instance
enhanced_diversity_engine = EnhancedDiversityEngine() 