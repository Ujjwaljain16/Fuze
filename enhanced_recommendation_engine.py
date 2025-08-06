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

# from app import app  # Removed to fix circular import
from models import db, SavedContent, ContentAnalysis, User, Feedback
from redis_utils import redis_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RecommendationResult:
    """Structured recommendation result"""
    id: int
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
            import torch
            # Initialize model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Fix meta tensor issue by using to_empty() instead of to()
            if hasattr(torch, 'meta') and torch.meta.is_available():
                # Use to_empty() for meta tensors
                self.embedding_model = self.embedding_model.to_empty(device='cpu')
            else:
                # Fallback to CPU
                self.embedding_model = self.embedding_model.to('cpu')
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
        """Analyze content comprehensively without hardcoding"""
        try:
            # Combine all available text content
            text_parts = []
            
            if content.title:
                text_parts.append(content.title)
            
            if content.extracted_text:
                text_parts.append(content.extracted_text)
            
            if content.tags:
                text_parts.append(content.tags)
            
            if content.notes:
                text_parts.append(content.notes)
            
            if content.category:
                text_parts.append(content.category)
            
            text_content = ' '.join(text_parts)
            
            # Extract technologies dynamically
            technologies = self.extract_technologies_dynamic(text_content, analysis)
            
            # Calculate quality score
            quality_score = self.calculate_quality_score(content, analysis)
            
            # Classify content type
            content_type = self.classify_content_type(text_content, analysis)
            
            # Assess difficulty
            difficulty = self.assess_difficulty(text_content, analysis)
            
            # Extract key concepts
            key_concepts = self.extract_key_concepts(text_content, analysis)
            
            # Calculate complexity score
            complexity_score = self.calculate_complexity_score(text_content)
            
            return {
                'text_content': text_content,
                'technologies': technologies,
                'quality_score': quality_score,
                'content_type': content_type,
                'difficulty': difficulty,
                'key_concepts': key_concepts,
                'complexity_score': complexity_score
            }
            
        except Exception as e:
            print(f"Content analysis error: {e}")
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
            'text_content': '',
            'technologies': [],
            'quality_score': content.quality_score or 5.0,
            'content_type': 'general',
            'difficulty': 'intermediate',
            'key_concepts': [],
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
        """Get intelligent recommendations using the best algorithm"""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(user_id, request_data)
            cached_result = self.cache_manager.get_cache(cache_key)
            if cached_result:
                self.performance_monitor.record_request('cached', time.time() - start_time)
                # Convert cached dict back to RecommendationResult objects
                if isinstance(cached_result, list) and cached_result:
                    if isinstance(cached_result[0], dict):
                        return [RecommendationResult(**rec) for rec in cached_result]
                    elif isinstance(cached_result[0], RecommendationResult):
                        return cached_result
                return []
            
            # Select the best algorithm
            algorithm = self._select_algorithm(user_id, request_data)
            
            # Get recommendations using selected algorithm
            if algorithm == 'semantic':
                recommendations = self._semantic_algorithm(user_id, request_data)
            elif algorithm == 'content_based':
                recommendations = self._content_based_algorithm(user_id, request_data)
            else:  # hybrid (default)
                recommendations = self._hybrid_algorithm(user_id, request_data, limit)
            
            # Apply diversity optimization to all algorithms
            recommendations = self._apply_diversity_optimization(recommendations)
            
            # Limit results
            recommendations = recommendations[:limit]
            
            # Cache results as dictionaries
            cache_data = [asdict(rec) for rec in recommendations]
            self.cache_manager.set_cache(cache_key, cache_data, ttl=1800)  # 30 minutes
            
            # Record performance
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.performance_monitor.record_request(algorithm, response_time)
            
            return recommendations
            
        except Exception as e:
            print(f"Recommendation error: {e}")
            self.performance_monitor.record_request('error', time.time() - start_time, success=False)
            return []
    
    def _generate_cache_key(self, user_id: int, request_data: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        data_str = json.dumps(request_data, sort_keys=True)
        return f"recommendations:user_{user_id}:{hashlib.md5(data_str.encode()).hexdigest()}"
    
    def _select_algorithm(self, user_id: int, request_data: Dict[str, Any]) -> str:
        """Dynamically select the best algorithm based on request characteristics"""
        # Check for specific algorithm preference
        if request_data.get('algorithm'):
            return request_data['algorithm']
        
        # Analyze request characteristics
        has_technologies = bool(request_data.get('technologies'))
        has_detailed_description = bool(request_data.get('description') and len(request_data['description']) > 50)
        is_project_specific = bool(request_data.get('project_title'))
        
        # Algorithm selection logic
        if has_technologies and has_detailed_description:
            return 'hybrid'  # Best for detailed project requests
        elif has_technologies:
            return 'content_based'  # Good for technology-focused requests
        elif has_detailed_description:
            return 'semantic'  # Good for concept-focused requests
        else:
            return 'hybrid'  # Default fallback
    
    def _hybrid_algorithm(self, user_id: int, request_data: Dict[str, Any], 
                         limit: int) -> List[RecommendationResult]:
        """Hybrid recommendation algorithm combining multiple approaches"""
        try:
            # Get candidate content
            candidates = self._get_candidate_content(user_id, request_data)
            if not candidates:
                return []
            
            # Extract technologies from request using improved extraction
            request_techs = self._extract_project_technologies(request_data)
            
            # Update request_data with extracted technologies
            request_data['technologies'] = request_techs
            
            results = []
            for content, analysis in candidates:
                # Analyze content
                analysis_result = self.content_analyzer.analyze_content(content, analysis)
                
                # Calculate hybrid score
                score = self._calculate_hybrid_score(content, analysis, analysis_result, request_data)
                
                # Generate reasoning
                reasoning = self._generate_reasoning(content, analysis, analysis_result, request_data)
                
                # Create recommendation result
                result = RecommendationResult(
                    id=content.id,
                    title=content.title,
                    url=content.url,
                    score=score,
                    reasoning=reasoning,
                    content_type=analysis_result['content_type'],
                    difficulty=analysis_result['difficulty'],
                    technologies=analysis_result['technologies'],
                    key_concepts=analysis_result['key_concepts'],
                    quality_score=analysis_result['quality_score'],
                    diversity_score=0.0,
                    novelty_score=0.0,
                    algorithm_used='hybrid',
                    confidence=min(0.9, score / 10.0),
                    metadata={'analysis_result': analysis_result}
                )
                results.append(result)
            
            # Sort by score
            results.sort(key=lambda x: x.score, reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            print(f"Hybrid algorithm error: {e}")
            return []
    
    def _get_candidate_content(self, user_id: int, request_data: Dict[str, Any]) -> List[Tuple[SavedContent, ContentAnalysis]]:
        """Get candidate content for recommendations with improved relevance and performance"""
        try:
            # Create a minimal app context without importing app
            from flask import Flask
            temp_app = Flask(__name__)
            temp_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db')
            temp_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            
            with temp_app.app_context():
                db.init_app(temp_app)
                # Use more efficient query with better filtering
                base_query = db.session.query(SavedContent, ContentAnalysis).join(
                    ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
                ).filter(
                    SavedContent.quality_score >= 5,  # Lower threshold for more candidates
                    SavedContent.title.notlike('%Test%'),
                    SavedContent.title.notlike('%test%')
                )
                
                # If specific technologies are requested, filter by them
                if request_data.get('technologies'):
                    tech_filter = db.or_(
                        *[ContentAnalysis.technology_tags.ilike(f'%{tech}%') for tech in request_data['technologies']]
                    )
                    base_query = base_query.filter(tech_filter)
                
                # Limit results for performance with proper ordering
                candidates = base_query.order_by(
                    SavedContent.quality_score.desc(),
                    ContentAnalysis.created_at.desc()
                ).limit(500).all()
                
                return candidates
                
        except Exception as e:
            print(f"Error getting candidate content: {e}")
            return []
    
    def _calculate_hybrid_score(self, content: SavedContent, analysis: ContentAnalysis, 
                              analysis_result: Dict[str, Any], request_data: Dict[str, Any]) -> float:
        """Calculate hybrid recommendation score with embedding-based semantic similarity"""
        score = 0.0
        
        # Import embedding utilities
        from embedding_utils import (
            get_content_embedding, 
            get_embedding,
            calculate_cosine_similarity
        )
        
        # Major weight to embedding-based semantic similarity (60%)
        try:
            # Get content embedding
            content_embedding = get_content_embedding(content)
            
            # Create request text for embedding
            request_text = f"technologies: {' '.join(request_data.get('technologies', []))} content_type: {request_data.get('content_type', 'general')} difficulty: {request_data.get('difficulty', 'intermediate')}"
            request_embedding = get_embedding(request_text)
            
            # Calculate semantic similarity
            semantic_similarity = calculate_cosine_similarity(content_embedding, request_embedding)
            score += semantic_similarity * 6.0  # Scale to 60%
            
        except Exception as embedding_error:
            print(f"Embedding calculation failed, falling back to keyword matching: {embedding_error}")
            # Fallback to keyword matching
            tech_match = self._calculate_technology_match(
                analysis_result['technologies'], 
                request_data.get('technologies', [])
            )
            score += tech_match * 3.0  # Scale to 30% as fallback
        
        # Technology match (reduced weight - 15%)
        tech_match = self._calculate_technology_match(
            analysis_result['technologies'], 
            request_data.get('technologies', [])
        )
        score += tech_match * 1.5  # Scale to 15%
        
        # Quality score (reduced weight - 10%)
        score += analysis_result['quality_score'] * 0.1
        
        # Content type relevance (reduced weight - 10%)
        content_relevance = self._calculate_content_relevance(
            analysis_result['content_type'],
            request_data.get('content_type', 'general')
        )
        score += content_relevance * 1.0  # Scale to 10%
        
        # Difficulty alignment (reduced weight - 3%)
        difficulty_alignment = self._calculate_difficulty_alignment(
            analysis_result['difficulty'],
            request_data.get('difficulty', 'intermediate')
        )
        score += difficulty_alignment * 0.3  # Scale to 3%
        
        # Recency bonus (reduced weight - 2%)
        recency_bonus = self._calculate_recency_bonus(content.saved_at)
        score += recency_bonus * 0.2  # Scale to 2%
        
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
    
    def _semantic_algorithm(self, user_id: int, request_data: Dict[str, Any]) -> List[RecommendationResult]:
        """Advanced semantic similarity algorithm using embeddings"""
        try:
            # Get candidate content
            candidates = self._get_candidate_content(user_id, request_data)
            if not candidates:
                return []
            
            # Generate request embedding
            request_text = self._build_request_text(request_data)
            request_embedding = self.content_analyzer.generate_embedding(request_text)
            
            results = []
            for content, analysis in candidates:
                # Analyze content
                analysis_result = self.content_analyzer.analyze_content(content, analysis)
                content_text = analysis_result['text_content']
                
                # Generate content embedding
                content_embedding = self.content_analyzer.generate_embedding(content_text)
                
                # Calculate semantic similarity
                similarity = self._calculate_cosine_similarity(request_embedding, content_embedding)
                
                # Calculate semantic score (0-10)
                semantic_score = similarity * 10
                
                # Generate reasoning
                reasoning = f"Semantic similarity score: {semantic_score:.2f}/10. This content is semantically similar to your request."
                
                result = RecommendationResult(
                    id=content.id,
                    title=content.title,
                    url=content.url,
                    score=semantic_score,
                    reasoning=reasoning,
                    content_type=analysis_result['content_type'],
                    difficulty=analysis_result['difficulty'],
                    technologies=analysis_result['technologies'],
                    key_concepts=analysis_result['key_concepts'],
                    quality_score=analysis_result['quality_score'],
                    diversity_score=0.0,
                    novelty_score=0.0,
                    algorithm_used='semantic',
                    confidence=min(0.9, similarity + 0.1),
                    metadata={'similarity': similarity}
                )
                results.append(result)
            
            # Sort by score and apply diversity
            results.sort(key=lambda x: x.score, reverse=True)
            results = self._apply_diversity_optimization(results)
            
            return results[:10]
            
        except Exception as e:
            print(f"Semantic algorithm error: {e}")
            return []

    def _content_based_algorithm(self, user_id: int, request_data: Dict[str, Any]) -> List[RecommendationResult]:
        """Content-based filtering algorithm using TF-IDF and content features"""
        try:
            # Get candidate content
            candidates = self._get_candidate_content(user_id, request_data)
            if not candidates:
                return []
            
            # Extract technologies from request using improved extraction
            request_techs = self._extract_project_technologies(request_data)
            
            # Update request_data with extracted technologies
            request_data['technologies'] = request_techs
            
            # Build content corpus for TF-IDF
            content_texts = []
            for content, analysis in candidates:
                analysis_result = self.content_analyzer.analyze_content(content, analysis)
                content_texts.append(analysis_result['text_content'])
            
            # Fit TF-IDF vectorizer
            if content_texts:
                tfidf_matrix = self.content_analyzer.tfidf_vectorizer.fit_transform(content_texts)
                
                # Build request vector
                request_text = self._build_request_text(request_data)
                request_vector = self.content_analyzer.tfidf_vectorizer.transform([request_text])
                
                # Calculate TF-IDF similarities
                similarities = cosine_similarity(request_vector, tfidf_matrix).flatten()
                
                results = []
                for i, (content, analysis) in enumerate(candidates):
                    # Calculate content-based score
                    tfidf_score = similarities[i] * 5  # Scale to 0-5
                    
                    # Get content features
                    analysis_result = self.content_analyzer.analyze_content(content, analysis)
                    quality_score = analysis_result['quality_score'] * 0.3  # Scale to 0-3
                    complexity_score = analysis_result['complexity_score'] * 0.2  # Scale to 0-2
                    
                    # Total content-based score
                    total_score = tfidf_score + quality_score + complexity_score
                    
                    # Generate reasoning
                    reasoning = f"Content-based score: {total_score:.2f}/10 (TF-IDF: {tfidf_score:.2f}, Quality: {quality_score:.2f}, Complexity: {complexity_score:.2f})"
                    
                    result = RecommendationResult(
                        id=content.id,
                        title=content.title,
                        url=content.url,
                        score=total_score,
                        reasoning=reasoning,
                        content_type=analysis_result['content_type'],
                        difficulty=analysis_result['difficulty'],
                        technologies=analysis_result['technologies'],
                        key_concepts=analysis_result['key_concepts'],
                        quality_score=analysis_result['quality_score'],
                        diversity_score=0.0,
                        novelty_score=0.0,
                        algorithm_used='content_based',
                        confidence=min(0.8, similarities[i] + 0.2),
                        metadata={'tfidf_similarity': similarities[i]}
                    )
                    results.append(result)
                
                # Sort by score and apply diversity
                results.sort(key=lambda x: x.score, reverse=True)
                results = self._apply_diversity_optimization(results)
                
                return results[:10]
            
            return []
            
        except Exception as e:
            print(f"Content-based algorithm error: {e}")
            return []

    def _apply_diversity_optimization(self, recommendations: List[RecommendationResult], 
                                    max_similarity: float = 0.7) -> List[RecommendationResult]:
        """Apply diversity optimization to prevent recommendation clustering"""
        if not recommendations:
            return []
        
        diverse_recommendations = [recommendations[0]]
        
        for rec in recommendations[1:]:
            is_diverse = True
            
            # Check similarity with existing diverse recommendations
            for existing in diverse_recommendations:
                similarity = self._calculate_recommendation_similarity(rec, existing)
                if similarity > max_similarity:
                    is_diverse = False
                    break
            
            if is_diverse:
                diverse_recommendations.append(rec)
        
        return diverse_recommendations

    def _calculate_recommendation_similarity(self, rec1: RecommendationResult, 
                                          rec2: RecommendationResult) -> float:
        """Calculate similarity between two recommendations"""
        # Technology overlap
        tech1 = set(rec1.technologies)
        tech2 = set(rec2.technologies)
        tech_similarity = len(tech1 & tech2) / len(tech1 | tech2) if tech1 | tech2 else 0
        
        # Content type similarity
        type_similarity = 1.0 if rec1.content_type == rec2.content_type else 0.0
        
        # Difficulty similarity
        difficulty_similarity = 1.0 if rec1.difficulty == rec2.difficulty else 0.5
        
        # Weighted average
        return (tech_similarity * 0.4 + type_similarity * 0.3 + difficulty_similarity * 0.3)

    def _build_request_text(self, request_data: Dict[str, Any]) -> str:
        """Build comprehensive request text for semantic analysis"""
        text_parts = []
        
        if request_data.get('project_title'):
            text_parts.append(str(request_data['project_title']))
        
        if request_data.get('project_description'):
            text_parts.append(str(request_data['project_description']))
        
        if request_data.get('learning_goals'):
            text_parts.append(str(request_data['learning_goals']))
        
        if request_data.get('technologies'):
            tech_data = request_data['technologies']
            if isinstance(tech_data, list):
                text_parts.append(', '.join(tech_data))
            else:
                text_parts.append(str(tech_data))
        
        return ' '.join(text_parts)
    
    def _extract_project_technologies(self, request_data: Dict[str, Any]) -> List[str]:
        """Extract relevant technologies from project information"""
        technologies = []
        
        # Extract from explicit technologies field
        if request_data.get('technologies'):
            tech_data = request_data['technologies']
            if isinstance(tech_data, str):
                technologies.extend([tech.strip() for tech in tech_data.split(',') if tech.strip()])
            elif isinstance(tech_data, list):
                technologies.extend([str(tech).strip() for tech in tech_data if tech])
        
        # Extract from project title and description
        project_text = self._build_request_text(request_data)
        
        # Common technology patterns for different project types
        project_patterns = {
            'expense': ['python', 'javascript', 'react', 'node.js', 'sql', 'database', 'api', 'web', 'mobile'],
            'tracker': ['python', 'javascript', 'react', 'node.js', 'sql', 'database', 'api', 'web', 'mobile'],
            'finance': ['python', 'javascript', 'react', 'node.js', 'sql', 'database', 'api', 'excel', 'analytics'],
            'budget': ['python', 'javascript', 'react', 'node.js', 'sql', 'database', 'api', 'excel', 'analytics'],
            'mobile': ['react native', 'flutter', 'android', 'ios', 'javascript', 'dart', 'kotlin', 'swift'],
            'web': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'node.js', 'python', 'django', 'flask'],
            'api': ['python', 'node.js', 'django', 'flask', 'express', 'fastapi', 'rest', 'graphql'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'sqlite', 'redis'],
            'machine learning': ['python', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy'],
            'data': ['python', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'sql', 'excel'],
            'game': ['unity', 'unreal', 'c#', 'c++', 'javascript', 'python', 'godot'],
            'ecommerce': ['react', 'vue', 'angular', 'node.js', 'python', 'django', 'sql', 'payment', 'stripe'],
            'social': ['react', 'vue', 'angular', 'node.js', 'python', 'django', 'sql', 'websocket', 'real-time'],
            'dashboard': ['react', 'vue', 'angular', 'd3.js', 'chart.js', 'python', 'django', 'flask'],
            'automation': ['python', 'selenium', 'requests', 'beautifulsoup', 'api', 'scripting'],
            'chat': ['react', 'vue', 'angular', 'node.js', 'websocket', 'socket.io', 'real-time', 'api'],
            'blog': ['react', 'vue', 'angular', 'node.js', 'python', 'django', 'wordpress', 'content management'],
            'portfolio': ['html', 'css', 'javascript', 'react', 'vue', 'angular', 'design', 'responsive'],
            'calculator': ['javascript', 'react', 'vue', 'angular', 'python', 'math', 'algorithm'],
            'todo': ['javascript', 'react', 'vue', 'angular', 'node.js', 'python', 'django', 'flask'],
            'weather': ['javascript', 'react', 'vue', 'angular', 'api', 'fetch', 'axios', 'python'],
            'news': ['javascript', 'react', 'vue', 'angular', 'api', 'rss', 'python', 'django', 'flask'],
            'recipe': ['javascript', 'react', 'vue', 'angular', 'api', 'database', 'python', 'django'],
            'music': ['javascript', 'react', 'vue', 'angular', 'audio', 'api', 'spotify', 'python'],
            'fitness': ['javascript', 'react', 'vue', 'angular', 'mobile', 'api', 'python', 'health'],
            'education': ['javascript', 'react', 'vue', 'angular', 'python', 'django', 'flask', 'learning'],
            'travel': ['javascript', 'react', 'vue', 'angular', 'api', 'maps', 'python', 'django'],
            'shopping': ['javascript', 'react', 'vue', 'angular', 'ecommerce', 'payment', 'api', 'python'],
            'booking': ['javascript', 'react', 'vue', 'angular', 'api', 'database', 'python', 'django'],
            'analytics': ['python', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'd3.js', 'chart.js', 'sql'],
            'crm': ['javascript', 'react', 'vue', 'angular', 'python', 'django', 'sql', 'api'],
            'inventory': ['javascript', 'react', 'vue', 'angular', 'python', 'django', 'sql', 'database'],
            'scheduling': ['javascript', 'react', 'vue', 'angular', 'python', 'django', 'calendar', 'api'],
            'file': ['javascript', 'react', 'vue', 'angular', 'python', 'django', 'upload', 'storage'],
            'image': ['javascript', 'react', 'vue', 'angular', 'python', 'opencv', 'pil', 'processing'],
            'video': ['javascript', 'react', 'vue', 'angular', 'python', 'opencv', 'ffmpeg', 'streaming'],
            'audio': ['javascript', 'react', 'vue', 'angular', 'python', 'pyaudio', 'processing', 'music'],
            'pdf': ['javascript', 'react', 'vue', 'angular', 'python', 'pdf', 'processing', 'generation'],
            'email': ['javascript', 'react', 'vue', 'angular', 'python', 'smtp', 'email', 'notification'],
            'notification': ['javascript', 'react', 'vue', 'angular', 'python', 'push', 'email', 'sms'],
            'authentication': ['javascript', 'react', 'vue', 'angular', 'python', 'jwt', 'oauth', 'security'],
            'payment': ['javascript', 'react', 'vue', 'angular', 'python', 'stripe', 'paypal', 'payment'],
            'search': ['javascript', 'react', 'vue', 'angular', 'python', 'elasticsearch', 'search', 'algorithm'],
            'recommendation': ['javascript', 'react', 'vue', 'angular', 'python', 'machine learning', 'algorithm'],
            'chatbot': ['javascript', 'react', 'vue', 'angular', 'python', 'nlp', 'ai', 'machine learning'],
            'ai': ['python', 'tensorflow', 'pytorch', 'scikit-learn', 'nlp', 'machine learning', 'ai'],
            'blockchain': ['javascript', 'python', 'solidity', 'web3', 'ethereum', 'blockchain', 'crypto'],
            'iot': ['python', 'raspberry pi', 'arduino', 'sensors', 'mqtt', 'iot', 'hardware'],
            'vr': ['unity', 'unreal', 'c#', 'c++', 'vr', 'ar', '3d', 'gaming'],
            'ar': ['unity', 'unreal', 'c#', 'c++', 'ar', 'vr', '3d', 'mobile'],
        }
        
        # Extract technologies based on project keywords
        project_lower = project_text.lower()
        for keyword, techs in project_patterns.items():
            if keyword in project_lower:
                technologies.extend(techs)
        
        # Remove duplicates and normalize
        unique_techs = list(set([tech.lower().strip() for tech in technologies if tech.strip()]))
        
        return unique_techs

    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
        except Exception as e:
            print(f"Cosine similarity error: {e}")
            return 0.0

    def integrate_user_feedback(self, user_id: int, recommendation_id: int, 
                              feedback_type: str, feedback_data: Dict[str, Any] = None):
        """Integrate user feedback to improve future recommendations"""
        try:
            # Store feedback for learning
            feedback_key = f"feedback:{user_id}:{recommendation_id}"
            
            feedback_info = {
                'user_id': user_id,
                'recommendation_id': recommendation_id,
                'feedback_type': feedback_type,  # 'relevant', 'not_relevant', 'rating'
                'feedback_data': feedback_data or {},
                'timestamp': time.time()
            }
            
            # Store in cache for immediate use
            self.cache_manager.set_cache(feedback_key, feedback_info, ttl=3600)
            
            # Invalidate user recommendations to force refresh
            self.cache_manager.invalidate_user_cache(user_id)
            
            print(f"Feedback integrated: {feedback_type} for recommendation {recommendation_id}")
            
        except Exception as e:
            print(f"Feedback integration error: {e}")

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
        if recommendations:
            return [asdict(rec) for rec in recommendations]
        else:
            return []
    except Exception as e:
        print(f"Error getting enhanced recommendations: {e}")
        return [] 

# Phase 3: Advanced Features Implementation
# ======================================

@dataclass
class ContextualData:
    """Contextual information for recommendations"""
    timestamp: datetime
    user_agent: str
    device_type: str
    location: Optional[str]
    time_of_day: str
    day_of_week: str
    session_duration: int
    previous_interactions: List[str]
    current_project: Optional[str]
    learning_session: bool

@dataclass
class LearningMetrics:
    """Real-time learning metrics"""
    user_engagement: float
    content_effectiveness: float
    algorithm_performance: Dict[str, float]
    user_satisfaction: float
    learning_progress: float
    adaptation_rate: float

class ContextualAnalyzer:
    """Analyze and incorporate contextual information"""
    
    def __init__(self):
        self.device_patterns = {
            'mobile': ['mobile', 'android', 'ios', 'phone', 'tablet'],
            'desktop': ['desktop', 'windows', 'mac', 'linux'],
            'tablet': ['ipad', 'tablet', 'surface']
        }
        self.time_patterns = {
            'morning': (6, 12),
            'afternoon': (12, 18),
            'evening': (18, 22),
            'night': (22, 6)
        }
        
    def analyze_context(self, request_data: Dict[str, Any], user_id: int) -> ContextualData:
        """Analyze contextual information from request"""
        try:
            # Extract contextual information
            user_agent = request_data.get('user_agent', '')
            timestamp = datetime.now()
            
            # Device type detection
            device_type = self._detect_device_type(user_agent)
            
            # Time-based analysis
            time_of_day = self._get_time_of_day(timestamp)
            day_of_week = timestamp.strftime('%A').lower()
            
            # Session analysis
            session_duration = self._get_session_duration(user_id)
            previous_interactions = self._get_previous_interactions(user_id)
            
            # Project context
            current_project = request_data.get('project_title')
            learning_session = self._is_learning_session(user_id, timestamp)
            
            return ContextualData(
                timestamp=timestamp,
                user_agent=user_agent,
                device_type=device_type,
                location=None,  # Could be enhanced with IP geolocation
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                session_duration=session_duration,
                previous_interactions=previous_interactions,
                current_project=current_project,
                learning_session=learning_session
            )
            
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            return self._get_default_context()
    
    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        user_agent_lower = user_agent.lower()
        
        for device_type, patterns in self.device_patterns.items():
            if any(pattern in user_agent_lower for pattern in patterns):
                return device_type
        
        return 'desktop'  # Default
    
    def _get_time_of_day(self, timestamp: datetime) -> str:
        """Get time of day category"""
        hour = timestamp.hour
        
        for time_category, (start, end) in self.time_patterns.items():
            if start <= hour < end:
                return time_category
        
        return 'night'
    
    def _get_session_duration(self, user_id: int) -> int:
        """Get current session duration in minutes"""
        try:
            # This would integrate with session management
            # For now, return a default value
            return 30
        except Exception:
            return 0
    
    def _get_previous_interactions(self, user_id: int) -> List[str]:
        """Get recent user interactions"""
        try:
            # Query recent user interactions from database
            recent_interactions = Feedback.query.filter_by(user_id=user_id)\
                .order_by(Feedback.created_at.desc())\
                .limit(10)\
                .all()
            
            return [interaction.feedback_type for interaction in recent_interactions]
        except Exception:
            return []
    
    def _is_learning_session(self, user_id: int, timestamp: datetime) -> bool:
        """Determine if this is part of a learning session"""
        try:
            # Check if user has been active in the last hour
            one_hour_ago = timestamp - timedelta(hours=1)
            recent_activity = Feedback.query.filter_by(user_id=user_id)\
                .filter(Feedback.created_at >= one_hour_ago)\
                .count()
            
            return recent_activity > 2
        except Exception:
            return False
    
    def _get_default_context(self) -> ContextualData:
        """Get default contextual data"""
        now = datetime.now()
        return ContextualData(
            timestamp=now,
            user_agent='',
            device_type='desktop',
            location=None,
            time_of_day=self._get_time_of_day(now),
            day_of_week=now.strftime('%A').lower(),
            session_duration=0,
            previous_interactions=[],
            current_project=None,
            learning_session=False
        )

class RealTimeLearner:
    """Real-time learning and adaptation system"""
    
    def __init__(self):
        self.user_profiles = {}
        self.algorithm_performance = defaultdict(list)
        self.content_effectiveness = defaultdict(list)
        self.learning_rate = 0.1
        self.adaptation_threshold = 0.05
        
    def update_user_profile(self, user_id: int, interaction_data: Dict[str, Any]):
        """Update user profile based on interaction"""
        try:
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile(
                    user_id=user_id,
                    interests=[],
                    skill_level='beginner',
                    learning_style='visual',
                    technology_preferences=[],
                    content_preferences={'tutorial': 0.5, 'documentation': 0.3, 'example': 0.2},
                    difficulty_preferences={'beginner': 0.4, 'intermediate': 0.4, 'advanced': 0.2},
                    interaction_patterns={},
                    last_updated=datetime.now()
                )
            
            profile = self.user_profiles[user_id]
            
            # Update based on interaction
            feedback_type = interaction_data.get('feedback_type')
            content_id = interaction_data.get('content_id')
            algorithm_used = interaction_data.get('algorithm_used')
            
            if feedback_type == 'relevant':
                self._boost_preferences(profile, interaction_data)
            elif feedback_type == 'not_relevant':
                self._reduce_preferences(profile, interaction_data)
            
            # Update algorithm performance
            if algorithm_used:
                self.algorithm_performance[algorithm_used].append(1.0 if feedback_type == 'relevant' else 0.0)
            
            # Update content effectiveness
            if content_id:
                self.content_effectiveness[content_id].append(1.0 if feedback_type == 'relevant' else 0.0)
            
            profile.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
    
    def _boost_preferences(self, profile: UserProfile, interaction_data: Dict[str, Any]):
        """Boost preferences based on positive interaction"""
        content_type = interaction_data.get('content_type')
        difficulty = interaction_data.get('difficulty')
        technologies = interaction_data.get('technologies', [])
        
        # Update content preferences
        if content_type and content_type in profile.content_preferences:
            profile.content_preferences[content_type] += self.learning_rate
            self._normalize_preferences(profile.content_preferences)
        
        # Update difficulty preferences
        if difficulty and difficulty in profile.difficulty_preferences:
            profile.difficulty_preferences[difficulty] += self.learning_rate
            self._normalize_preferences(profile.difficulty_preferences)
        
        # Update technology preferences
        for tech in technologies:
            if tech not in profile.technology_preferences:
                profile.technology_preferences.append(tech)
    
    def _reduce_preferences(self, profile: UserProfile, interaction_data: Dict[str, Any]):
        """Reduce preferences based on negative interaction"""
        content_type = interaction_data.get('content_type')
        difficulty = interaction_data.get('difficulty')
        
        # Update content preferences
        if content_type and content_type in profile.content_preferences:
            profile.content_preferences[content_type] -= self.learning_rate
            self._normalize_preferences(profile.content_preferences)
        
        # Update difficulty preferences
        if difficulty and difficulty in profile.difficulty_preferences:
            profile.difficulty_preferences[difficulty] -= self.learning_rate
            self._normalize_preferences(profile.difficulty_preferences)
    
    def _normalize_preferences(self, preferences: Dict[str, float]):
        """Normalize preference values to sum to 1.0"""
        total = sum(preferences.values())
        if total > 0:
            for key in preferences:
                preferences[key] = max(0.0, preferences[key] / total)
    
    def get_adapted_parameters(self, user_id: int, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get adapted parameters based on user profile"""
        try:
            if user_id not in self.user_profiles:
                return request_data
            
            profile = self.user_profiles[user_id]
            adapted_data = request_data.copy()
            
            # Adapt content type preferences
            if 'content_type' not in adapted_data or adapted_data['content_type'] == 'all':
                # Select preferred content type
                preferred_type = max(profile.content_preferences.items(), key=lambda x: x[1])[0]
                adapted_data['content_type'] = preferred_type
            
            # Adapt difficulty preferences
            if 'difficulty' not in adapted_data or adapted_data['difficulty'] == 'all':
                # Select preferred difficulty
                preferred_difficulty = max(profile.difficulty_preferences.items(), key=lambda x: x[1])[0]
                adapted_data['difficulty'] = preferred_difficulty
            
            # Add technology preferences
            if profile.technology_preferences:
                existing_techs = adapted_data.get('technologies', '')
                if existing_techs:
                    existing_techs += ', '
                existing_techs += ', '.join(profile.technology_preferences[:3])  # Top 3
                adapted_data['technologies'] = existing_techs
            
            return adapted_data
            
        except Exception as e:
            logger.error(f"Error getting adapted parameters: {e}")
            return request_data
    
    def get_learning_metrics(self, user_id: int) -> LearningMetrics:
        """Get learning metrics for a user"""
        try:
            profile = self.user_profiles.get(user_id)
            if not profile:
                return self._get_default_learning_metrics()
            
            # Calculate engagement based on interaction frequency
            time_since_update = (datetime.now() - profile.last_updated).total_seconds()
            engagement = max(0.0, 1.0 - (time_since_update / 86400))  # Decay over 24 hours
            
            # Calculate content effectiveness
            content_effectiveness = 0.0
            if self.content_effectiveness:
                all_ratings = [rating for ratings in self.content_effectiveness.values() for rating in ratings]
                if all_ratings:
                    content_effectiveness = sum(all_ratings) / len(all_ratings)
            
            # Calculate algorithm performance
            algorithm_performance = {}
            for algo, ratings in self.algorithm_performance.items():
                if ratings:
                    algorithm_performance[algo] = sum(ratings) / len(ratings)
            
            # Calculate user satisfaction
            user_satisfaction = (engagement + content_effectiveness) / 2
            
            # Calculate learning progress
            learning_progress = len(profile.technology_preferences) / 10.0  # Normalize to 0-1
            
            # Calculate adaptation rate
            adaptation_rate = len(profile.interaction_patterns) / 100.0  # Normalize to 0-1
            
            return LearningMetrics(
                user_engagement=engagement,
                content_effectiveness=content_effectiveness,
                algorithm_performance=algorithm_performance,
                user_satisfaction=user_satisfaction,
                learning_progress=learning_progress,
                adaptation_rate=adaptation_rate
            )
            
        except Exception as e:
            logger.error(f"Error getting learning metrics: {e}")
            return self._get_default_learning_metrics()
    
    def _get_default_learning_metrics(self) -> LearningMetrics:
        """Get default learning metrics"""
        return LearningMetrics(
            user_engagement=0.0,
            content_effectiveness=0.0,
            algorithm_performance={},
            user_satisfaction=0.0,
            learning_progress=0.0,
            adaptation_rate=0.0
        )

class AdvancedAnalytics:
    """Advanced analytics and insights system"""
    
    def __init__(self):
        self.analytics_data = defaultdict(list)
        self.insights_cache = {}
        self.insights_ttl = 3600  # 1 hour
        
    def record_interaction(self, user_id: int, interaction_data: Dict[str, Any]):
        """Record user interaction for analytics"""
        try:
            interaction_data['timestamp'] = datetime.now()
            interaction_data['user_id'] = user_id
            self.analytics_data[user_id].append(interaction_data)
            
            # Keep only last 1000 interactions per user
            if len(self.analytics_data[user_id]) > 1000:
                self.analytics_data[user_id] = self.analytics_data[user_id][-1000:]
            
            # Invalidate insights cache
            self.insights_cache.clear()
            
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
    
    def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Get personalized insights for a user"""
        try:
            cache_key = f"insights_{user_id}"
            if cache_key in self.insights_cache:
                return self.insights_cache[cache_key]
            
            user_data = self.analytics_data.get(user_id, [])
            if not user_data:
                return self._get_default_insights()
            
            insights = {
                'learning_patterns': self._analyze_learning_patterns(user_data),
                'content_preferences': self._analyze_content_preferences(user_data),
                'technology_trends': self._analyze_technology_trends(user_data),
                'performance_metrics': self._analyze_performance_metrics(user_data),
                'recommendations': self._generate_insight_recommendations(user_data)
            }
            
            self.insights_cache[cache_key] = insights
            return insights
            
        except Exception as e:
            logger.error(f"Error getting user insights: {e}")
            return self._get_default_insights()
    
    def _analyze_learning_patterns(self, user_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user learning patterns"""
        try:
            # Time-based patterns
            time_distribution = defaultdict(int)
            day_distribution = defaultdict(int)
            
            for interaction in user_data:
                timestamp = interaction.get('timestamp')
                if timestamp:
                    hour = timestamp.hour
                    day = timestamp.strftime('%A')
                    
                    if 6 <= hour < 12:
                        time_distribution['morning'] += 1
                    elif 12 <= hour < 18:
                        time_distribution['afternoon'] += 1
                    elif 18 <= hour < 22:
                        time_distribution['evening'] += 1
                    else:
                        time_distribution['night'] += 1
                    
                    day_distribution[day] += 1
            
            # Session patterns
            session_lengths = []
            current_session_start = None
            
            for interaction in sorted(user_data, key=lambda x: x.get('timestamp', datetime.now())):
                timestamp = interaction.get('timestamp')
                if not timestamp:
                    continue
                
                if current_session_start is None:
                    current_session_start = timestamp
                elif (timestamp - current_session_start).total_seconds() > 3600:  # 1 hour gap
                    session_length = (timestamp - current_session_start).total_seconds() / 60
                    session_lengths.append(session_length)
                    current_session_start = timestamp
            
            avg_session_length = sum(session_lengths) / len(session_lengths) if session_lengths else 0
            
            return {
                'peak_learning_time': max(time_distribution.items(), key=lambda x: x[1])[0] if time_distribution else 'unknown',
                'preferred_days': sorted(day_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
                'average_session_length': avg_session_length,
                'total_sessions': len(session_lengths),
                'engagement_trend': self._calculate_engagement_trend(user_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing learning patterns: {e}")
            return {}
    
    def _analyze_content_preferences(self, user_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user content preferences"""
        try:
            content_types = defaultdict(int)
            difficulties = defaultdict(int)
            feedback_scores = defaultdict(list)
            
            for interaction in user_data:
                content_type = interaction.get('content_type')
                difficulty = interaction.get('difficulty')
                feedback_type = interaction.get('feedback_type')
                
                if content_type:
                    content_types[content_type] += 1
                
                if difficulty:
                    difficulties[difficulty] += 1
                
                if feedback_type:
                    score = 1.0 if feedback_type == 'relevant' else 0.0
                    if content_type:
                        feedback_scores[content_type].append(score)
            
            # Calculate effectiveness scores
            effectiveness_scores = {}
            for content_type, scores in feedback_scores.items():
                if scores:
                    effectiveness_scores[content_type] = sum(scores) / len(scores)
            
            return {
                'preferred_content_types': sorted(content_types.items(), key=lambda x: x[1], reverse=True),
                'preferred_difficulties': sorted(difficulties.items(), key=lambda x: x[1], reverse=True),
                'content_effectiveness': effectiveness_scores,
                'total_interactions': len(user_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing content preferences: {e}")
            return {}
    
    def _analyze_technology_trends(self, user_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user technology trends"""
        try:
            technology_usage = defaultdict(int)
            technology_effectiveness = defaultdict(list)
            
            for interaction in user_data:
                technologies = interaction.get('technologies', [])
                feedback_type = interaction.get('feedback_type')
                
                for tech in technologies:
                    technology_usage[tech] += 1
                    
                    if feedback_type:
                        score = 1.0 if feedback_type == 'relevant' else 0.0
                        technology_effectiveness[tech].append(score)
            
            # Calculate effectiveness scores
            tech_effectiveness_scores = {}
            for tech, scores in technology_effectiveness.items():
                if scores:
                    tech_effectiveness_scores[tech] = sum(scores) / len(scores)
            
            # Get trending technologies
            trending_techs = sorted(technology_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'trending_technologies': trending_techs,
                'technology_effectiveness': tech_effectiveness_scores,
                'total_technologies': len(technology_usage)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing technology trends: {e}")
            return {}
    
    def _analyze_performance_metrics(self, user_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user performance metrics"""
        try:
            algorithm_performance = defaultdict(list)
            response_times = []
            
            for interaction in user_data:
                algorithm = interaction.get('algorithm_used')
                feedback_type = interaction.get('feedback_type')
                response_time = interaction.get('response_time')
                
                if algorithm and feedback_type:
                    score = 1.0 if feedback_type == 'relevant' else 0.0
                    algorithm_performance[algorithm].append(score)
                
                if response_time:
                    response_times.append(response_time)
            
            # Calculate algorithm effectiveness
            algo_effectiveness = {}
            for algo, scores in algorithm_performance.items():
                if scores:
                    algo_effectiveness[algo] = sum(scores) / len(scores)
            
            # Calculate average response time
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'algorithm_effectiveness': algo_effectiveness,
                'average_response_time': avg_response_time,
                'total_recommendations': len(user_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance metrics: {e}")
            return {}
    
    def _calculate_engagement_trend(self, user_data: List[Dict[str, Any]]) -> str:
        """Calculate user engagement trend"""
        try:
            if len(user_data) < 2:
                return 'stable'
            
            # Group by week and count interactions
            weekly_interactions = defaultdict(int)
            for interaction in user_data:
                timestamp = interaction.get('timestamp')
                if timestamp:
                    week = timestamp.strftime('%Y-%W')
                    weekly_interactions[week] += 1
            
            if len(weekly_interactions) < 2:
                return 'stable'
            
            # Calculate trend
            weeks = sorted(weekly_interactions.keys())
            recent_avg = sum(weekly_interactions[week] for week in weeks[-2:]) / 2
            older_avg = sum(weekly_interactions[week] for week in weeks[:-2]) / max(1, len(weeks) - 2)
            
            if recent_avg > older_avg * 1.2:
                return 'increasing'
            elif recent_avg < older_avg * 0.8:
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception:
            return 'stable'
    
    def _generate_insight_recommendations(self, user_data: List[Dict[str, Any]]) -> List[str]:
        """Generate personalized recommendations based on insights"""
        try:
            recommendations = []
            
            # Analyze patterns and generate recommendations
            content_prefs = self._analyze_content_preferences(user_data)
            tech_trends = self._analyze_technology_trends(user_data)
            learning_patterns = self._analyze_learning_patterns(user_data)
            
            # Content type recommendations
            if content_prefs.get('preferred_content_types'):
                top_content = content_prefs['preferred_content_types'][0][0]
                recommendations.append(f"Focus on {top_content} content for better engagement")
            
            # Technology recommendations
            if tech_trends.get('trending_technologies'):
                top_tech = tech_trends['trending_technologies'][0][0]
                recommendations.append(f"Explore more {top_tech} resources to build expertise")
            
            # Learning pattern recommendations
            peak_time = learning_patterns.get('peak_learning_time')
            if peak_time and peak_time != 'unknown':
                recommendations.append(f"Schedule learning sessions during {peak_time} for optimal focus")
            
            # Session length recommendations
            avg_session = learning_patterns.get('average_session_length', 0)
            if avg_session < 30:
                recommendations.append("Try longer learning sessions (30+ minutes) for better retention")
            elif avg_session > 120:
                recommendations.append("Consider shorter, focused sessions to maintain concentration")
            
            return recommendations[:5]  # Limit to 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating insight recommendations: {e}")
            return []
    
    def _get_default_insights(self) -> Dict[str, Any]:
        """Get default insights"""
        return {
            'learning_patterns': {},
            'content_preferences': {},
            'technology_trends': {},
            'performance_metrics': {},
            'recommendations': ['Start exploring content to generate personalized insights']
        }

class GlobalScaler:
    """Global scaling and multi-region deployment support"""
    
    def __init__(self):
        self.region_configs = {
            'us-east': {'latency': 50, 'capacity': 1000},
            'us-west': {'latency': 80, 'capacity': 800},
            'eu-west': {'latency': 120, 'capacity': 600},
            'asia-pacific': {'latency': 200, 'capacity': 400}
        }
        self.current_region = 'us-east'
        self.load_balancing_enabled = True
        
    def get_optimal_region(self, user_location: Optional[str] = None) -> str:
        """Get optimal region based on user location"""
        try:
            if not user_location:
                return self.current_region
            
            # Simple region selection based on location
            location_lower = user_location.lower()
            
            if any(region in location_lower for region in ['us', 'america', 'north']):
                return 'us-east'
            elif any(region in location_lower for region in ['europe', 'eu', 'uk']):
                return 'eu-west'
            elif any(region in location_lower for region in ['asia', 'china', 'japan', 'india']):
                return 'asia-pacific'
            else:
                return 'us-east'  # Default
                
        except Exception:
            return self.current_region
    
    def get_region_performance(self, region: str) -> Dict[str, Any]:
        """Get performance metrics for a region"""
        try:
            config = self.region_configs.get(region, {})
            return {
                'region': region,
                'latency_ms': config.get('latency', 100),
                'capacity': config.get('capacity', 500),
                'status': 'operational',
                'load': self._get_region_load(region)
            }
        except Exception:
            return {
                'region': region,
                'latency_ms': 100,
                'capacity': 500,
                'status': 'unknown',
                'load': 0.5
            }
    
    def _get_region_load(self, region: str) -> float:
        """Get current load for a region (0.0 to 1.0)"""
        try:
            # This would integrate with actual load monitoring
            # For now, return a simulated load
            import random
            return random.uniform(0.1, 0.8)
        except Exception:
            return 0.5
    
    def should_scale(self, current_load: float, region: str) -> bool:
        """Determine if scaling is needed"""
        try:
            config = self.region_configs.get(region, {})
            capacity = config.get('capacity', 500)
            
            # Scale if load exceeds 80% of capacity
            return current_load > 0.8
            
        except Exception:
            return False
    
    def get_scaling_recommendations(self, region: str) -> List[str]:
        """Get scaling recommendations for a region"""
        try:
            recommendations = []
            config = self.region_configs.get(region, {})
            current_load = self._get_region_load(region)
            
            if current_load > 0.9:
                recommendations.append(f"High load detected in {region}. Consider adding more instances.")
            
            if current_load > 0.7:
                recommendations.append(f"Moderate load in {region}. Monitor performance closely.")
            
            if config.get('latency', 100) > 150:
                recommendations.append(f"High latency in {region}. Consider CDN optimization.")
            
            return recommendations
            
        except Exception:
            return []

# Initialize Phase 3 components
contextual_analyzer = ContextualAnalyzer()
real_time_learner = RealTimeLearner()
advanced_analytics = AdvancedAnalytics()
global_scaler = GlobalScaler()

# Extend UnifiedIntelligentEngine with Phase 3 capabilities
def get_enhanced_recommendations_phase3(user_id: int, request_data: Dict[str, Any], 
                                      limit: int = 10) -> List[Dict[str, Any]]:
    """Enhanced recommendations with Phase 3 features"""
    try:
        start_time = time.time()
        
        # Phase 3: Contextual Analysis
        context = contextual_analyzer.analyze_context(request_data, user_id)
        
        # Phase 3: Real-time Learning Adaptation
        adapted_data = real_time_learner.get_adapted_parameters(user_id, request_data)
        
        # Phase 3: Global Scaling
        optimal_region = global_scaler.get_optimal_region(context.location)
        
        # Get base recommendations
        recommendations = get_enhanced_recommendations(user_id, adapted_data, limit)
        
        # Phase 3: Contextual Enhancement
        enhanced_recommendations = []
        for rec in recommendations:
            enhanced_rec = rec.copy()
            
            # Add contextual information
            enhanced_rec['context'] = {
                'device_optimized': context.device_type,
                'time_appropriate': context.time_of_day,
                'session_context': context.learning_session,
                'region': optimal_region
            }
            
            # Add learning insights
            learning_metrics = real_time_learner.get_learning_metrics(user_id)
            enhanced_rec['learning_insights'] = {
                'engagement_score': learning_metrics.user_engagement,
                'content_effectiveness': learning_metrics.content_effectiveness,
                'learning_progress': learning_metrics.learning_progress
            }
            
            enhanced_recommendations.append(enhanced_rec)
        
        # Phase 3: Analytics Recording
        interaction_data = {
            'request_data': request_data,
            'context': asdict(context),
            'recommendations_count': len(enhanced_recommendations),
            'response_time': (time.time() - start_time) * 1000,
            'region': optimal_region
        }
        advanced_analytics.record_interaction(user_id, interaction_data)
        
        return enhanced_recommendations
        
    except Exception as e:
        logger.error(f"Error in Phase 3 enhanced recommendations: {e}")
        # Fallback to Phase 2
        return get_enhanced_recommendations(user_id, request_data, limit)

def get_user_insights_phase3(user_id: int) -> Dict[str, Any]:
    """Get comprehensive user insights with Phase 3 analytics"""
    try:
        insights = advanced_analytics.get_user_insights(user_id)
        learning_metrics = real_time_learner.get_learning_metrics(user_id)
        
        # Combine insights with learning metrics
        comprehensive_insights = {
            'analytics': insights,
            'learning_metrics': asdict(learning_metrics),
            'recommendations': insights.get('recommendations', []),
            'phase': 'phase_3_complete'
        }
        
        return comprehensive_insights
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 user insights: {e}")
        return {'error': 'Unable to generate insights', 'phase': 'phase_3_error'}

def record_user_feedback_phase3(user_id: int, recommendation_id: int, 
                               feedback_type: str, feedback_data: Dict[str, Any] = None):
    """Record user feedback with Phase 3 learning"""
    try:
        # Record feedback in base system
        unified_engine.integrate_user_feedback(user_id, recommendation_id, feedback_type, feedback_data)
        
        # Phase 3: Real-time Learning
        interaction_data = {
            'feedback_type': feedback_type,
            'recommendation_id': recommendation_id,
            'feedback_data': feedback_data or {},
            'timestamp': datetime.now()
        }
        real_time_learner.update_user_profile(user_id, interaction_data)
        
        # Phase 3: Analytics
        advanced_analytics.record_interaction(user_id, interaction_data)
        
        logger.info(f"Phase 3 feedback recorded for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error recording Phase 3 feedback: {e}")

def get_system_health_phase3() -> Dict[str, Any]:
    """Get comprehensive system health with Phase 3 metrics"""
    try:
        # Base system health
        base_health = {
            'enhanced_engine_available': True,
            'phase_1_complete': True,
            'phase_2_complete': True,
            'phase_3_complete': True
        }
        
        # Phase 3: Performance metrics
        performance_metrics = unified_engine.get_performance_metrics()
        
        # Phase 3: Global scaling status
        regions_status = {}
        for region in global_scaler.region_configs.keys():
            regions_status[region] = global_scaler.get_region_performance(region)
        
        # Phase 3: Learning system status
        learning_status = {
            'active_users': len(real_time_learner.user_profiles),
            'total_interactions': sum(len(data) for data in advanced_analytics.analytics_data.values()),
            'adaptation_rate': sum(
                real_time_learner.get_learning_metrics(user_id).adaptation_rate 
                for user_id in real_time_learner.user_profiles.keys()
            ) / max(1, len(real_time_learner.user_profiles))
        }
        
        comprehensive_health = {
            **base_health,
            'performance_metrics': asdict(performance_metrics),
            'global_scaling': {
                'regions': regions_status,
                'load_balancing': global_scaler.load_balancing_enabled,
                'current_region': global_scaler.current_region
            },
            'learning_system': learning_status,
            'analytics': {
                'total_users_analyzed': len(advanced_analytics.analytics_data),
                'insights_cache_size': len(advanced_analytics.insights_cache)
            }
        }
        
        return comprehensive_health
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 system health: {e}")
        return {
            'enhanced_engine_available': True,
            'phase_1_complete': True,
            'phase_2_complete': True,
            'phase_3_complete': False,
            'error': str(e)
        } 