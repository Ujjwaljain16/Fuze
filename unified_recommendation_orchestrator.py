#!/usr/bin/env python3
"""
Unified Recommendation Orchestrator
Coordinates all recommendation engines with proper hierarchy and fallback strategies
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, continue without it

from models import db, SavedContent, ContentAnalysis, User
from redis_utils import redis_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class UnifiedRecommendationRequest:
    """Standardized recommendation request format"""
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    user_interests: str = ""
    project_id: Optional[int] = None
    max_recommendations: int = 10
    engine_preference: Optional[str] = None  # 'fast', 'context', 'gemini', 'auto'
    diversity_weight: float = 0.3
    quality_threshold: int = 6
    include_global_content: bool = True
    cache_duration: int = 1800  # 30 minutes

@dataclass
class UnifiedRecommendationResult:
    """Standardized recommendation result format"""
    id: int
    title: str
    url: str
    score: float
    reason: str
    content_type: str
    difficulty: str
    technologies: List[str]
    key_concepts: List[str]
    quality_score: float
    engine_used: str
    confidence: float
    metadata: Dict[str, Any]
    cached: bool = False

@dataclass
class EnginePerformance:
    """Engine performance metrics"""
    engine_name: str
    response_time_ms: float
    success_rate: float
    cache_hit_rate: float
    error_count: int
    last_used: datetime
    total_requests: int

class UnifiedDataLayer:
    """Standardized data layer for all engines"""
    
    def __init__(self):
        self.embedding_model = None
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """Initialize embedding model with fallback for network issues"""
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Try to load the model with network fallback
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                if hasattr(torch, 'meta') and torch.meta.is_available():
                    self.embedding_model = self.embedding_model.to_empty(device='cpu')
                else:
                    self.embedding_model = self.embedding_model.to('cpu')
                logger.info("✅ Embedding model loaded successfully")
            except Exception as network_error:
                logger.warning(f"Network error loading embedding model: {network_error}")
                logger.info("Using fallback embedding approach...")
                # Create a simple fallback embedding function
                self.embedding_model = None
                self._use_fallback_embeddings = True
                
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            self.embedding_model = None
            self._use_fallback_embeddings = True
    
    def normalize_content_data(self, content: SavedContent, analysis: Optional[ContentAnalysis] = None) -> Dict[str, Any]:
        """Normalize content data to unified format"""
        try:
            # Extract technologies from multiple sources
            technologies = []
            
            # From tags
            if content.tags:
                technologies.extend([tech.strip() for tech in content.tags.split(',') if tech.strip()])
            
            # From analysis
            if analysis:
                if analysis.technology_tags:
                    technologies.extend([tech.strip() for tech in analysis.technology_tags.split(',') if tech.strip()])
                
                # From analysis_data JSON
                if analysis.analysis_data:
                    analysis_techs = analysis.analysis_data.get('technologies', [])
                    if isinstance(analysis_techs, list):
                        technologies.extend(analysis_techs)
                    elif isinstance(analysis_techs, str):
                        technologies.extend([tech.strip() for tech in analysis_techs.split(',') if tech.strip()])
            
            # Remove duplicates and normalize
            technologies = list(set([tech.lower().strip() for tech in technologies if tech.strip()]))
            
            # Extract key concepts
            key_concepts = []
            if analysis and analysis.key_concepts:
                key_concepts = [concept.strip() for concept in analysis.key_concepts.split(',') if concept.strip()]
            
            # Determine content type
            content_type = 'article'  # default
            if analysis:
                content_type = analysis.content_type or 'article'
            
            # Determine difficulty
            difficulty = 'intermediate'  # default
            if analysis:
                difficulty = analysis.difficulty_level or 'intermediate'
            
            # Create unified format
            unified_data = {
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'extracted_text': content.extracted_text or '',
                'notes': content.notes or '',
                'technologies': technologies,
                'key_concepts': key_concepts,
                'content_type': content_type,
                'difficulty': difficulty,
                'quality_score': content.quality_score or 6,
                'saved_at': content.saved_at,
                'tags': content.tags or '',
                'analysis_data': analysis.analysis_data if analysis else {},
                'embedding': content.embedding,
                'relevance_score': analysis.relevance_score if analysis else 0
            }
            
            return unified_data
            
        except Exception as e:
            logger.error(f"Error normalizing content data: {e}")
            # Return minimal data
            return {
                'id': content.id,
                'title': content.title,
                'url': content.url,
                'extracted_text': content.extracted_text or '',
                'technologies': [],
                'key_concepts': [],
                'content_type': 'article',
                'difficulty': 'intermediate',
                'quality_score': content.quality_score or 6,
                'saved_at': content.saved_at,
                'tags': content.tags or '',
                'analysis_data': {},
                'embedding': content.embedding,
                'relevance_score': 0
            }
    
    def get_candidate_content(self, user_id: int, request: UnifiedRecommendationRequest) -> List[Dict[str, Any]]:
        """Get candidate content in unified format"""
        try:
            from flask import Flask
            temp_app = Flask(__name__)
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
            db.init_app(temp_app)
            with temp_app.app_context():
                return self._get_content_from_db(user_id, request)
        except Exception as e:
            logger.error(f"Error getting candidate content: {e}")
            return []
    
    def _get_content_from_db(self, user_id: int, request: UnifiedRecommendationRequest) -> List[Dict[str, Any]]:
        """Get content from database with focus on the requesting user's own saved content"""
        try:
            from flask import Flask
            temp_app = Flask(__name__)
            
            # Use the correct DATABASE_URL from environment variables
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                logger.error("DATABASE_URL not found in environment variables")
                return []
                
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            db.init_app(temp_app)
            
            with temp_app.app_context():
                # Build query - FOCUS ON THE REQUESTING USER'S OWN SAVED CONTENT
                query = db.session.query(SavedContent, ContentAnalysis).outerjoin(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                )
                
                # Filter for the requesting user's content
                query = query.filter(SavedContent.user_id == user_id)
                
                # Apply quality filter - but be more inclusive for user's own content
                query = query.filter(SavedContent.quality_score >= 3)  # Lowered to include more user content
                
                # Filter out test content and generic/low-quality content
                query = query.filter(
                    ~SavedContent.title.like('%Test Bookmark%'),
                    ~SavedContent.title.like('%test bookmark%'),
                    ~SavedContent.title.like('%Dictionary%'),
                    ~SavedContent.title.like('%dictionary%'),
                    ~SavedContent.title.like('%International%'),
                    ~SavedContent.url.like('%dbooks.org%'),
                    ~SavedContent.url.like('%pdfdrive.com%'),
                    ~SavedContent.url.like('%scribd.com%')
                )
                
                # Extract request technologies for relevance filtering
                request_techs = [tech.strip().lower() for tech in request.technologies.split(',') if tech.strip()]
                request_text = f"{request.title} {request.description}".lower()
                
                # Get ALL user's own content ordered by quality and recency
                user_content = query.order_by(
                    SavedContent.quality_score.desc(),
                    SavedContent.saved_at.desc()
                ).limit(200).all()  # Increased limit to get more user content
                
                logger.info(f"Found {len(user_content)} content items from user {user_id}")
                
                # Convert to dict format with proper normalization and relevance scoring
                content_list = []
                for content, analysis in user_content:
                    # Use the normalize_content_data method to ensure all required fields
                    normalized_content = self.normalize_content_data(content, analysis)
                    
                    # Calculate relevance score for this content
                    relevance_score = self._calculate_content_relevance(
                        normalized_content, request_techs, request_text, request
                    )
                    
                    # Add additional fields needed by engines
                    normalized_content.update({
                        'user_id': content.user_id,  # This will be the requesting user's ID
                        'is_user_content': True,  # All content is from the requesting user
                        'project_relevance_boost': relevance_score,  # Use calculated relevance
                        'relevance_score': relevance_score  # Add relevance score
                    })
                    
                    # Include all user's own content but prioritize by relevance
                    content_list.append(normalized_content)
                
                # Sort by relevance score first, then by quality
                content_list.sort(key=lambda x: (x.get('relevance_score', 0), x.get('quality_score', 0)), reverse=True)
                
                logger.info(f"Retrieved {len(content_list)} content items from user {user_id}")
                return content_list
                
        except Exception as e:
            logger.error(f"Error getting content from database: {e}")
            return []
    
    def _calculate_content_relevance(self, content: Dict[str, Any], request_techs: List[str], request_text: str, request: UnifiedRecommendationRequest) -> float:
        """Calculate relevance score for user's own content"""
        relevance_score = 0.0
        
        # Technology overlap (50% weight) - Higher weight for user content
        content_techs = content.get('technologies', [])
        if request_techs and content_techs:
            tech_overlap = len(set(request_techs).intersection(set(content_techs)))
            tech_relevance = tech_overlap / len(request_techs) if request_techs else 0
            relevance_score += tech_relevance * 0.5
        
        # Text similarity (30% weight)
        content_text = f"{content.get('title', '')} {content.get('extracted_text', '')}".lower()
        if request_text and content_text:
            # Simple keyword matching for now
            request_words = set(request_text.split())
            content_words = set(content_text.split())
            word_overlap = len(request_words.intersection(content_words))
            text_relevance = word_overlap / len(request_words) if request_words else 0
            relevance_score += text_relevance * 0.3
        
        # Quality score (15% weight) - Lower weight since it's user's own content
        quality_score = content.get('quality_score', 5) / 10.0
        relevance_score += quality_score * 0.15
        
        # User content boost (5% weight) - Small boost since all content is user's
        relevance_score += 0.05
        
        # Project-specific boost
        if request.project_id:
            project_boost = content.get('project_relevance_boost', 0) / 10.0
            relevance_score += project_boost * 0.1
        
        return min(relevance_score, 1.0)  # Cap at 1.0
    
    def _boost_project_relevance(self, content: Dict[str, Any], request: UnifiedRecommendationRequest) -> Dict[str, Any]:
        """Boost content relevance for project-based recommendations"""
        try:
            if not request.project_id:
                return content
            
            # Get project details
            from models import Project
            project = Project.query.filter_by(id=request.project_id, user_id=request.user_id).first()
            if not project:
                return content
            
            # Extract project technologies
            project_techs = [tech.strip().lower() for tech in (project.technologies or '').split(',') if tech.strip()]
            if not project_techs:
                return content
            
            # Check content for project technology matches
            content_text = f"{content.get('title', '')} {content.get('extracted_text', '')} {content.get('tags', '')}".lower()
            content_techs = content.get('technologies', [])
            
            # Calculate technology overlap
            tech_matches = 0
            for project_tech in project_techs:
                if project_tech in content_text or any(project_tech in tech.lower() for tech in content_techs):
                    tech_matches += 1
            
            # Boost quality score based on technology matches
            if tech_matches > 0:
                boost_factor = min(tech_matches * 0.5, 2.0)  # Max 2 point boost
                content['quality_score'] = min(content.get('quality_score', 7) + boost_factor, 10)
                content['project_relevance_boost'] = boost_factor
                logger.debug(f"Boosted content {content.get('id')} by {boost_factor} for project {request.project_id}")
            
            return content
            
        except Exception as e:
            logger.error(f"Error boosting project relevance: {e}")
            return content
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text"""
        if not self.embedding_model or not text:
            return None
        
        try:
            return self.embedding_model.encode([text])[0]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        try:
            emb1 = self.generate_embedding(text1)
            emb2 = self.generate_embedding(text2)
            
            if emb1 is None or emb2 is None:
                return 0.5  # Neutral similarity
            
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.5
    
    def calculate_batch_similarities(self, request_text: str, content_texts: List[str]) -> List[float]:
        """Calculate semantic similarities for multiple content texts in batch"""
        try:
            if not self.embedding_model:
                return [0.5] * len(content_texts)
            
            # Generate embeddings in batch
            all_texts = [request_text] + content_texts
            embeddings = self.embedding_model.encode(all_texts, show_progress_bar=False, batch_size=32)
            
            # Extract request embedding
            request_embedding = embeddings[0]
            content_embeddings = embeddings[1:]
            
            # Calculate similarities
            similarities = []
            for content_emb in content_embeddings:
                similarity = np.dot(request_embedding, content_emb) / (np.linalg.norm(request_embedding) * np.linalg.norm(content_emb))
                similarities.append(float(similarity))
            
            return similarities
            
        except Exception as e:
            logger.error(f"Error calculating batch similarities: {e}")
            return [0.5] * len(content_texts)

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text with fallback support"""
        if self.embedding_model is not None:
            try:
                return self.embedding_model.encode(text).tolist()
            except Exception as e:
                logger.warning(f"Error with embedding model: {e}")
                return self._fallback_embedding(text)
        else:
            return self._fallback_embedding(text)
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """Simple fallback embedding using TF-IDF-like approach"""
        try:
            import re
            from collections import Counter
            
            # Simple text preprocessing
            text = text.lower()
            words = re.findall(r'\b\w+\b', text)
            
            # Create a simple vector representation
            word_counts = Counter(words)
            
            # Create a fixed-size vector (384 dimensions like the original model)
            vector = [0.0] * 384
            
            # Simple hash-based embedding
            for word, count in word_counts.items():
                # Use hash to distribute words across dimensions
                hash_val = hash(word) % 384
                vector[hash_val] += count * 0.1  # Normalize
            
            # Normalize the vector
            magnitude = sum(x*x for x in vector) ** 0.5
            if magnitude > 0:
                vector = [x / magnitude for x in vector]
            
            return vector
            
        except Exception as e:
            logger.error(f"Error in fallback embedding: {e}")
            # Return zero vector as last resort
            return [0.0] * 384

class FastSemanticEngine:
    """Fast semantic similarity engine (Primary)"""
    
    def __init__(self, data_layer: UnifiedDataLayer):
        self.data_layer = data_layer
        self.name = "FastSemanticEngine"
        self.performance = EnginePerformance(
            engine_name=self.name,
            response_time_ms=0.0,
            success_rate=1.0,
            cache_hit_rate=0.0,
            error_count=0,
            last_used=datetime.utcnow(),
            total_requests=0
        )
    
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get fast semantic recommendations"""
        start_time = time.time()
        
        try:
            # Create request text with enhanced project context
            request_text = f"{request.title} {request.description} {request.technologies} {request.user_interests}"
            
            # Add project context if available
            if request.project_id:
                try:
                    from models import Project
                    project = Project.query.filter_by(id=request.project_id, user_id=request.user_id).first()
                    if project:
                        project_context = f"{project.title} {project.description or ''} {project.technologies or ''}"
                        request_text += f" {project_context}"
                        logger.info(f"Enhanced request with project context: {project.title}")
                except Exception as e:
                    logger.warning(f"Could not load project context: {e}")
            
            # OPTIMIZATION: Use batch embedding generation instead of individual calls
            content_texts = []
            for content in content_list:
                # Ensure technologies field exists
                technologies = content.get('technologies', [])
                if not isinstance(technologies, list):
                    technologies = []
                
                content_text = f"{content['title']} {content['extracted_text']} {' '.join(technologies)}"
                content_texts.append(content_text)
            
            # Calculate similarities in batch
            similarities = self.data_layer.calculate_batch_similarities(request_text, content_texts)
            
            recommendations = []
            
            for i, content in enumerate(content_list):
                similarity = similarities[i]
                
                # Calculate technology overlap
                content_techs = content.get('technologies', [])
                if not isinstance(content_techs, list):
                    content_techs = []
                
                tech_overlap = self._calculate_technology_overlap(
                    content_techs,
                    [tech.strip() for tech in request.technologies.split(',') if tech.strip()]
                )
                
                # Calculate final score with improved weighting for user content
                # Technology overlap (40%) + Semantic similarity (35%) + Quality (15%) + User content boost (10%)
                final_score = (tech_overlap * 0.4) + (similarity * 0.35) + (content.get('quality_score', 6) / 10.0 * 0.15)
                
                # Apply user content boost (all content is user's own)
                final_score += 0.1
                
                # Apply project-specific boosts
                if request.project_id and 'project_relevance_boost' in content:
                    project_boost = content['project_relevance_boost'] / 10.0  # Normalize boost
                    final_score = min(final_score + project_boost, 1.0)  # Cap at 1.0
                    logger.debug(f"Applied project boost of {project_boost} to content {content['id']}")
                
                # Apply relevance score boost
                relevance_score = content.get('relevance_score', 0)
                if relevance_score > 0:
                    final_score = min(final_score + (relevance_score * 0.2), 1.0)
                
                # Generate reason
                reason = self._generate_reason(content, similarity, tech_overlap, request.project_id)
                
                # Create result
                result = UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=final_score * 100,  # Convert to percentage
                    reason=reason,
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 6),
                    engine_used=self.name,
                    confidence=similarity,
                    metadata={
                        'semantic_similarity': similarity,
                        'tech_overlap': tech_overlap,
                        'project_boost': content.get('project_relevance_boost', 0),
                        'relevance_score': relevance_score,
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                )
                
                recommendations.append(result)
            
            # Sort by score and limit
            recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # Filter out low-quality recommendations
            min_score_threshold = 25  # Minimum score to be considered relevant
            filtered_recommendations = [r for r in recommendations if r.score >= min_score_threshold]
            
            # If we don't have enough high-quality recommendations, include some medium quality
            if len(filtered_recommendations) < 3:
                medium_threshold = 15
                medium_quality = [r for r in recommendations if r.score >= medium_threshold and r not in filtered_recommendations]
                filtered_recommendations.extend(medium_quality[:2])  # Add max 2 medium quality
            
            # Limit to requested number
            filtered_recommendations = filtered_recommendations[:request.max_recommendations]
            
            # Update performance metrics
            self._update_performance(start_time, True)
            
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Error in FastSemanticEngine: {e}")
            self._update_performance(start_time, False)
            return []
    
    def _calculate_technology_overlap(self, content_techs: List[str], request_techs: List[str]) -> float:
        """Calculate technology overlap score with improved accuracy"""
        if not content_techs or not request_techs:
            return 0.0
        
        # Normalize to lowercase and clean
        content_set = set([tech.lower().strip() for tech in content_techs if tech.strip()])
        request_set = set([tech.lower().strip() for tech in request_techs if tech.strip()])
        
        if not content_set or not request_set:
            return 0.0
        
        # Calculate exact matches
        exact_matches = len(content_set.intersection(request_set))
        
        # Calculate partial matches (one technology contains another)
        partial_matches = 0
        for req_tech in request_set:
            for content_tech in content_set:
                if req_tech in content_tech or content_tech in req_tech:
                    partial_matches += 0.5
                    break
        
        # Calculate related technology matches
        related_matches = 0
        tech_relations = {
            'javascript': ['js', 'node', 'nodejs', 'react', 'vue', 'angular'],
            'python': ['py', 'django', 'flask', 'fastapi'],
            'java': ['spring', 'maven', 'gradle'],
            'react': ['reactjs', 'jsx', 'tsx'],
            'typescript': ['ts', 'javascript'],
            'node': ['nodejs', 'javascript'],
            'sql': ['mysql', 'postgresql', 'database'],
            'mongodb': ['nosql', 'database'],
            'docker': ['container', 'kubernetes'],
            'aws': ['amazon', 'cloud'],
            'git': ['github', 'gitlab', 'version control']
        }
        
        for req_tech in request_set:
            if req_tech in tech_relations:
                related_techs = tech_relations[req_tech]
                for content_tech in content_set:
                    if content_tech in related_techs:
                        related_matches += 0.3
                        break
        
        # Calculate total matches
        total_matches = exact_matches + partial_matches + related_matches
        
        # Calculate overlap ratio
        union_size = len(content_set.union(request_set))
        overlap_ratio = total_matches / union_size if union_size > 0 else 0.0
        
        # Apply non-linear scaling for better differentiation
        if overlap_ratio >= 0.8:
            return 1.0
        elif overlap_ratio >= 0.6:
            return 0.8
        elif overlap_ratio >= 0.4:
            return 0.6
        elif overlap_ratio >= 0.2:
            return 0.4
        else:
            return overlap_ratio * 2  # Scale up small overlaps
    
    def _generate_reason(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int]) -> str:
        """Generate recommendation reason with improved accuracy"""
        reasons = []
        
        # Semantic relevance
        if similarity > 0.8:
            reasons.append("Highly relevant to your request")
        elif similarity > 0.6:
            reasons.append("Very relevant to your request")
        elif similarity > 0.4:
            reasons.append("Moderately relevant to your request")
        elif similarity > 0.2:
            reasons.append("Somewhat relevant to your request")
        
        # Technology match
        if tech_overlap > 0.7:
            tech_list = ', '.join(content.get('technologies', [])[:3])
            reasons.append(f"Directly covers {tech_list} technologies")
        elif tech_overlap > 0.4:
            tech_list = ', '.join(content.get('technologies', [])[:2])
            reasons.append(f"Includes {tech_list} technologies")
        elif tech_overlap > 0.2:
            reasons.append("Some technology overlap")
        
        # Quality indicator
        quality_score = content.get('quality_score', 0)
        if quality_score >= 9:
            reasons.append("Exceptional quality content")
        elif quality_score >= 8:
            reasons.append("High-quality content")
        elif quality_score >= 7:
            reasons.append("Good quality content")
        
        # Content type
        content_type = content.get('content_type', 'article')
        if content_type in ['tutorial', 'guide', 'example']:
            reasons.append(f"Practical {content_type} content")
        elif content_type == 'documentation':
            reasons.append("Comprehensive documentation")
        
        # User content boost
        if content.get('is_user_content', False):
            reasons.append("From your saved content")
        
        # Project relevance
        if project_id:
            reasons.append(f"Relevant to your project")
        
        # Relevance score
        relevance_score = content.get('relevance_score', 0)
        if relevance_score > 0.7:
            reasons.append("Highly relevant based on your request")
        elif relevance_score > 0.5:
            reasons.append("Very relevant based on your request")
        
        # Fallback if no specific reasons
        if not reasons:
            if similarity > 0.1:
                reasons.append("Relevant learning material from your saved content")
            else:
                reasons.append("Quality content from your saved bookmarks")
        
        return ". ".join(reasons) + "."
    
    def _update_performance(self, start_time: float, success: bool):
        """Update performance metrics"""
        response_time = (time.time() - start_time) * 1000
        self.performance.response_time_ms = response_time
        self.performance.total_requests += 1
        self.performance.last_used = datetime.utcnow()
        
        if not success:
            self.performance.error_count += 1
        
        self.performance.success_rate = (
            (self.performance.total_requests - self.performance.error_count) / 
            self.performance.total_requests
        )

class ContextAwareEngine:
    """Context-aware recommendation engine (Secondary)"""
    
    def __init__(self, data_layer: UnifiedDataLayer):
        self.data_layer = data_layer
        self.name = "ContextAwareEngine"
        self.performance = EnginePerformance(
            engine_name=self.name,
            response_time_ms=0.0,
            success_rate=1.0,
            cache_hit_rate=0.0,
            error_count=0,
            last_used=datetime.utcnow(),
            total_requests=0
        )
    
    def get_recommendations(self, content_list: List[Dict], request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get context-aware recommendations"""
        start_time = time.time()
        
        try:
            # Extract context from request
            context = self._extract_context(request)
            
            recommendations = []
            
            for content in content_list:
                # Calculate comprehensive score
                score_components = self._calculate_score_components(content, context)
                
                # Weighted final score with improved weighting for user content
                final_score = (
                    score_components['technology'] * 0.4 +     # Higher tech weight for user content
                    score_components['semantic'] * 0.3 +       # Reduced semantic weight
                    score_components['content_type'] * 0.15 +  # Keep content type
                    score_components['difficulty'] * 0.1 +     # Keep difficulty
                    score_components['quality'] * 0.05         # Keep quality
                )
                
                # Apply user content boost (all content is user's own)
                final_score += 0.1
                
                # Apply relevance score boost
                relevance_score = content.get('relevance_score', 0)
                if relevance_score > 0:
                    final_score = min(final_score + (relevance_score * 0.15), 1.0)
                
                # Generate detailed reason
                reason = self._generate_detailed_reason(content, context, score_components)
                
                # Create result
                result = UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=final_score * 100,
                    reason=reason,
                    content_type=content.get('content_type', 'article'),
                    difficulty=content.get('difficulty', 'intermediate'),
                    technologies=content.get('technologies', []),
                    key_concepts=content.get('key_concepts', []),
                    quality_score=content.get('quality_score', 6),
                    engine_used=self.name,
                    confidence=score_components['semantic'],
                    metadata={
                        'score_components': score_components,
                        'context_used': context,
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                )
                
                recommendations.append(result)
            
            # Sort and limit
            recommendations.sort(key=lambda x: x.score, reverse=True)
            
            # Filter out low-quality recommendations
            min_score_threshold = 25  # Minimum score to be considered relevant
            filtered_recommendations = [r for r in recommendations if r.score >= min_score_threshold]
            
            # If we don't have enough high-quality recommendations, include some medium quality
            if len(filtered_recommendations) < 3:
                medium_threshold = 15
                medium_quality = [r for r in recommendations if r.score >= medium_threshold and r not in filtered_recommendations]
                filtered_recommendations.extend(medium_quality[:2])  # Add max 2 medium quality
            
            # Limit to requested number
            filtered_recommendations = filtered_recommendations[:request.max_recommendations]
            
            # Update performance
            self._update_performance(start_time, True)
            
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Error in ContextAwareEngine: {e}")
            self._update_performance(start_time, False)
            return []
    
    def _extract_context(self, request: UnifiedRecommendationRequest) -> Dict[str, Any]:
        """Extract context from request"""
        # Extract technologies
        technologies = [tech.strip() for tech in request.technologies.split(',') if tech.strip()]
        
        # Determine content type preference
        content_type = 'general'
        if 'tutorial' in request.description.lower() or 'learn' in request.description.lower():
            content_type = 'tutorial'
        elif 'documentation' in request.description.lower() or 'api' in request.description.lower():
            content_type = 'documentation'
        elif 'example' in request.description.lower() or 'demo' in request.description.lower():
            content_type = 'example'
        
        # Determine difficulty preference
        difficulty = 'intermediate'
        if 'beginner' in request.description.lower() or 'basic' in request.description.lower():
            difficulty = 'beginner'
        elif 'advanced' in request.description.lower() or 'expert' in request.description.lower():
            difficulty = 'advanced'
        
        return {
            'technologies': technologies,
            'content_type': content_type,
            'difficulty': difficulty,
            'title': request.title,
            'description': request.description,
            'user_interests': request.user_interests
        }
    
    def _calculate_score_components(self, content: Dict, context: Dict) -> Dict[str, float]:
        """Calculate individual score components"""
        components = {}
        
        # Ensure technologies fields exist
        content_techs = content.get('technologies', [])
        if not isinstance(content_techs, list):
            content_techs = []
        
        context_techs = context.get('technologies', [])
        if not isinstance(context_techs, list):
            context_techs = []
        
        # Semantic similarity
        request_text = f"{context['title']} {context['description']} {' '.join(context_techs)}"
        content_text = f"{content['title']} {content['extracted_text']} {' '.join(content_techs)}"
        components['semantic'] = self.data_layer.calculate_semantic_similarity(request_text, content_text)
        
        # Technology match
        tech_overlap = self._calculate_technology_overlap(content_techs, context_techs)
        components['technology'] = tech_overlap
        
        # Content type match
        content_type_match = 1.0 if content.get('content_type', 'article') == context.get('content_type', 'article') else 0.3
        components['content_type'] = content_type_match
        
        # Difficulty match
        difficulty_match = self._calculate_difficulty_match(content.get('difficulty', 'intermediate'), context.get('difficulty', 'intermediate'))
        components['difficulty'] = difficulty_match
        
        # Quality score (normalized to 0-1)
        components['quality'] = min(content.get('quality_score', 6) / 10.0, 1.0)
        
        return components
    
    def _calculate_technology_overlap(self, content_techs: List[str], context_techs: List[str]) -> float:
        """Calculate technology overlap with enhanced matching"""
        if not content_techs or not context_techs:
            return 0.0
        
        content_set = set([tech.lower() for tech in content_techs])
        context_set = set([tech.lower() for tech in context_techs])
        
        # Direct matches
        direct_matches = len(content_set.intersection(context_set))
        
        # Related matches (simple heuristic)
        related_matches = 0
        for context_tech in context_set:
            for content_tech in content_set:
                if context_tech in content_tech or content_tech in context_tech:
                    related_matches += 0.5
                    break
        
        total_matches = direct_matches + related_matches
        union = len(content_set.union(context_set))
        
        return total_matches / union if union > 0 else 0.0
    
    def _calculate_difficulty_match(self, content_diff: str, context_diff: str) -> float:
        """Calculate difficulty alignment"""
        if content_diff == context_diff:
            return 1.0
        
        difficulty_levels = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        content_level = difficulty_levels.get(content_diff, 2)
        context_level = difficulty_levels.get(context_diff, 2)
        
        level_diff = abs(content_level - context_level)
        
        if level_diff == 0:
            return 1.0
        elif level_diff == 1:
            return 0.7
        else:
            return 0.3
    
    def _generate_detailed_reason(self, content: Dict, context: Dict, components: Dict[str, float]) -> str:
        """Generate detailed recommendation reason"""
        reasons = []
        
        # Technology match
        if components['technology'] > 0.5:
            tech_list = ', '.join(content.get('technologies', [])[:3])
            reasons.append(f"Directly covers {tech_list} technologies")
        elif components['technology'] > 0.2:
            reasons.append("Some technology overlap with your project")
        
        # Content type
        if components['content_type'] > 0.8:
            reasons.append(f"Perfect {content.get('content_type', 'article')} content for your needs")
        elif components['content_type'] > 0.5:
            reasons.append(f"Good {content.get('content_type', 'article')} material")
        
        # Difficulty
        if components['difficulty'] > 0.8:
            reasons.append(f"Appropriate {content.get('difficulty', 'intermediate')} level for your project")
        
        # Quality
        if components['quality'] > 0.8:
            reasons.append("High-quality, well-curated content")
        
        # Semantic relevance
        if components['semantic'] > 0.7:
            reasons.append("High semantic relevance to your project")
        
        # User content boost - ADD THIS
        if content.get('is_user_content', False):
            reasons.append("From your saved content")
        
        # Project relevance
        if context.get('project_id'):
            reasons.append("Relevant to your project")
        
        # Relevance score
        relevance_score = content.get('relevance_score', 0)
        if relevance_score > 0.7:
            reasons.append("Highly relevant based on your request")
        elif relevance_score > 0.5:
            reasons.append("Very relevant based on your request")
        
        if not reasons:
            if components['semantic'] > 0.1:
                reasons.append("Relevant learning material from your saved content")
            else:
                reasons.append("Quality content from your saved bookmarks")
        
        return ". ".join(reasons) + "."
    
    def _update_performance(self, start_time: float, success: bool):
        """Update performance metrics"""
        response_time = (time.time() - start_time) * 1000
        self.performance.response_time_ms = response_time
        self.performance.total_requests += 1
        self.performance.last_used = datetime.utcnow()
        
        if not success:
            self.performance.error_count += 1
        
        self.performance.success_rate = (
            (self.performance.total_requests - self.performance.error_count) / 
            self.performance.total_requests
        )

class UnifiedRecommendationOrchestrator:
    """Main orchestrator that coordinates all engines"""
    
    def __init__(self):
        self.data_layer = UnifiedDataLayer()
        self.fast_engine = FastSemanticEngine(self.data_layer)
        self.context_engine = ContextAwareEngine(self.data_layer)
        
        # Engine registry
        self.engines = {
            'fast': self.fast_engine,
            'context': self.context_engine
        }
        
        # Performance tracking
        self.performance_history = []
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("Unified Recommendation Orchestrator initialized")
    
    def get_recommendations(self, request: UnifiedRecommendationRequest) -> List[UnifiedRecommendationResult]:
        """Get recommendations using orchestrated approach"""
        start_time = time.time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(request)
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self.cache_hits += 1
                logger.info(f"Cache hit for request: {request.title[:50]}...")
                return cached_result
            
            self.cache_misses += 1
            
            # Get candidate content
            content_list = self.data_layer.get_candidate_content(request.user_id, request)
            
            if not content_list:
                logger.warning("No candidate content found")
                return []
            
            # Select and execute engine
            recommendations = self._execute_engine_strategy(request, content_list)
            
            # Cache results
            self._cache_result(cache_key, recommendations, request.cache_duration)
            
            # Log performance
            response_time = (time.time() - start_time) * 1000
            logger.info(f"Recommendations generated in {response_time:.2f}ms using {recommendations[0].engine_used if recommendations else 'no engine'}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            return []
    
    def _execute_engine_strategy(self, request: UnifiedRecommendationRequest, content_list: List[Dict]) -> List[UnifiedRecommendationResult]:
        """Execute engine selection strategy"""
        
        # Engine selection logic
        if request.engine_preference == 'fast':
            return self.fast_engine.get_recommendations(content_list, request)
        elif request.engine_preference == 'context':
            return self.context_engine.get_recommendations(content_list, request)
        else:
            # Auto-selection based on request characteristics
            return self._auto_select_engine(request, content_list)
    
    def _auto_select_engine(self, request: UnifiedRecommendationRequest, content_list: List[Dict]) -> List[UnifiedRecommendationResult]:
        """Auto-select best engine based on request characteristics"""
        
        # Simple heuristics for engine selection
        request_complexity = self._assess_request_complexity(request)
        
        if request_complexity == 'simple':
            # Use fast engine for simple requests
            return self.fast_engine.get_recommendations(content_list, request)
        else:
            # Use context engine for complex requests
            return self.context_engine.get_recommendations(content_list, request)
    
    def _assess_request_complexity(self, request: UnifiedRecommendationRequest) -> str:
        """Assess request complexity"""
        complexity_score = 0
        
        # Title length
        if len(request.title) > 50:
            complexity_score += 1
        
        # Description length
        if len(request.description) > 100:
            complexity_score += 1
        
        # Number of technologies
        tech_count = len([tech for tech in request.technologies.split(',') if tech.strip()])
        if tech_count > 3:
            complexity_score += 1
        
        # User interests
        if len(request.user_interests) > 50:
            complexity_score += 1
        
        return 'complex' if complexity_score >= 2 else 'simple'
    
    def _generate_cache_key(self, request: UnifiedRecommendationRequest) -> str:
        """Generate cache key for request"""
        import hashlib
        
        # Create unique string from request
        request_str = f"{request.user_id}:{request.title}:{request.description}:{request.technologies}:{request.max_recommendations}:{request.engine_preference}"
        
        # Generate hash
        return f"unified_recommendations:{hashlib.md5(request_str.encode()).hexdigest()}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[UnifiedRecommendationResult]]:
        """Get cached result"""
        try:
            cached_data = redis_cache.get_cache(cache_key)
            if cached_data:
                # Convert back to UnifiedRecommendationResult objects
                results = []
                for item in cached_data:
                    result = UnifiedRecommendationResult(**item)
                    result.cached = True
                    results.append(result)
                return results
            return None
        except Exception as e:
            logger.error(f"Error getting cached result: {e}")
            return None
    
    def _cache_result(self, cache_key: str, results: List[UnifiedRecommendationResult], ttl: int):
        """Cache result"""
        try:
            # Convert to serializable format
            cache_data = [asdict(result) for result in results]
            redis_cache.set_cache(cache_key, cache_data, ttl)
        except Exception as e:
            logger.error(f"Error caching result: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'engines': {
                name: {
                    'response_time_ms': engine.performance.response_time_ms,
                    'success_rate': engine.performance.success_rate,
                    'total_requests': engine.performance.total_requests,
                    'error_count': engine.performance.error_count,
                    'last_used': engine.performance.last_used.isoformat()
                }
                for name, engine in self.engines.items()
            }
        }

# Global orchestrator instance
_orchestrator_instance = None

def get_unified_orchestrator() -> UnifiedRecommendationOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = UnifiedRecommendationOrchestrator()
    return _orchestrator_instance

def get_unified_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Main function to get unified recommendations"""
    try:
        # Create request object
        request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            user_interests=request_data.get('user_interests', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engine_preference=request_data.get('engine_preference'),
            diversity_weight=request_data.get('diversity_weight', 0.3),
            quality_threshold=request_data.get('quality_threshold', 6),
            include_global_content=request_data.get('include_global_content', True)
        )
        
        # Get orchestrator
        orchestrator = get_unified_orchestrator()
        
        # Get recommendations
        results = orchestrator.get_recommendations(request)
        
        # Convert to dictionary format for API response
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error getting unified recommendations: {e}")
        return []

if __name__ == "__main__":
    # Test the orchestrator
    test_request = UnifiedRecommendationRequest(
        user_id=1,
        title="React Learning Project",
        description="Building a modern web application with React",
        technologies="JavaScript, React, Node.js",
        user_interests="Frontend development, state management",
        max_recommendations=5
    )
    
    orchestrator = UnifiedRecommendationOrchestrator()
    results = orchestrator.get_recommendations(test_request)
    
    print(f"Generated {len(results)} recommendations:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Score: {result.score:.2f}")
        print(f"   Engine: {result.engine_used}")
        print(f"   Reason: {result.reason}")
        print(f"   Technologies: {', '.join(result.technologies[:3])}") 