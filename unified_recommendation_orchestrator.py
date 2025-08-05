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
        """Initialize embedding model with error handling"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model initialized successfully")
        except Exception as e:
            logger.warning(f"Embedding model not available: {e}")
            self.embedding_model = None
    
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
            # Create a minimal app context if needed
            from flask import Flask
            if not hasattr(db, 'app') or db.app is None:
                temp_app = Flask(__name__)
                temp_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/fuze')
                db.init_app(temp_app)
                with temp_app.app_context():
                    return self._get_content_from_db(user_id, request)
            else:
                with db.app.app_context():
                    return self._get_content_from_db(user_id, request)
        except Exception as e:
            logger.error(f"Error getting candidate content: {e}")
            return []
    
    def _get_content_from_db(self, user_id: int, request: UnifiedRecommendationRequest) -> List[Dict[str, Any]]:
        """Get content from database with proper error handling"""
        try:
            # Build query
                query = db.session.query(SavedContent, ContentAnalysis).outerjoin(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                )
                
                # Apply quality filter
                query = query.filter(SavedContent.quality_score >= request.quality_threshold)
                
                # Filter out test content
                query = query.filter(
                    ~SavedContent.title.like('%Test Bookmark%'),
                    ~SavedContent.title.like('%test bookmark%')
                )
                
                # Include global content if requested
                if not request.include_global_content:
                    query = query.filter(SavedContent.user_id == user_id)
                
                # For project-based recommendations, prioritize content that might be relevant
                if request.project_id:
                    # Get project details to enhance filtering
                    from models import Project
                    project = Project.query.filter_by(id=request.project_id, user_id=user_id).first()
                    if project:
                        # Boost content that mentions project technologies
                        project_techs = [tech.strip().lower() for tech in (project.technologies or '').split(',') if tech.strip()]
                        if project_techs:
                            # Add a subquery to boost relevant content
                            logger.info(f"Project technologies: {project_techs}")
                
                # Order by quality and recency
                query = query.order_by(
                    SavedContent.quality_score.desc(),
                    SavedContent.saved_at.desc()
                )
                
                # Limit results
                query = query.limit(500)
                
                # Execute query
                results = query.all()
                
                # Normalize data
                normalized_content = []
                for content, analysis in results:
                    normalized = self.normalize_content_data(content, analysis)
                    
                    # Boost score for project-relevant content
                    if request.project_id:
                        normalized = self._boost_project_relevance(normalized, request)
                    
                    normalized_content.append(normalized)
                
                logger.info(f"Retrieved {len(normalized_content)} candidate content items")
                return normalized_content
                
        except Exception as e:
            logger.error(f"Error getting candidate content: {e}")
            return []
    
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
            
            recommendations = []
            
            for content in content_list:
                # Create content text
                content_text = f"{content['title']} {content['extracted_text']} {' '.join(content['technologies'])}"
                
                # Calculate semantic similarity
                similarity = self.data_layer.calculate_semantic_similarity(request_text, content_text)
                
                # Calculate technology overlap
                tech_overlap = self._calculate_technology_overlap(
                    content['technologies'],
                    [tech.strip() for tech in request.technologies.split(',') if tech.strip()]
                )
                
                # Calculate final score (70% semantic + 30% tech overlap)
                final_score = (similarity * 0.7) + (tech_overlap * 0.3)
                
                # Apply project-specific boosts
                if request.project_id and 'project_relevance_boost' in content:
                    project_boost = content['project_relevance_boost'] / 10.0  # Normalize boost
                    final_score = min(final_score + project_boost, 1.0)  # Cap at 1.0
                    logger.debug(f"Applied project boost of {project_boost} to content {content['id']}")
                
                # Generate reason
                reason = self._generate_reason(content, similarity, tech_overlap, request.project_id)
                
                # Create result
                result = UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=final_score * 100,  # Convert to percentage
                    reason=reason,
                    content_type=content['content_type'],
                    difficulty=content['difficulty'],
                    technologies=content['technologies'],
                    key_concepts=content['key_concepts'],
                    quality_score=content['quality_score'],
                    engine_used=self.name,
                    confidence=similarity,
                    metadata={
                        'semantic_similarity': similarity,
                        'tech_overlap': tech_overlap,
                        'project_boost': content.get('project_relevance_boost', 0),
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                )
                
                recommendations.append(result)
            
            # Sort by score and limit
            recommendations.sort(key=lambda x: x.score, reverse=True)
            recommendations = recommendations[:request.max_recommendations]
            
            # Update performance metrics
            self._update_performance(start_time, True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in FastSemanticEngine: {e}")
            self._update_performance(start_time, False)
            return []
    
    def _calculate_technology_overlap(self, content_techs: List[str], request_techs: List[str]) -> float:
        """Calculate technology overlap score"""
        if not content_techs or not request_techs:
            return 0.0
        
        # Normalize to lowercase
        content_set = set([tech.lower() for tech in content_techs])
        request_set = set([tech.lower() for tech in request_techs])
        
        # Calculate Jaccard similarity
        intersection = len(content_set.intersection(request_set))
        union = len(content_set.union(request_set))
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_reason(self, content: Dict, similarity: float, tech_overlap: float, project_id: Optional[int]) -> str:
        """Generate recommendation reason"""
        reasons = []
        
        if similarity > 0.7:
            reasons.append("High semantic relevance to your project")
        elif similarity > 0.5:
            reasons.append("Moderate semantic relevance")
        
        if tech_overlap > 0.5:
            tech_list = ', '.join(content['technologies'][:3])
            reasons.append(f"Directly covers {tech_list} technologies")
        elif tech_overlap > 0.2:
            reasons.append("Some technology overlap")
        
        if content['quality_score'] >= 8:
            reasons.append("High-quality content")
        
        if project_id:
            reasons.append(f"Relevant to your project: {project_id}")
        
        if not reasons:
            reasons.append("Relevant learning material")
        
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
                
                # Weighted final score
                final_score = (
                    score_components['semantic'] * 0.4 +
                    score_components['technology'] * 0.3 +
                    score_components['content_type'] * 0.15 +
                    score_components['difficulty'] * 0.1 +
                    score_components['quality'] * 0.05
                )
                
                # Generate detailed reason
                reason = self._generate_detailed_reason(content, context, score_components)
                
                # Create result
                result = UnifiedRecommendationResult(
                    id=content['id'],
                    title=content['title'],
                    url=content['url'],
                    score=final_score * 100,
                    reason=reason,
                    content_type=content['content_type'],
                    difficulty=content['difficulty'],
                    technologies=content['technologies'],
                    key_concepts=content['key_concepts'],
                    quality_score=content['quality_score'],
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
            recommendations = recommendations[:request.max_recommendations]
            
            # Update performance
            self._update_performance(start_time, True)
            
            return recommendations
            
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
        
        # Semantic similarity
        request_text = f"{context['title']} {context['description']} {' '.join(context['technologies'])}"
        content_text = f"{content['title']} {content['extracted_text']} {' '.join(content['technologies'])}"
        components['semantic'] = self.data_layer.calculate_semantic_similarity(request_text, content_text)
        
        # Technology match
        tech_overlap = self._calculate_technology_overlap(content['technologies'], context['technologies'])
        components['technology'] = tech_overlap
        
        # Content type match
        content_type_match = 1.0 if content['content_type'] == context['content_type'] else 0.3
        components['content_type'] = content_type_match
        
        # Difficulty match
        difficulty_match = self._calculate_difficulty_match(content['difficulty'], context['difficulty'])
        components['difficulty'] = difficulty_match
        
        # Quality score (normalized to 0-1)
        components['quality'] = min(content['quality_score'] / 10.0, 1.0)
        
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
            tech_list = ', '.join(content['technologies'][:3])
            reasons.append(f"Directly covers {tech_list} technologies")
        elif components['technology'] > 0.2:
            reasons.append("Some technology overlap with your project")
        
        # Content type
        if components['content_type'] > 0.8:
            reasons.append(f"Perfect {content['content_type']} content for your needs")
        elif components['content_type'] > 0.5:
            reasons.append(f"Good {content['content_type']} material")
        
        # Difficulty
        if components['difficulty'] > 0.8:
            reasons.append(f"Appropriate {content['difficulty']} level for your project")
        
        # Quality
        if components['quality'] > 0.8:
            reasons.append("High-quality, well-curated content")
        
        # Semantic relevance
        if components['semantic'] > 0.7:
            reasons.append("High semantic relevance to your project")
        
        if not reasons:
            reasons.append("Relevant learning material for your project")
        
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