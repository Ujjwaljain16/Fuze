#!/usr/bin/env python3
"""
Ensemble Recommendation Engine - OPTIMIZED Version
Combines results from multiple engines for better recommendations
"""

import time
import logging

from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json

# Add project root to path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_utils import redis_cache
from gemini_utils import GeminiAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class EnsembleRequest:
    user_id: int
    title: str
    description: str = ""
    technologies: str = ""
    project_id: int = None
    max_recommendations: int = 10
    engines: List[str] = None  # ['unified', 'smart', 'enhanced']

@dataclass
class EnsembleResult:
    id: int
    title: str
    url: str
    score: float = 0.0
    reason: str = ""
    ensemble_score: float = 0.0
    engine_votes: Dict[str, float] = None
    technologies: List[str] = None
    content_type: str = "article"
    difficulty: str = "intermediate"

class OptimizedEnsembleEngine:
    """Optimized ensemble engine with caching, parallel processing, and quality preservation"""
    
    def __init__(self):
        self.engine_weights = {
            'smart': 0.6,       # Heavier weight for smart NLP
            'fast_gemini': 0.4  # Weight for Gemini AI
        }
        self.cache_duration = 900  # 15 minutes
        self.max_parallel_engines = 2  # Only two engines
        self.timeout_seconds = 30
        self.quality_threshold = 0.6  # Increased quality threshold
        self.min_recommendations = 5
        logger.info("AI/NLP Ensemble Engine initialized with Smart and FastGemini only")
    
    def get_ensemble_recommendations(self, request: EnsembleRequest) -> List[EnsembleResult]:
        """Get ensemble recommendations with AI/NLP engines only"""
        start_time = time.time()
        try:
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.info("Cache hit for ensemble recommendations")
                return cached_result

            # Only use smart and fast_gemini engines
            engines_to_use = ['smart', 'fast_gemini']
            available_engines = self._get_available_engines(engines_to_use)
            if not available_engines:
                logger.warning("No AI/NLP engines available")
                return []
            logger.info(f"Using AI/NLP engines: {available_engines}")
            engine_results = self._get_engine_results_quality_optimized(available_engines, request)
            ensemble_results = self._combine_results_quality_optimized(engine_results, request)
            self._cache_result(cache_key, ensemble_results)
            response_time = (time.time() - start_time) * 1000
            logger.info(f"AI/NLP ensemble completed in {response_time:.2f}ms")
            return ensemble_results
        except Exception as e:
            logger.error(f"Ensemble error: {e}")
            return []
    
    def _generate_cache_key(self, request: EnsembleRequest) -> str:
        """Generate cache key for ensemble request"""
        cache_data = {
            'user_id': request.user_id,
            'title': request.title[:100],  # Limit title length
            'description': request.description[:200],  # Limit description length
            'technologies': request.technologies,
            'max_recommendations': request.max_recommendations
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"ensemble_{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    def _get_cached_result(self, cache_key: str) -> List[EnsembleResult]:
        """Get cached ensemble result"""
        try:
            cached = redis_cache.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                return [EnsembleResult(**item) for item in cached_data]
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
        return None
    
    def _cache_result(self, cache_key: str, results: List[EnsembleResult]):
        """Cache ensemble result"""
        try:
            cache_data = [asdict(result) for result in results]
            redis_cache.setex(cache_key, self.cache_duration, json.dumps(cache_data))
        except Exception as e:
            logger.warning(f"Error caching result: {e}")
    
    def _get_available_engines(self, requested_engines: List[str]) -> List[str]:
        """Return only available AI/NLP engines"""
        available = []
        for eng in requested_engines:
            if eng == 'smart':
                try:
                    from smart_recommendation_engine import SmartRecommendationEngine
                    available.append('smart')
                except Exception:
                    pass
            elif eng == 'fast_gemini':
                try:
                    from fast_gemini_engine import fast_gemini_engine
                    available.append('fast_gemini')
                except Exception:
                    pass
        return available
    
    def _get_engine_results_quality_optimized(self, engines: List[str], request: EnsembleRequest) -> Dict[str, List[Dict]]:
        """Get results from only smart and fast_gemini engines"""
        engine_results = {}
        if 'smart' in engines:
            try:
                engine_results['smart'] = self._get_smart_results(request)
            except Exception as e:
                logger.error(f"Error with smart engine: {e}")
                engine_results['smart'] = []
        if 'fast_gemini' in engines:
            try:
                engine_results['fast_gemini'] = self._get_fast_gemini_results(request)
            except Exception as e:
                logger.error(f"Error with fast_gemini engine: {e}")
                engine_results['fast_gemini'] = []
        return engine_results
    
    def _get_single_engine_results(self, engine_name: str, request: EnsembleRequest) -> List[Dict]:
        """Get results from a single engine with error handling"""
        try:
            if engine_name == 'smart':
                return self._get_smart_results(request)
            elif engine_name == 'fast_gemini':
                return self._get_fast_gemini_results(request)
            else:
                logger.warning(f"Unknown engine: {engine_name}")
                return []
        except Exception as e:
            logger.error(f"Error getting results from {engine_name}: {e}")
            return []
    
    def _get_smart_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from SmartRecommendationEngine with quality filtering"""
        try:
            from smart_recommendation_engine import SmartRecommendationEngine
            
            # Initialize smart engine
            smart_engine = SmartRecommendationEngine(request.user_id)
            
            # Get user's bookmarks for context
            user_bookmarks = smart_engine.get_analyzed_bookmarks()
            
            if not user_bookmarks:
                logger.info(f"No analyzed bookmarks found for user {request.user_id}")
                return []
            
            # Process bookmarks with quality filtering
            recommendations = []
            for bookmark, analysis in user_bookmarks:
                # Skip low-quality content
                if bookmark.quality_score < 6:
                    continue
                
                # Skip test bookmarks
                if 'test' in bookmark.title.lower():
                    continue
                
                # Extract technologies from analysis
                technologies = []
                if analysis:
                    # Try to get technologies from technology_tags field
                    if analysis.technology_tags:
                        try:
                            tech_tags = [tech.strip() for tech in analysis.technology_tags.split(',') if tech.strip()]
                            technologies.extend(tech_tags)
                        except:
                            pass
                    
                    # Try to get technologies from analysis_data JSON
                    if analysis.analysis_data:
                        try:
                            analysis_data = analysis.analysis_data
                            if isinstance(analysis_data, dict):
                                tech_data = analysis_data.get('technologies', [])
                                if isinstance(tech_data, list):
                                    technologies.extend(tech_data)
                                elif isinstance(tech_data, str):
                                    technologies.append(tech_data)
                        except:
                            pass
                    
                    # Remove duplicates
                    technologies = list(set(technologies))
                
                # Generate meaningful reason
                reason = self._generate_smart_reason(bookmark, analysis, technologies, request)
                
                # Calculate score based on quality and relevance
                score = self._calculate_smart_score(bookmark, analysis, request)
                
                # Only include if score is reasonable (increased threshold)
                if score >= 60:
                    recommendations.append({
                        'id': bookmark.id,
                        'title': bookmark.title[:200],  # Limit title length
                        'url': bookmark.url or "",
                        'score': score,
                        'reason': reason,
                        'technologies': technologies,
                        'content_type': self._detect_content_type(bookmark.title),
                        'difficulty': self._detect_difficulty(bookmark.title, analysis),
                        'quality_score': bookmark.quality_score or 6.0
                    })
            
            # Sort by score and limit
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:request.max_recommendations * 2]
            
        except Exception as e:
            logger.error(f"Error in smart engine: {e}")
            return []
    
    def _get_fast_gemini_results(self, request: EnsembleRequest) -> List[Dict]:
        """Get results from FastGeminiEngine with quality filtering"""
        try:
            from fast_gemini_engine import fast_gemini_engine
            from models import SavedContent
            from app import app
            
            with app.app_context():
                # Optimized query with limits and specific fields to prevent timeouts
                user_bookmarks = SavedContent.query.filter_by(
                    user_id=request.user_id
                ).with_entities(
                    SavedContent.id,
                    SavedContent.title,
                    SavedContent.url,
                    SavedContent.extracted_text,
                    SavedContent.quality_score
                ).filter(
                    SavedContent.quality_score >= 6,  # Quality threshold
                    SavedContent.title.notlike('%Test Bookmark%'),
                    SavedContent.title.notlike('%test bookmark%')
                ).limit(100).all()  # Limit to prevent large result sets
                
                if not user_bookmarks:
                    logger.info(f"No bookmarks found for user {request.user_id}")
                    return []
                
                bookmarks_data = []
                for bookmark in user_bookmarks:
                    # Skip incomplete content
                    if not bookmark.title or len(bookmark.title.strip()) < 10:
                        continue
                    
                    bookmarks_data.append({
                        'id': bookmark.id,
                        'title': bookmark.title[:200],  # Limit title length
                        'url': bookmark.url or "",
                        'content': bookmark.extracted_text or bookmark.title,
                        'quality_score': bookmark.quality_score or 7.0,
                        'similarity_score': 0.5
                    })
                
                user_input = {
                    'title': request.title,
                    'description': request.description,
                    'technologies': request.technologies,
                    'user_id': request.user_id
                }
                
                result = fast_gemini_engine.get_fast_gemini_recommendations(
                    bookmarks_data, user_input, request.max_recommendations * 2
                )
                
                # Filter out bad recommendations using GeminiAnalyzer utility
                try:
                    filtered = GeminiAnalyzer().filter_bad_recommendations(result.get('recommendations', []))
                    return self._clean_fast_gemini_results(filtered)
                except Exception as filter_error:
                    logger.warning(f"GeminiAnalyzer filtering failed, using manual filtering: {filter_error}")
                    return self._clean_fast_gemini_results(result.get('recommendations', []))
                    
        except Exception as e:
            logger.warning(f"FastGeminiEngine not available: {e}")
            return []
    
    def _clean_fast_gemini_results(self, results: List[Dict]) -> List[Dict]:
        """Clean and validate FastGemini results with strict quality filtering"""
        cleaned_results = []
        
        for result in results:
            # Skip incomplete results
            if not result.get('id') or not result.get('title'):
                continue
            
            # Clean title (remove truncation artifacts)
            title = result.get('title', '')
            if title.endswith('...') or title.endswith(' is'):
                continue
            
            # Skip very short titles
            if len(title.strip()) < 15:
                continue
            
            # Ensure URL is valid and not problematic
            url = result.get('url', '')
            if not url or url == "":
                continue
                
            # Skip problematic URLs
            url_lower = url.lower()
            if any(bad_url in url_lower for bad_url in [
                'file://', 'raw.githubusercontent.com', 'docs.google.com/spreadsheets',
                'leetcode.com/problem-list', 'codeforces.com/problemset'
            ]):
                continue
            
            # Skip generic or low-quality titles
            title_lower = title.lower()
            if any(generic in title_lower for generic in [
                'syllabus', 'batch', 'shareable', 'google sheets', 'problem -', 
                'leetcode discuss', 'raw.githubusercontent.com', 'tutorial', 'guide'
            ]):
                continue
            
            # Extract technologies properly
            technologies = result.get('technologies', [])
            if not technologies or (isinstance(technologies, list) and len(technologies) == 0):
                # Try to extract from title/content
                technologies = self._extract_technologies_from_text(title)
            
            # Skip content with too many technologies (likely noise)
            if len(technologies) > 15:
                continue
            
            # Generate meaningful reason if missing
            reason = result.get('reason', '')
            if not reason or reason in ['Relevant learning content', 'Helpful content']:
                reason = self._generate_dynamic_reason(title, technologies)
            
            # Calculate proper score with quality adjustments
            score = result.get('score', 0)
            if score > 100:  # Normalize if score is too high
                score = min(score / 10, 100)
            
            # Apply quality penalties
            if any(generic in reason.lower() for generic in [
                'high-quality', 'helpful', 'useful', 'relevant'
            ]):
                score -= 20  # Penalty for generic reasons
            
            # Skip low-scoring content
            if score < 50:
                continue
            
            cleaned_results.append({
                'id': result['id'],
                'title': title[:200],  # Limit title length
                'url': url,
                'score': score,
                'reason': reason,
                'technologies': technologies,
                'content_type': result.get('content_type', 'article'),
                'difficulty': result.get('difficulty', 'intermediate')
            })
        
        return cleaned_results
    
    def _extract_technologies_from_text(self, text: str) -> List[str]:
        """Extract technologies from text using keyword matching"""
        if not text:
            return []
        
        text_lower = text.lower()
        tech_keywords = {
            'java': ['java', 'jvm', 'bytecode', 'spring', 'maven', 'gradle'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'typescript'],
            'python': ['python', 'django', 'flask', 'pandas', 'numpy', 'scikit-learn'],
            'dsa': ['algorithm', 'data structure', 'dsa', 'sorting', 'searching', 'leetcode'],
            'instrumentation': ['instrumentation', 'monitoring', 'profiling', 'byte buddy', 'asm'],
            'machine learning': ['machine learning', 'ml', 'ai', 'neural', 'tensorflow', 'pytorch'],
            'web development': ['html', 'css', 'web', 'frontend', 'backend', 'fullstack']
        }
        
        found_techs = []
        for tech, keywords in tech_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_techs.append(tech)
                    break
        
        return list(set(found_techs))
    
    def _generate_dynamic_reason(self, title: str, technologies: List[str]) -> str:
        """Generate a dynamic recommendation reason"""
        if not title:
            return "High-quality learning content"
        
        title_lower = title.lower()
        
        # Technology-specific reasons
        if technologies:
            tech_list = ', '.join(technologies[:3])  # Limit to 3 technologies
            return f"Content covering {tech_list} technologies"
        
        # Content type detection
        if any(word in title_lower for word in ['tutorial', 'guide', 'learn']):
            return "Tutorial content for skill development"
        elif any(word in title_lower for word in ['documentation', 'api', 'reference']):
            return "Reference material and documentation"
        elif any(word in title_lower for word in ['project', 'github', 'repo']):
            return "Practical project implementation"
        elif any(word in title_lower for word in ['interview', 'question', 'leetcode']):
            return "Interview preparation and practice"
        else:
            return "High-quality learning resource"
    
    def _generate_smart_reason(self, bookmark, analysis, technologies: List[str], request: EnsembleRequest) -> str:
        """Generate meaningful reason for smart engine results"""
        if not bookmark.title:
            return "High-quality learning content"
        
        title_lower = bookmark.title.lower()
        
        # Technology overlap
        if technologies and request.technologies:
            request_techs = [tech.strip().lower() for tech in request.technologies.split(',') if tech.strip()]
            overlap = [tech for tech in technologies if any(req_tech in tech.lower() or tech.lower() in req_tech for req_tech in request_techs)]
            if overlap:
                return f"Directly covers {', '.join(overlap[:2])} technologies"
        
        # Content type detection
        if any(word in title_lower for word in ['tutorial', 'guide', 'learn']):
            return "Structured learning tutorial"
        elif any(word in title_lower for word in ['documentation', 'api', 'reference']):
            return "Comprehensive reference material"
        elif any(word in title_lower for word in ['project', 'github', 'repo']):
            return "Practical project example"
        elif any(word in title_lower for word in ['interview', 'question', 'leetcode']):
            return "Interview preparation content"
        else:
            return "High-quality educational resource"
    
    def _calculate_smart_score(self, bookmark, analysis, request: EnsembleRequest) -> float:
        """Calculate score for smart engine results with better quality filtering"""
        base_score = bookmark.quality_score or 6.0
        
        # Start with a lower base score
        final_score = base_score * 5  # Scale down from 10x to 5x
        
        # Quality bonus (more selective)
        if base_score >= 9:
            final_score += 30
        elif base_score >= 8:
            final_score += 20
        elif base_score >= 7:
            final_score += 10
        elif base_score >= 6:
            final_score += 5
        
        # Content length bonus (more selective)
        if bookmark.title and len(bookmark.title) > 80:
            final_score += 10
        elif bookmark.title and len(bookmark.title) > 50:
            final_score += 5
        
        # Analysis bonus (more selective)
        if analysis and analysis.technology_tags:
            tech_count = len([t.strip() for t in analysis.technology_tags.split(',') if t.strip()])
            if 1 <= tech_count <= 10:  # Sweet spot for technology count
                final_score += 15
            elif tech_count > 10:
                final_score += 5  # Reduced bonus for too many technologies
        
        # Penalty for generic content
        title_lower = bookmark.title.lower() if bookmark.title else ""
        if any(generic in title_lower for generic in [
            'syllabus', 'batch', 'shareable', 'google sheets', 'problem -', 
            'leetcode discuss', 'raw.githubusercontent.com'
        ]):
            final_score -= 30
        
        # Penalty for poor URLs
        if bookmark.url:
            url_lower = bookmark.url.lower()
            if any(bad_url in url_lower for bad_url in [
                'file://', 'raw.githubusercontent.com', 'docs.google.com/spreadsheets'
            ]):
                final_score -= 40
        
        # Ensure score is within reasonable bounds
        return max(0, min(100, final_score))
    
    def _detect_content_type(self, title: str) -> str:
        """Detect content type from title"""
        if not title:
            return "article"
        
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['tutorial', 'guide', 'learn']):
            return "tutorial"
        elif any(word in title_lower for word in ['documentation', 'api', 'reference']):
            return "documentation"
        elif any(word in title_lower for word in ['project', 'github', 'repo']):
            return "project"
        elif any(word in title_lower for word in ['interview', 'question', 'leetcode']):
            return "practice"
        else:
            return "article"
    
    def _detect_difficulty(self, title: str, analysis) -> str:
        """Detect difficulty level"""
        if not title:
            return "intermediate"
        
        title_lower = title.lower()
        
        # Check for difficulty indicators
        if any(word in title_lower for word in ['beginner', 'basic', 'intro', 'start']):
            return "beginner"
        elif any(word in title_lower for word in ['advanced', 'expert', 'master', 'deep']):
            return "advanced"
        elif analysis and hasattr(analysis, 'difficulty_level'):
            return analysis.difficulty_level or "intermediate"
        else:
            return "intermediate"
    
    def _check_quality_sufficient(self, results: List[Dict]) -> bool:
        """Check if results have sufficient quality"""
        if not results:
            return False
        
        # Check average score
        scores = [result.get('score', 0) for result in results]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Check if we have enough high-quality results
        high_quality_count = sum(1 for score in scores if score >= 70)
        
        return avg_score >= 60 and high_quality_count >= 3
    
    def _combine_results_quality_optimized(self, engine_results: Dict[str, List[Dict]], request: EnsembleRequest) -> List[EnsembleResult]:
        """Combine results using quality-optimized weighted voting"""
        # Track votes for each content item
        content_votes = defaultdict(lambda: {
            'votes': defaultdict(float),
            'content': None,
            'total_score': 0.0,
            'quality_score': 0.0,
            'engine_count': 0
        })
        
        # Collect votes from each engine with quality weighting
        for engine_name, results in engine_results.items():
            weight = self.engine_weights.get(engine_name, 0.1)
            
            for i, result in enumerate(results):
                content_id = result.get('id')
                if not content_id:
                    continue
                
                # Enhanced vote calculation with quality focus
                rank_score = 1.0 / (i + 1)  # Higher rank = higher score
                score = result.get('score', 0) / 100.0  # Normalize score
                
                # Quality bonus for high-scoring content
                quality_bonus = 1.0 if score >= 0.8 else 0.5 if score >= 0.6 else 0.2
                
                # Calculate vote with quality weighting
                vote = (rank_score * 0.4 + score * 0.6) * weight * quality_bonus
                
                content_votes[content_id]['votes'][engine_name] = vote
                content_votes[content_id]['total_score'] += vote
                content_votes[content_id]['quality_score'] += score
                content_votes[content_id]['engine_count'] += 1
                content_votes[content_id]['content'] = result
        
        # Convert to ensemble results with quality filtering
        ensemble_results = []
        for content_id, vote_data in content_votes.items():
            content = vote_data['content']
            if not content:
                continue
            
            # Calculate ensemble score with quality consideration
            avg_quality = vote_data['quality_score'] / vote_data['engine_count'] if vote_data['engine_count'] > 0 else 0
            ensemble_score = vote_data['total_score'] * (1 + avg_quality * 0.3)  # Quality boost
            
            # Filter by quality threshold
            if avg_quality < self.quality_threshold and vote_data['engine_count'] < 2:
                continue  # Skip low-quality content unless multiple engines agree
            
            # Filter out very low quality content more strictly
            if avg_quality < 0.2 and vote_data['engine_count'] < 2:
                continue  # Skip very low-quality content
            
            # Filter out content with generic reasons
            reason = content.get('reason', '')
            if reason and any(generic in reason.lower() for generic in ['helpful', 'useful', 'relevant']):
                if avg_quality < 0.5:  # Only allow generic reasons for high-quality content
                    continue
            
            # Create ensemble result
            ensemble_result = EnsembleResult(
                id=content.get('id'),
                title=content.get('title', ''),
                url=content.get('url', ''),
                score=content.get('score', 0),
                reason=content.get('reason', ''),
                ensemble_score=ensemble_score,
                engine_votes=dict(vote_data['votes']),
                technologies=content.get('technologies', []),
                content_type=content.get('content_type', 'article'),
                difficulty=content.get('difficulty', 'intermediate')
            )
            ensemble_results.append(ensemble_result)
        
        # Sort by ensemble score and limit results
        ensemble_results.sort(key=lambda x: x.ensemble_score, reverse=True)
        
        # Apply quality filters and return final results
        final_recommendations = self._apply_quality_filters(ensemble_results)
        
        return final_recommendations[:request.max_recommendations]

    def _apply_quality_filters(self, recommendations: List[EnsembleResult]) -> List[EnsembleResult]:
        """Apply strict quality filters to ensure only high-quality recommendations are returned"""
        filtered_recommendations = []
        
        for rec in recommendations:
            # Skip very low quality recommendations
            if rec.score < 50:  # Increased threshold
                continue
                
            # Skip content with poor URLs
            url = rec.url.lower()
            if any(bad_url in url for bad_url in [
                'file://', 'raw.githubusercontent.com', 'docs.google.com/spreadsheets',
                'leetcode.com/problem-list', 'codeforces.com/problemset'
            ]):
                continue
                
            # Skip generic or low-quality titles
            title = rec.title.lower()
            if any(generic in title for generic in [
                'javascript tutorial', 'python tutorial', 'html tutorial', 'css tutorial',
                'programming basics', 'coding tutorial', 'learn to code', 'syllabus',
                'batch term', 'shareable', 'google sheets', 'problem -', 'leetcode discuss'
            ]):
                continue
            
            # Skip content with too many technologies (likely noise)
            if len(rec.technologies) > 20:
                continue
                
            # Skip content with very short titles
            if len(rec.title.strip()) < 15:
                continue
                
            # Skip content with generic reasons
            reason = rec.reason.lower()
            if any(generic in reason for generic in [
                'high-quality educational resource', 'high-quality learning content',
                'helpful content', 'useful content', 'relevant content'
            ]):
                if rec.score < 80:  # Only allow generic reasons for very high scores
                    continue
            
            # Skip content that looks like raw files or documents
            if any(raw in title for raw in [
                'raw.githubusercontent.com', '.txt', '.html', 'syllabus', 'batch'
            ]):
                continue
            
            # Boost user's own content (if we have that attribute)
            if hasattr(rec, 'is_user_content') and rec.is_user_content:
                rec.score = rec.score * 1.3  # 30% boost
                if hasattr(rec, 'confidence'):
                    rec.confidence = min(1.0, rec.confidence * 1.2)
            
            filtered_recommendations.append(rec)
        
        # Sort by score
        filtered_recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return filtered_recommendations

    def _generate_reason(self, content, request_techs, similarity, tech_overlap):
        matched_techs = [t for t in content.get('technologies', []) if t in request_techs]
        if tech_overlap > 0 and matched_techs:
            return f"Recommended because it covers: {', '.join(matched_techs)}. Highly relevant to your request."
        elif similarity > 0.7:
            return "Semantically similar to your request."
        else:
            return "High-quality, relevant content."

# Global instance
_ensemble_engine = None

def get_ensemble_engine() -> OptimizedEnsembleEngine:
    """Get singleton ensemble engine instance"""
    global _ensemble_engine
    if _ensemble_engine is None:
        _ensemble_engine = OptimizedEnsembleEngine()
    return _ensemble_engine

def get_ensemble_recommendations(user_id: int, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get ensemble recommendations (optimized)"""
    try:
        # Create request object
        request = EnsembleRequest(
            user_id=user_id,
            title=request_data.get('title', ''),
            description=request_data.get('description', ''),
            technologies=request_data.get('technologies', ''),
            project_id=request_data.get('project_id'),
            max_recommendations=request_data.get('max_recommendations', 10),
            engines=request_data.get('engines', ['unified'])
        )
        
        # Get ensemble engine
        engine = get_ensemble_engine()
        
        # Get recommendations
        results = engine.get_ensemble_recommendations(request)
        
        # Convert to dict format
        return [asdict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Error in get_ensemble_recommendations: {e}")
        return [] 