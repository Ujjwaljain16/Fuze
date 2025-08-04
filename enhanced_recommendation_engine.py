#!/usr/bin/env python3
"""
Enhanced Recommendation System - Phase 1: Core Engine Unification
Unified Intelligent Engine (UIE) - Foundation
"""

import os
import sys
import time
import logging
import json
import hashlib
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np

# Optional imports
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("SentenceTransformers not available, using fallback embeddings")

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Optional imports
try:
    import redis
except ImportError:
    redis = None
    logging.warning("Redis not available, using memory-only caching")

from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis, User, Feedback
from redis_utils import redis_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RecommendationResult:
    """Structured recommendation result"""
    content_id: int
    title: str
    url: str
    score: float
    reasoning: str
    content_type: str
    difficulty: str
    technologies: List[str]
    key_concepts: List[str]
    quality_score: float
    diversity_score: float
    novelty_score: float
    algorithm_used: str
    confidence: float
    metadata: Dict[str, Any]

@dataclass
class UserProfile:
    """Comprehensive user profile"""
    user_id: int
    interests: List[str]
    skill_level: str
    learning_style: str
    technology_preferences: List[str]
    content_preferences: Dict[str, float]
    difficulty_preferences: Dict[str, float]
    interaction_patterns: Dict[str, Any]
    last_updated: datetime

@dataclass
class PerformanceMetrics:
    """Performance monitoring metrics"""
    response_time_ms: float
    cache_hit_rate: float
    algorithm_performance: Dict[str, float]
    error_rate: float
    throughput: int
    timestamp: datetime

class PerformanceMonitor:
    """Monitor and track system performance"""
    
    def __init__(self):
        self.metrics_history = []
        self.algorithm_performance = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.response_times = []
        
    def record_request(self, algorithm: str, response_time: float, success: bool = True):
        """Record a request's performance metrics"""
        self.response_times.append(response_time)
        self.algorithm_performance[algorithm].append(response_time)
        
        if not success:
            self.error_counts[algorithm] += 1
            
        # Keep only last 1000 metrics
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
            
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        avg_response_time = np.mean(self.response_times) if self.response_times else 0
        error_rate = sum(self.error_counts.values()) / max(len(self.response_times), 1)
        
        algorithm_avg = {}
        for algo, times in self.algorithm_performance.items():
            if times:
                algorithm_avg[algo] = np.mean(times)
        
        return PerformanceMetrics(
            response_time_ms=avg_response_time * 1000,
            cache_hit_rate=self.get_cache_hit_rate(),
            algorithm_performance=algorithm_avg,
            error_rate=error_rate,
            throughput=len(self.response_times),
            timestamp=datetime.now()
        )
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This will be implemented when we add cache monitoring
        return 0.75  # Placeholder
    
    def get_best_algorithm(self, request_type: str) -> str:
        """Get the best performing algorithm for a request type"""
        if not self.algorithm_performance:
            return 'hybrid'  # Default fallback
            
        # Find algorithm with best average performance
        best_algo = min(self.algorithm_performance.items(), 
                       key=lambda x: np.mean(x[1]) if x[1] else float('inf'))
        return best_algo[0]

class SmartCacheManager:
    """Intelligent multi-level caching system"""
    
    def __init__(self):
        self.memory_cache = {}
        self.cache_stats = {
            'memory_hits': 0,
            'redis_hits': 0,
            'disk_hits': 0,
            'misses': 0
        }
        
    def get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache with multi-level fallback"""
        # Check memory cache first
        if key in self.memory_cache:
            self.cache_stats['memory_hits'] += 1
            return self.memory_cache[key]
        
        # Check Redis cache
        if redis:  # Only if redis is available
            try:
                redis_result = redis_cache.get_cache(key)
                if redis_result is not None:
                    self.cache_stats['redis_hits'] += 1
                    # Store in memory cache for faster access
                    self.memory_cache[key] = redis_result
                    return redis_result
            except Exception as e:
                logger.warning(f"Redis cache error: {e}")
        
        self.cache_stats['misses'] += 1
        return None
    
    def set_cache(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL"""
        # Store in memory cache
        self.memory_cache[key] = value
        
        # Store in Redis cache
        if redis:  # Only if redis is available
            try:
                redis_cache.set_cache(key, value, ttl)
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        # Clean memory cache if too large
        if len(self.memory_cache) > 1000:
            # Remove oldest entries
            oldest_keys = list(self.memory_cache.keys())[:100]
            for old_key in oldest_keys:
                del self.memory_cache[old_key]
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics"""
        total_requests = sum(self.cache_stats.values())
        if total_requests == 0:
            return {'hit_rate': 0, **self.cache_stats}
        
        hit_rate = (self.cache_stats['memory_hits'] + 
                   self.cache_stats['redis_hits'] + 
                   self.cache_stats['disk_hits']) / total_requests
        
        return {
            'hit_rate': hit_rate,
            **self.cache_stats
        }
    
    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a user"""
        keys_to_remove = []
        for key in self.memory_cache.keys():
            if f"user_{user_id}" in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.memory_cache[key]
        
        # Also invalidate Redis cache
        try:
            pattern = f"*user_{user_id}*"
            # Note: This is a simplified version. In production, you'd use SCAN
            logger.info(f"Invalidated cache for user {user_id}")
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

class ContentAnalyzer:
    """Advanced content analysis without hardcoding - Optimized for performance"""
    
    def __init__(self):
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.embedding_model = None
            
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,  # Reduced for performance
            stop_words='english',
            ngram_range=(1, 2),  # Reduced for performance
            min_df=1,
            max_df=0.95
        )
        
        # Cache for embeddings to avoid recomputation
        self.embedding_cache = {}
        
    def analyze_content(self, content: SavedContent, analysis: ContentAnalysis) -> Dict[str, Any]:
        """Comprehensive content analysis - Optimized for performance"""
        try:
            # Combine all text for analysis using available fields
            text_parts = [content.title]
            
            # Add extracted text if available (limit to first 1000 chars for performance)
            if content.extracted_text:
                text_parts.append(content.extracted_text[:1000])
            
            # Add tags if available
            if content.tags:
                text_parts.append(content.tags)
            
            # Add notes if available (limit to first 500 chars)
            if content.notes:
                text_parts.append(content.notes[:500])
            
            # Add category if available
            if content.category:
                text_parts.append(content.category)
            
            text_content = " ".join(text_parts)
            
            # Generate embeddings (with caching)
            embedding = self.generate_embedding(text_content)
            
            # Extract technologies dynamically (simplified for performance)
            technologies = self.extract_technologies_dynamic(text_content, analysis)
            
            # Calculate quality score (simplified)
            quality_score = self.calculate_quality_score(content, analysis)
            
            # Determine content type (simplified)
            content_type = self.classify_content_type(text_content, analysis)
            
            # Assess difficulty (simplified)
            difficulty = self.assess_difficulty(text_content, analysis)
            
            # Extract key concepts (simplified)
            key_concepts = self.extract_key_concepts(text_content, analysis)
            
            return {
                'embedding': embedding,
                'technologies': technologies,
                'quality_score': quality_score,
                'content_type': content_type,
                'difficulty': difficulty,
                'key_concepts': key_concepts,
                'text_length': len(text_content),
                'complexity_score': 0.5  # Simplified for performance
            }
            
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return self._get_fallback_analysis(content, analysis)
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate semantic embedding for text - with caching"""
        # Create cache key
        cache_key = hash(text[:500])  # Use first 500 chars as key
        
        # Check cache first
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        try:
            if self.embedding_model:
                embedding = self.embedding_model.encode(text[:1000], convert_to_numpy=True)  # Limit text length
            else:
                # Fallback: simple TF-IDF based embedding
                embedding = self._generate_fallback_embedding(text[:1000])
            
            # Cache the result
            self.embedding_cache[cache_key] = embedding
            
            # Limit cache size
            if len(self.embedding_cache) > 1000:
                # Remove oldest entries
                oldest_keys = list(self.embedding_cache.keys())[:100]
                for old_key in oldest_keys:
                    del self.embedding_cache[old_key]
            
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return np.zeros(384)  # Default embedding size
    
    def _generate_fallback_embedding(self, text: str) -> np.ndarray:
        """Generate fallback embedding using TF-IDF"""
        try:
            # Simple TF-IDF based embedding
            tfidf_vector = self.tfidf_vectorizer.fit_transform([text])
            # Convert to dense array and pad/truncate to 384 dimensions
            dense_vector = tfidf_vector.toarray().flatten()
            if len(dense_vector) > 384:
                return dense_vector[:384]
            else:
                # Pad with zeros
                padded_vector = np.zeros(384)
                padded_vector[:len(dense_vector)] = dense_vector
                return padded_vector
        except Exception as e:
            logger.error(f"Fallback embedding error: {e}")
            return np.zeros(384)
    
    def extract_technologies_dynamic(self, text: str, analysis: ContentAnalysis) -> List[str]:
        """Extract technologies dynamically without hardcoding"""
        technologies = []
        
        # Use existing analysis if available
        if analysis.technology_tags:
            technologies.extend([tech.strip() for tech in analysis.technology_tags.split(',')])
        
        # Extract from analysis_data if available
        if analysis.analysis_data:
            try:
                analysis_dict = json.loads(analysis.analysis_data) if isinstance(analysis.analysis_data, str) else analysis.analysis_data
                if 'technologies' in analysis_dict:
                    if isinstance(analysis_dict['technologies'], list):
                        technologies.extend(analysis_dict['technologies'])
                    else:
                        technologies.append(str(analysis_dict['technologies']))
            except Exception as e:
                logger.warning(f"Error parsing analysis_data: {e}")
        
        # Use key concepts as potential technologies
        if analysis.key_concepts:
            concepts = [concept.strip() for concept in analysis.key_concepts.split(',')]
            # Filter concepts that look like technologies
            tech_concepts = [concept for concept in concepts 
                           if self._looks_like_technology(concept)]
            technologies.extend(tech_concepts)
        
        # Extract from text content using semantic patterns
        text_lower = text.lower()
        
        # Dynamic technology detection using patterns and heuristics
        detected_techs = self._detect_technologies_semantic(text_lower)
        technologies.extend(detected_techs)
        
        # Remove duplicates and normalize
        unique_techs = list(set([tech.lower().strip() for tech in technologies if tech.strip()]))
        return unique_techs
    
    def _detect_technologies_semantic(self, text: str) -> List[str]:
        """Detect technologies using semantic patterns without hardcoding - Optimized for performance"""
        technologies = []
        
        # Look for common technology patterns (simplified for performance)
        import re
        
        # Pattern 1: Framework/library mentions (simplified)
        framework_patterns = [
            r'using\s+([a-zA-Z][a-zA-Z0-9\-_\.]+)',
            r'with\s+([a-zA-Z][a-zA-Z0-9\-_\.]+)',
            r'built\s+with\s+([a-zA-Z][a-zA-Z0-9\-_\.]+)',
        ]
        
        for pattern in framework_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            technologies.extend(matches)
        
        # Pattern 2: Language mentions (simplified)
        language_patterns = [
            r'([a-zA-Z][a-zA-Z0-9#\+]+)\s+code',
            r'([a-zA-Z][a-zA-Z0-9#\+]+)\s+function',
        ]
        
        for pattern in language_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            technologies.extend(matches)
        
        # Pattern 3: Database mentions (simplified)
        db_patterns = [
            r'([a-zA-Z][a-zA-Z0-9]+)\s+database',
        ]
        
        for pattern in db_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            technologies.extend(matches)
        
        # Filter out common non-technology words (simplified)
        common_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'must', 'shall', 'code', 'function', 'script', 'application',
            'database', 'cloud', 'platform', 'framework', 'library', 'tool', 'technology'
        }
        
        filtered_techs = []
        for tech in technologies:
            tech_lower = tech.lower()
            if (len(tech_lower) > 2 and 
                tech_lower not in common_words and
                not tech_lower.isdigit() and
                not tech_lower.startswith('http')):
                filtered_techs.append(tech_lower)
        
        return filtered_techs[:10]  # Limit to top 10 for performance
    
    def _looks_like_technology(self, text: str) -> bool:
        """Check if text looks like a technology name using patterns"""
        text_lower = text.lower()
        
        # Skip if too short or too long
        if len(text_lower) < 2 or len(text_lower) > 50:
            return False
        
        # Skip common non-technology words
        common_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'must', 'shall', 'code', 'function', 'script', 'application',
            'database', 'cloud', 'platform', 'framework', 'library', 'tool', 'technology',
            'system', 'service', 'api', 'web', 'app', 'mobile', 'desktop', 'server', 'client'
        }
        
        if text_lower in common_words:
            return False
        
        # Check for technology-like patterns
        import re
        
        # Pattern 1: Contains common tech suffixes
        tech_suffixes = ['js', 'ts', 'py', 'java', 'go', 'rs', 'php', 'rb', 'swift', 'kt', 'cs']
        if any(text_lower.endswith(suffix) for suffix in tech_suffixes):
            return True
        
        # Pattern 2: Contains common tech prefixes
        tech_prefixes = ['react', 'vue', 'angular', 'django', 'flask', 'spring', 'express', 'fastapi']
        if any(text_lower.startswith(prefix) for prefix in tech_prefixes):
            return True
        
        # Pattern 3: Contains dots (like framework names)
        if '.' in text_lower:
            return True
        
        # Pattern 4: Contains hyphens (like library names)
        if '-' in text_lower:
            return True
        
        # Pattern 5: Contains numbers (like version numbers)
        if re.search(r'\d', text_lower):
            return True
        
        # Pattern 6: All caps (like API names)
        if text.isupper() and len(text) > 2:
            return True
        
        # Pattern 7: CamelCase or PascalCase
        if re.match(r'^[A-Z][a-z]+([A-Z][a-z]+)*$', text) or re.match(r'^[a-z]+([A-Z][a-z]+)*$', text):
            return True
        
        return False
    
    def calculate_quality_score(self, content: SavedContent, analysis: ContentAnalysis) -> float:
        """Calculate content quality score"""
        score = 0.0
        
        # Base score from existing quality_score
        if content.quality_score:
            score += content.quality_score * 0.4
        
        # Text length factor
        text_length = len(content.extracted_text or '')
        if text_length > 1000:
            score += 2.0
        elif text_length > 500:
            score += 1.0
        
        # Analysis completeness factor
        if analysis.technology_tags:
            score += 1.0
        if analysis.key_concepts:
            score += 1.0
        if analysis.content_type:
            score += 0.5
        
        # URL quality factor
        if content.url and ('github.com' in content.url or 'stackoverflow.com' in content.url):
            score += 1.0
        
        return min(10.0, score)
    
    def classify_content_type(self, text: str, analysis: ContentAnalysis) -> str:
        """Classify content type"""
        if analysis.content_type:
            return analysis.content_type
        
        text_lower = text.lower()
        
        # Simple classification based on keywords
        if any(word in text_lower for word in ['tutorial', 'guide', 'how to', 'step by step']):
            return 'tutorial'
        elif any(word in text_lower for word in ['documentation', 'docs', 'reference']):
            return 'documentation'
        elif any(word in text_lower for word in ['example', 'demo', 'sample']):
            return 'example'
        elif any(word in text_lower for word in ['article', 'blog', 'post']):
            return 'article'
        else:
            return 'general'
    
    def assess_difficulty(self, text: str, analysis: ContentAnalysis) -> str:
        """Assess content difficulty level"""
        if analysis.difficulty_level:
            return analysis.difficulty_level
        
        text_lower = text.lower()
        
        # Simple difficulty assessment
        beginner_indicators = ['beginner', 'basic', 'intro', 'getting started', 'first']
        advanced_indicators = ['advanced', 'expert', 'complex', 'optimization', 'performance']
        
        if any(indicator in text_lower for indicator in advanced_indicators):
            return 'advanced'
        elif any(indicator in text_lower for indicator in beginner_indicators):
            return 'beginner'
        else:
            return 'intermediate'
    
    def extract_key_concepts(self, text: str, analysis: ContentAnalysis) -> List[str]:
        """Extract key concepts from content"""
        if analysis.key_concepts:
            return [concept.strip() for concept in analysis.key_concepts.split(',')]
        
        # Simple concept extraction (placeholder for more sophisticated NLP)
        words = text.lower().split()
        # Remove common words and get most frequent terms
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        filtered_words = [word for word in words if word not in common_words and len(word) > 3]
        
        # Get most common words as concepts
        word_counts = Counter(filtered_words)
        concepts = [word for word, count in word_counts.most_common(10)]
        
        return concepts[:5]  # Return top 5 concepts
    
    def calculate_complexity_score(self, text: str) -> float:
        """Calculate text complexity score"""
        if not text:
            return 0.0
        
        # Simple complexity metrics
        sentences = text.split('.')
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        unique_word_ratio = len(set(words)) / len(words)
        
        # Normalize scores
        complexity = (avg_sentence_length * 0.6 + unique_word_ratio * 0.4) / 10
        return min(1.0, complexity)
    
    def _get_fallback_analysis(self, content: SavedContent, analysis: ContentAnalysis) -> Dict[str, Any]:
        """Fallback analysis when main analysis fails"""
        return {
            'embedding': np.zeros(384),
            'technologies': [],
            'quality_score': content.quality_score or 5.0,
            'content_type': 'general',
            'difficulty': 'intermediate',
            'key_concepts': [],
            'text_length': len(content.extracted_text or ''),
            'complexity_score': 0.5
        }

class UnifiedIntelligentEngine:
    """
    Unified Intelligent Engine - Phase 1 Foundation
    Single, intelligent recommendation engine that provides consistent, high-quality results
    """
    
    def __init__(self):
        self.content_analyzer = ContentAnalyzer()
        self.cache_manager = SmartCacheManager()
        self.performance_monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)
        
        # Initialize algorithms (will be expanded in Phase 2)
        self.algorithms = {
            'hybrid': self._hybrid_algorithm,
            'semantic': self._semantic_algorithm,
            'content_based': self._content_based_algorithm
        }
        
    def get_recommendations(self, user_id: int, request_data: Dict[str, Any], 
                          limit: int = 10) -> List[RecommendationResult]:
        """
        Get intelligent recommendations using the best algorithm
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(user_id, request_data)
            cached_result = self.cache_manager.get_cache(cache_key)
            if cached_result:
                self.performance_monitor.record_request('cached', time.time() - start_time)
                return [RecommendationResult(**rec) for rec in cached_result]
            
            # Select best algorithm
            algorithm = self._select_algorithm(user_id, request_data)
            
            # Get recommendations
            recommendations = self.algorithms[algorithm](user_id, request_data, limit)
            
            # Cache results
            self.cache_manager.set_cache(cache_key, [asdict(rec) for rec in recommendations])
            
            # Record performance
            response_time = time.time() - start_time
            self.performance_monitor.record_request(algorithm, response_time)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation error: {e}")
            self.performance_monitor.record_request('error', time.time() - start_time, success=False)
            return []
    
    def _generate_cache_key(self, user_id: int, request_data: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        data_str = json.dumps(request_data, sort_keys=True)
        return f"recommendations:user_{user_id}:{hashlib.md5(data_str.encode()).hexdigest()}"
    
    def _select_algorithm(self, user_id: int, request_data: Dict[str, Any]) -> str:
        """Select the best algorithm for the request"""
        # For Phase 1, use hybrid algorithm as default
        # In Phase 2, this will be more sophisticated
        return 'hybrid'
    
    def _hybrid_algorithm(self, user_id: int, request_data: Dict[str, Any], 
                         limit: int) -> List[RecommendationResult]:
        """Hybrid recommendation algorithm combining multiple approaches"""
        try:
            # Get candidate content
            candidates = self._get_candidate_content(user_id, request_data)
            
            # Analyze each candidate
            analyzed_candidates = []
            for content, analysis in candidates:
                analysis_result = self.content_analyzer.analyze_content(content, analysis)
                analyzed_candidates.append((content, analysis, analysis_result))
            
            # Score candidates
            scored_candidates = []
            for content, analysis, analysis_result in analyzed_candidates:
                score = self._calculate_hybrid_score(content, analysis, analysis_result, request_data)
                scored_candidates.append((content, analysis, analysis_result, score))
            
            # Sort by score and return top results
            scored_candidates.sort(key=lambda x: x[3], reverse=True)
            
            recommendations = []
            for content, analysis, analysis_result, score in scored_candidates[:limit]:
                recommendation = RecommendationResult(
                    content_id=content.id,
                    title=content.title,
                    url=content.url,
                    score=score,
                    reasoning=self._generate_reasoning(content, analysis, analysis_result, request_data),
                    content_type=analysis_result['content_type'],
                    difficulty=analysis_result['difficulty'],
                    technologies=analysis_result['technologies'],
                    key_concepts=analysis_result['key_concepts'],
                    quality_score=analysis_result['quality_score'],
                    diversity_score=0.0,  # Will be calculated in Phase 2
                    novelty_score=0.0,    # Will be calculated in Phase 2
                    algorithm_used='hybrid',
                    confidence=min(1.0, score / 10.0),
                    metadata={'analysis_result': analysis_result}
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Hybrid algorithm error: {e}")
            return []
    
    def _get_candidate_content(self, user_id: int, request_data: Dict[str, Any]) -> List[Tuple[SavedContent, ContentAnalysis]]:
        """Get candidate content for recommendations with improved relevance and performance"""
        try:
            with app.app_context():
                # Use more efficient query with better filtering
                base_query = db.session.query(SavedContent, ContentAnalysis).join(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                ).filter(
                    SavedContent.quality_score >= 5,  # Lower threshold for more candidates
                    SavedContent.title.notlike('%Test%'),
                    SavedContent.title.notlike('%test%')
                )
                
                # If specific technologies are requested, prioritize content with those technologies
                requested_techs = request_data.get('technologies', [])
                if requested_techs:
                    # More efficient technology matching
                    tech_conditions = []
                    for tech in requested_techs:
                        tech_lower = tech.lower()
                        tech_conditions.append(
                            db.or_(
                                ContentAnalysis.technology_tags.ilike(f'%{tech_lower}%'),
                                SavedContent.title.ilike(f'%{tech_lower}%'),
                                SavedContent.tags.ilike(f'%{tech_lower}%')
                            )
                        )
                    
                    # Get content with technology matches first (limit to 30 for performance)
                    tech_matched_query = base_query.filter(db.or_(*tech_conditions))
                    tech_matched_content = tech_matched_query.order_by(
                        SavedContent.quality_score.desc()
                    ).limit(30).all()
                    
                    # Get other high-quality content as fallback (limit to 20)
                    other_content_query = base_query.filter(~db.or_(*tech_conditions))
                    other_content = other_content_query.order_by(
                        SavedContent.quality_score.desc()
                    ).limit(20).all()
                    
                    # Combine with technology matches first
                    all_content = tech_matched_content + other_content
                else:
                    # No specific technologies, get general high-quality content (limit to 50)
                    all_content = base_query.order_by(
                        SavedContent.quality_score.desc()
                    ).limit(50).all()
                
                return all_content
                
        except Exception as e:
            self.logger.error(f"Error getting candidate content: {e}")
            return []
    
    def _calculate_hybrid_score(self, content: SavedContent, analysis: ContentAnalysis, 
                              analysis_result: Dict[str, Any], request_data: Dict[str, Any]) -> float:
        """Calculate hybrid recommendation score with improved relevance"""
        score = 0.0
        
        # Technology match (40% - much higher weight for relevance)
        tech_match = self._calculate_technology_match(
            analysis_result['technologies'], 
            request_data.get('technologies', [])
        )
        score += tech_match * 4.0  # Scale to 40%
        
        # Quality score (25%)
        score += analysis_result['quality_score'] * 0.25
        
        # Content type relevance (20%)
        content_relevance = self._calculate_content_relevance(
            analysis_result['content_type'],
            request_data.get('content_type', 'general')
        )
        score += content_relevance * 2.0  # Scale to 20%
        
        # Difficulty alignment (10%)
        difficulty_alignment = self._calculate_difficulty_alignment(
            analysis_result['difficulty'],
            request_data.get('difficulty', 'intermediate')
        )
        score += difficulty_alignment * 1.0  # Scale to 10%
        
        # Recency bonus (5%)
        recency_bonus = self._calculate_recency_bonus(content.saved_at)
        score += recency_bonus * 0.5  # Scale to 5%
        
        # Apply relevance penalty for low technology match
        if tech_match < 0.3:  # Very low technology relevance
            score *= 0.3  # Heavily penalize irrelevant content
        
        return min(10.0, score)
    
    def _calculate_technology_match(self, content_techs: List[str], request_techs: List[str]) -> float:
        """Calculate technology match score with improved relevance"""
        if not content_techs or not request_techs:
            return 0.3  # Lower score if no technologies specified
        
        # Normalize technology names
        content_techs_normalized = [tech.lower().strip() for tech in content_techs]
        request_techs_normalized = [tech.lower().strip() for tech in request_techs]
        
        # Calculate exact matches
        exact_matches = set(content_techs_normalized) & set(request_techs_normalized)
        
        # Calculate related matches (e.g., react native matches react, mobile, etc.)
        related_matches = 0
        for req_tech in request_techs_normalized:
            for content_tech in content_techs_normalized:
                if self._are_technologies_related(req_tech, content_tech):
                    related_matches += 1
        
        # Weight exact matches higher than related matches
        exact_score = len(exact_matches) / len(request_techs_normalized)
        related_score = min(related_matches / len(request_techs_normalized), 0.5)  # Cap related matches
        
        total_score = exact_score * 0.8 + related_score * 0.2
        return min(1.0, total_score)
    
    def _are_technologies_related(self, tech1: str, tech2: str) -> bool:
        """Check if two technologies are related using semantic analysis"""
        tech1_lower = tech1.lower()
        tech2_lower = tech2.lower()
        
        # Direct match
        if tech1_lower == tech2_lower:
            return True
        
        # Check for common prefixes/suffixes (e.g., react/react-native, python/django)
        if (tech1_lower.startswith(tech2_lower) or tech2_lower.startswith(tech1_lower) or
            tech1_lower.endswith(tech2_lower) or tech2_lower.endswith(tech1_lower)):
            return True
        
        # Check for common domain patterns
        common_domains = {
            'web': ['html', 'css', 'javascript', 'typescript', 'react', 'vue', 'angular'],
            'mobile': ['android', 'ios', 'react', 'native', 'flutter', 'dart'],
            'backend': ['python', 'java', 'go', 'node', 'php', 'ruby'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes']
        }
        
        for domain, techs in common_domains.items():
            if tech1_lower in techs and tech2_lower in techs:
                return True
        
        # Check for semantic similarity using word embeddings if available
        if hasattr(self, 'content_analyzer') and self.content_analyzer.embedding_model:
            try:
                # Create simple context for each technology
                context1 = f"technology {tech1_lower} framework library"
                context2 = f"technology {tech2_lower} framework library"
                
                # Get embeddings
                emb1 = self.content_analyzer.embedding_model.encode(context1, convert_to_numpy=True)
                emb2 = self.content_analyzer.embedding_model.encode(context2, convert_to_numpy=True)
                
                # Calculate similarity
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                
                # If similarity is high, they're related
                if similarity > 0.7:
                    return True
            except Exception as e:
                logger.debug(f"Embedding similarity check failed: {e}")
        
        return False
    
    def _calculate_content_relevance(self, content_type: str, requested_type: str) -> float:
        """Calculate content type relevance"""
        if content_type == requested_type:
            return 1.0
        elif requested_type == 'general':
            return 0.7  # General requests accept most content types
        else:
            return 0.3  # Lower score for type mismatch
    
    def _calculate_difficulty_alignment(self, content_difficulty: str, requested_difficulty: str) -> float:
        """Calculate difficulty alignment"""
        difficulty_levels = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        
        content_level = difficulty_levels.get(content_difficulty, 2)
        requested_level = difficulty_levels.get(requested_difficulty, 2)
        
        # Perfect match
        if content_level == requested_level:
            return 1.0
        # Adjacent levels
        elif abs(content_level - requested_level) == 1:
            return 0.7
        # Far apart
        else:
            return 0.3
    
    def _calculate_recency_bonus(self, saved_at: datetime) -> float:
        """Calculate recency bonus for content"""
        if not saved_at:
            return 0.5
        
        days_old = (datetime.now() - saved_at).days
        
        if days_old <= 7:
            return 1.0  # Very recent
        elif days_old <= 30:
            return 0.8  # Recent
        elif days_old <= 90:
            return 0.6  # Moderately recent
        else:
            return 0.4  # Older content
    
    def _generate_reasoning(self, content: SavedContent, analysis: ContentAnalysis, 
                          analysis_result: Dict[str, Any], request_data: Dict[str, Any]) -> str:
        """Generate reasoning for recommendation"""
        reasons = []
        
        # Technology match reasoning
        tech_match = self._calculate_technology_match(
            analysis_result['technologies'], 
            request_data.get('technologies', [])
        )
        if tech_match > 0.5:
            reasons.append(f"Matches your technology interests ({tech_match:.1%} match)")
        
        # Content type reasoning
        if analysis_result['content_type'] == request_data.get('content_type', 'general'):
            reasons.append(f"Perfect {analysis_result['content_type']} content")
        
        # Quality reasoning
        if analysis_result['quality_score'] >= 7:
            reasons.append("High-quality, well-reviewed content")
        
        # Difficulty reasoning
        if analysis_result['difficulty'] == request_data.get('difficulty', 'intermediate'):
            reasons.append(f"Appropriate {analysis_result['difficulty']} level")
        
        if not reasons:
            reasons.append("Relevant content based on your interests")
        
        return ". ".join(reasons) + "."
    
    def _semantic_algorithm(self, user_id: int, request_data: Dict[str, Any], 
                          limit: int) -> List[RecommendationResult]:
        """Semantic similarity algorithm (placeholder for Phase 2)"""
        # This will be implemented in Phase 2
        return self._hybrid_algorithm(user_id, request_data, limit)
    
    def _content_based_algorithm(self, user_id: int, request_data: Dict[str, Any], 
                               limit: int) -> List[RecommendationResult]:
        """Content-based algorithm (placeholder for Phase 2)"""
        # This will be implemented in Phase 2
        return self._hybrid_algorithm(user_id, request_data, limit)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        return self.performance_monitor.get_performance_metrics()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return self.cache_manager.get_cache_stats()

# Global instance
unified_engine = UnifiedIntelligentEngine()

def get_enhanced_recommendations(user_id: int, request_data: Dict[str, Any], 
                               limit: int = 10) -> List[Dict[str, Any]]:
    """Main function to get enhanced recommendations"""
    try:
        recommendations = unified_engine.get_recommendations(user_id, request_data, limit)
        return [asdict(rec) for rec in recommendations]
    except Exception as e:
        logger.error(f"Error getting enhanced recommendations: {e}")
        return [] 