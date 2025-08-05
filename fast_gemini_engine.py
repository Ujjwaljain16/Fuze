#!/usr/bin/env python3
"""
Advanced Optimized Gemini Recommendation Engine
Uses sophisticated caching, batching, and optimization techniques
to make Gemini-enhanced recommendations much faster
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from ultra_fast_engine import UltraFastEngine
from redis_utils import RedisCache
from gemini_utils import GeminiAnalyzer
from rate_limit_handler import GeminiRateLimiter
import logging
import time
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class AdvancedGeminiEngine:
    """
    Advanced optimized Gemini recommendation engine
    Uses multiple optimization layers for maximum speed
    """
    
    def __init__(self):
        self.ultra_engine = UltraFastEngine()
        self.redis_cache = RedisCache()
        
        # Initialize Gemini components with error handling
        try:
            self.gemini_analyzer = GeminiAnalyzer()
            self.rate_limiter = GeminiRateLimiter()
            self.gemini_available = True
            logger.info("Gemini components initialized successfully")
        except Exception as e:
            logger.warning(f"Gemini components not available: {e}")
            self.gemini_analyzer = None
            self.rate_limiter = None
            self.gemini_available = False
        
        # Multi-layer caching system
        self.session_cache = {}
        self.request_cache = {}
        self.analysis_cache = {}
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.batch_operations = 0
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Cache TTL settings (in seconds)
        self.SESSION_CACHE_TTL = 300  # 5 minutes
        self.REQUEST_CACHE_TTL = 600  # 10 minutes
        self.ANALYSIS_CACHE_TTL = 1800  # 30 minutes
        
        logger.info("Advanced Gemini Engine initialized with multi-layer optimization")
    
    def _generate_dynamic_reason(self, content: str) -> str:
        """Generate a dynamic recommendation reason based on content analysis"""
        if not content:
            return "Relevant learning content"
        
        content_lower = content.lower()
        
        # Extract technologies from content
        tech_keywords = {
            'java': ['java', 'jvm', 'bytecode', 'spring', 'maven'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
            'python': ['python', 'django', 'flask', 'pandas', 'numpy'],
            'dsa': ['algorithm', 'data structure', 'dsa', 'sorting', 'searching'],
            'instrumentation': ['instrumentation', 'monitoring', 'profiling', 'byte buddy', 'asm']
        }
        
        # Find matching technologies
        found_techs = []
        for tech, keywords in tech_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    found_techs.append(tech)
                    break
        
        # Remove duplicates
        found_techs = list(set(found_techs))
        
        # Generate dynamic reason
        if found_techs:
            tech_list = ', '.join(found_techs)
            return f"Content about {tech_list}"
        elif 'tutorial' in content_lower or 'guide' in content_lower:
            return "Tutorial content for learning"
        elif 'documentation' in content_lower or 'api' in content_lower:
            return "Documentation and reference material"
        elif 'example' in content_lower or 'sample' in content_lower:
            return "Practical examples and code samples"
        else:
            return "Relevant learning content"
    
    def get_fast_gemini_recommendations(self, bookmarks: List[Dict], user_input: Dict, max_recommendations: int = 10) -> Dict:
        """
        Get optimized Gemini-enhanced recommendations with advanced caching
        """
        start_time = time.time()
        
        try:
            # Generate cache key for this request
            request_key = self._generate_request_key(user_input, bookmarks)
            
            # Check multi-layer cache first
            cached_result = self._get_cached_result(request_key)
            if cached_result:
                self.cache_hits += 1
                logger.info(f"Cache hit! Returning cached result in {time.time() - start_time:.3f}s")
                return cached_result
            
            self.cache_misses += 1
            
            # Get ultra-fast base recommendations
            user_id = user_input.get('user_id', 1)
            ultra_result = self.ultra_engine.get_ultra_fast_recommendations(user_id)
            base_recommendations = ultra_result.get('recommendations', [])
            
            # Clean and validate base recommendations
            cleaned_recommendations = self._clean_recommendations(base_recommendations)
            
            if not cleaned_recommendations:
                logger.warning("No valid recommendations found, using fallback")
                return self._create_fallback_response(user_input, start_time)
            
            # Apply advanced Gemini optimization
            enhanced_recommendations = self._apply_advanced_gemini_optimization(
                cleaned_recommendations, user_input, max_recommendations
            )
            
            # Format results with enhanced context
            result = self._format_enhanced_results(enhanced_recommendations, user_input, start_time)
            
            # Cache the result
            self._cache_result(request_key, result)
            
            total_time = time.time() - start_time
            logger.info(f"Advanced Gemini recommendations completed in {total_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Advanced Gemini recommendations failed: {e}")
            # Create a proper fallback response instead of using ultra-fast engine
            return self._create_fallback_response(user_input, start_time)
    
    def _clean_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Clean and validate recommendations, filling in missing fields"""
        cleaned = []
        
        for rec in recommendations:
            if not rec:
                continue
                
            # Try to get content from database if it's missing
            content = rec.get('content', '')
            if not content and rec.get('id'):
                content = self._fetch_content_from_database(rec.get('id'))
            
            # Ensure all required fields exist
            cleaned_rec = {
                'id': rec.get('id'),
                'content': content or rec.get('title', '') or 'No content available',
                'url': rec.get('url', ''),
                'similarity_score': rec.get('similarity_score', 0.5),
                'quality_score': rec.get('quality_score', 0.5)
            }
            
            # Only add if we have at least an ID
            if cleaned_rec['id']:
                cleaned.append(cleaned_rec)
        
        return cleaned
    
    def _fetch_content_from_database(self, content_id: int) -> str:
        """Fetch content from database for a given ID"""
        try:
            from models import SavedContent
            from app import app
            
            with app.app_context():
                content = SavedContent.query.get(content_id)
                if content:
                    return content.extracted_text or content.title or content.url or ''
        except Exception as e:
            logger.warning(f"Failed to fetch content for ID {content_id}: {e}")
        
        return ''
    
    def _create_fallback_response(self, user_input: Dict, start_time: float) -> Dict:
        """Create a proper fallback response when Gemini is not available"""
        return {
            "recommendations": [],
            "context_analysis": {
                "input_analysis": {
                    "title": user_input.get('title'),
                    "technologies": user_input.get('technologies', '').split(',') if user_input.get('technologies') else [],
                    "content_type": "fallback",
                    "difficulty": "intermediate",
                    "intent": "learning"
                },
                "processing_stats": {
                    "total_recommendations": 0,
                    "gemini_enhanced": 0,
                    "cache_hits": self.cache_hits,
                    "cache_misses": self.cache_misses,
                    "api_calls": self.api_calls,
                    "batch_operations": self.batch_operations,
                    "engine": "advanced_gemini",
                    "response_type": "fallback",
                    "gemini_status": "unavailable",
                    "total_time": time.time() - start_time
                }
            }
        }
    
    def _generate_request_key(self, user_input: Dict, bookmarks: List[Dict]) -> str:
        """Generate unique cache key for request"""
        key_data = {
            'user_input': user_input,
            'bookmarks_count': len(bookmarks),
            'timestamp': int(time.time() / 60)  # Round to minute for better cache hits
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_result(self, request_key: str) -> Optional[Dict]:
        """Check multi-layer cache for result"""
        # Check session cache first (fastest)
        if request_key in self.session_cache:
            cache_data = self.session_cache[request_key]
            if time.time() - cache_data['timestamp'] < self.SESSION_CACHE_TTL:
                return cache_data['result']
            else:
                del self.session_cache[request_key]
        
        # Check Redis cache
        try:
            cached = self.redis_cache.get_cache(f"gemini_request:{request_key}")
            if cached:
                result = json.loads(cached)
                # Store in session cache for faster future access
                self.session_cache[request_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
                return result
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        return None
    
    def _cache_result(self, request_key: str, result: Dict):
        """Cache result in multiple layers"""
        # Session cache
        self.session_cache[request_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Redis cache
        try:
            self.redis_cache.set_cache(
                f"gemini_request:{request_key}",
                json.dumps(result),
                ttl=self.REQUEST_CACHE_TTL
            )
        except Exception as e:
            logger.warning(f"Failed to cache in Redis: {e}")
    
    def _apply_advanced_gemini_optimization(self, base_recommendations: List[Dict], user_input: Dict, max_recommendations: int) -> List[Dict]:
        """
        Apply ULTRA-FAST Gemini optimization with SINGLE API call
        """
        if not base_recommendations:
            return []
        
        # Select top candidates for Gemini enhancement (max 3 for speed)
        top_candidates = base_recommendations[:min(3, len(base_recommendations))]
        
        # Check if we have cached analysis for ALL candidates
        all_cached = True
        cached_analyses = {}
        
        for candidate in top_candidates:
            analysis_key = self._generate_analysis_key(candidate, user_input)
            cached_analysis = self._get_cached_analysis(analysis_key)
            if cached_analysis:
                cached_analyses[candidate['id']] = cached_analysis
            else:
                all_cached = False
        
        # If all cached, return immediately (ULTRA FAST)
        if all_cached:
            enhanced_candidates = []
            for candidate in top_candidates:
                candidate.update(cached_analyses[candidate['id']])
                candidate['enhanced'] = True
                candidate['enhancement_status'] = 'cached'
                enhanced_candidates.append(candidate)
            
            # Add remaining candidates
            remaining_candidates = base_recommendations[len(top_candidates):max_recommendations]
            for candidate in remaining_candidates:
                candidate['enhanced'] = False
                candidate['enhancement_status'] = 'ultra_fast_only'
                enhanced_candidates.append(candidate)
            
            return enhanced_candidates[:max_recommendations]
        
        # SINGLE BATCH API CALL for all candidates
        try:
            enhanced_candidates = self._batch_gemini_enhancement(top_candidates, user_input)
        except Exception as e:
            logger.warning(f"Batch enhancement failed: {e}")
            # Fallback to individual calls
            enhanced_candidates = []
            for candidate in top_candidates:
                try:
                    analysis_key = self._generate_analysis_key(candidate, user_input)
                    enhanced_candidate = self._quick_gemini_enhancement(candidate, user_input, analysis_key)
                    enhanced_candidates.append(enhanced_candidate)
                except Exception as e2:
                    logger.warning(f"Individual enhancement failed for {candidate.get('id')}: {e2}")
                    candidate['enhanced'] = False
                    candidate['enhancement_status'] = 'error'
                    enhanced_candidates.append(candidate)
        
        # Add remaining candidates without Gemini enhancement
        remaining_candidates = base_recommendations[len(top_candidates):max_recommendations]
        for candidate in remaining_candidates:
            candidate['enhanced'] = False
            candidate['enhancement_status'] = 'ultra_fast_only'
            enhanced_candidates.append(candidate)
        
        return enhanced_candidates[:max_recommendations]
    
    def _generate_analysis_key(self, candidate: Dict, user_input: Dict) -> str:
        """Generate cache key for candidate analysis"""
        content = candidate.get('content', '') or ''
        key_data = {
            'candidate_id': candidate.get('id'),
            'candidate_content': content[:200],  # First 200 chars
            'user_technologies': user_input.get('technologies', ''),
            'user_title': user_input.get('title', '')
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_analysis(self, analysis_key: str) -> Optional[Dict]:
        """Get cached Gemini analysis"""
        # Check session cache first
        if analysis_key in self.analysis_cache:
            cache_data = self.analysis_cache[analysis_key]
            if time.time() - cache_data['timestamp'] < self.ANALYSIS_CACHE_TTL:
                return cache_data['analysis']
            else:
                del self.analysis_cache[analysis_key]
        
        # Check Redis cache
        try:
            cached = self.redis_cache.get_cache(f"gemini_analysis:{analysis_key}")
            if cached:
                analysis = json.loads(cached)
                # Store in session cache
                self.analysis_cache[analysis_key] = {
                    'analysis': analysis,
                    'timestamp': time.time()
                }
                return analysis
        except Exception as e:
            logger.warning(f"Analysis cache error: {e}")
        
        return None
    
    def _batch_gemini_enhancement(self, candidates: List[Dict], user_input: Dict) -> List[Dict]:
        """
        ULTRA-FAST: Single batch API call for all candidates
        """
        try:
            if self.gemini_available and self.gemini_analyzer:
                # Check rate limits
                if self.rate_limiter and hasattr(self.rate_limiter, 'can_make_request'):
                    if not self.rate_limiter.can_make_request():
                        for candidate in candidates:
                            candidate['enhanced'] = False
                            candidate['enhancement_status'] = 'rate_limited'
                        return candidates
                
                # Create batch prompt for all candidates
                batch_prompt = self._create_batch_prompt(candidates, user_input)
                
                # SINGLE API CALL for all candidates
                start_api_time = time.time()
                batch_response = self.gemini_analyzer.analyze_bookmark_content(
                    title=f"Batch Analysis: {len(candidates)} candidates",
                    description=batch_prompt,
                    content=batch_prompt,
                    url=""
                )
                api_time = time.time() - start_api_time
                
                self.api_calls += 1
                
                # Extract insights for each candidate
                enhanced_candidates = []
                for i, candidate in enumerate(candidates):
                    try:
                        enhanced_data = self._extract_batch_insights(batch_response, candidate, i)
                        
                        # Cache individual analysis
                        analysis_key = self._generate_analysis_key(candidate, user_input)
                        self._cache_analysis(analysis_key, enhanced_data)
                        
                        # Update candidate
                        candidate.update(enhanced_data)
                        candidate['enhanced'] = True
                        candidate['enhancement_status'] = 'batch_enhanced'
                        candidate['api_time'] = api_time / len(candidates)  # Average time per candidate
                        
                        enhanced_candidates.append(candidate)
                        
                    except Exception as e:
                        logger.warning(f"Error processing candidate {candidate.get('id')} in batch: {e}")
                        candidate['enhanced'] = False
                        candidate['enhancement_status'] = 'batch_error'
                        enhanced_candidates.append(candidate)
                
                logger.info(f"Batch Gemini enhancement completed in {api_time:.3f}s for {len(candidates)} candidates")
                return enhanced_candidates
            else:
                logger.warning("Gemini not available, using semantic fallback enhancement")
                return self._semantic_fallback_enhancement(candidates, user_input)
            
        except Exception as e:
            logger.warning(f"Gemini enhancement failed, using semantic fallback: {e}")
            return self._semantic_fallback_enhancement(candidates, user_input)

    def _create_batch_prompt(self, candidates: List[Dict], user_input: Dict) -> str:
        """Create optimized batch prompt for multiple candidates"""
        user_tech = user_input.get('technologies', '')
        user_title = user_input.get('title', '')
        
        candidates_data = []
        for i, candidate in enumerate(candidates):
            content = candidate.get('content', '')[:300]  # Limit content
            candidates_data.append({
                'id': candidate.get('id'),
                'title': candidate.get('title', ''),
                'content': content,
                'index': i
            })
        
        prompt = f"""
Quick Batch Analysis (Max 200 words total):

User Interest: {user_title}
Technologies: {user_tech}

Analyze these {len(candidates)} candidates and provide insights for each:

{json.dumps(candidates_data, indent=2)}

Return JSON array with analysis for each candidate:
[
  {{
    "index": 0,
    "relevance_score": 8,
    "key_benefit": "Brief benefit",
    "difficulty": "intermediate",
    "technologies": ["tech1", "tech2"]
  }},
  ...
]

Focus on: relevance, key benefit, difficulty, technologies
"""
        return prompt.strip()

    def _extract_batch_insights(self, batch_response: Dict, candidate: Dict, index: int) -> Dict:
        """Extract insights for specific candidate from batch response"""
        try:
            # Try to extract from batch response
            if isinstance(batch_response, dict) and 'technologies' in batch_response:
                return {
                    'relevance_score': batch_response.get('relevance_score', 7),
                    'key_benefit': batch_response.get('summary', 'Relevant content for learning'),
                    'difficulty': batch_response.get('difficulty', 'intermediate'),
                    'confidence': batch_response.get('quality_indicators', {}).get('clarity', 85.0),
                    'analysis_summary': batch_response.get('summary', '')[:100] + '...' if batch_response.get('summary') else 'Analysis completed',
                    'technologies': batch_response.get('technologies', []),
                    'content_type': batch_response.get('content_type', 'article'),
                    'target_audience': batch_response.get('target_audience', 'intermediate')
                }
        except Exception as e:
            logger.warning(f"Error extracting batch insights: {e}")
        
        # Generate dynamic fallback based on content
        content = candidate.get('content', '')
        dynamic_reason = self._generate_dynamic_reason(content)
        
        return {
            'relevance_score': 7,
            'key_benefit': dynamic_reason,
            'difficulty': 'intermediate',
            'confidence': 75.0,
            'analysis_summary': 'Dynamic analysis completed',
            'technologies': [],
            'content_type': 'article',
            'target_audience': 'intermediate'
        }

    def _quick_gemini_enhancement(self, candidate: Dict, user_input: Dict, analysis_key: str) -> Dict:
        """
        Apply quick Gemini enhancement with aggressive caching
        """
        try:
            if self.gemini_available and self.gemini_analyzer:
                # Prepare focused analysis prompt
                analysis_prompt = self._create_focused_prompt(candidate, user_input)
                
                # Check rate limits
                if self.rate_limiter and hasattr(self.rate_limiter, 'can_make_request'):
                    if not self.rate_limiter.can_make_request():
                        logger.warning("Rate limit reached, skipping Gemini enhancement")
                        candidate['enhanced'] = False
                        candidate['enhancement_status'] = 'rate_limited'
                        return candidate
                elif self.rate_limiter and hasattr(self.rate_limiter, 'get_status'):
                    status = self.rate_limiter.get_status()
                    if not status.get('can_make_request', True):
                        logger.warning("Rate limit reached, skipping Gemini enhancement")
                        candidate['enhanced'] = False
                        candidate['enhancement_status'] = 'rate_limited'
                        return candidate
                
                # Make focused API call
                start_api_time = time.time()
                # Use the correct method from GeminiAnalyzer
                analysis_result = self.gemini_analyzer.analyze_bookmark_content(
                    title=candidate.get('title', ''),
                    description=candidate.get('content', '')[:500],
                    content=candidate.get('content', ''),
                    url=candidate.get('url', '')
                )
                api_time = time.time() - start_api_time
                
                self.api_calls += 1
                
                # Extract key insights quickly
                enhanced_data = self._extract_quick_insights(analysis_result, candidate)
                
                # Cache the analysis
                self._cache_analysis(analysis_key, enhanced_data)
                
                # Update candidate
                candidate.update(enhanced_data)
                candidate['enhanced'] = True
                candidate['enhancement_status'] = 'enhanced'
                candidate['api_time'] = api_time
                
                logger.info(f"Gemini enhancement completed in {api_time:.3f}s")
            else:
                logger.warning("Gemini not available, using semantic fallback enhancement")
                return self._semantic_fallback_enhancement_single(candidate, user_input)
            
        except Exception as e:
            logger.warning(f"Gemini enhancement failed, using semantic fallback: {e}")
            return self._semantic_fallback_enhancement_single(candidate, user_input)
        
        return candidate
    
    def _create_focused_prompt(self, candidate: Dict, user_input: Dict) -> str:
        """Create focused, optimized prompt for quick analysis"""
        content = candidate.get('content', '')[:500]  # Limit content length
        title = user_input.get('title', '')
        technologies = user_input.get('technologies', '')
        
        prompt = f"""
Quick Analysis Request (Max 100 words response):

Content: {content[:300]}...
User Interest: {title}
Technologies: {technologies}

Provide ONLY:
1. Relevance score (1-10)
2. Key benefit (one sentence)
3. Difficulty level (beginner/intermediate/advanced)

Format: JSON with keys: relevance_score, key_benefit, difficulty
"""
        return prompt.strip()
    
    def _extract_quick_insights(self, analysis_result: Dict, candidate: Dict) -> Dict:
        """Extract insights from Gemini analysis quickly"""
        try:
            # Handle dictionary response from analyze_bookmark_content
            if isinstance(analysis_result, dict):
                return {
                    'relevance_score': analysis_result.get('relevance_score', 7),
                    'key_benefit': analysis_result.get('summary', 'Relevant content for learning'),
                    'difficulty': analysis_result.get('difficulty', 'intermediate'),
                    'confidence': analysis_result.get('quality_indicators', {}).get('clarity', 85.0),
                    'analysis_summary': analysis_result.get('summary', '')[:100] + '...' if analysis_result.get('summary') else 'Analysis completed',
                    'technologies': analysis_result.get('technologies', []),
                    'content_type': analysis_result.get('content_type', 'article'),
                    'target_audience': analysis_result.get('target_audience', 'intermediate')
                }
        except Exception as e:
            logger.warning(f"Error extracting insights: {e}")
        
        # Generate dynamic fallback based on content
        content = candidate.get('content', '')
        dynamic_reason = self._generate_dynamic_reason(content)
        
        return {
            'relevance_score': 7,
            'key_benefit': dynamic_reason,
            'difficulty': 'intermediate',
            'confidence': 75.0,
            'analysis_summary': 'Dynamic analysis completed',
            'technologies': [],
            'content_type': 'article',
            'target_audience': 'intermediate'
        }
    
    def _cache_analysis(self, analysis_key: str, analysis: Dict):
        """Cache analysis result"""
        # Session cache
        self.analysis_cache[analysis_key] = {
            'analysis': analysis,
            'timestamp': time.time()
        }
        
        # Redis cache
        try:
            self.redis_cache.set_cache(
                f"gemini_analysis:{analysis_key}",
                json.dumps(analysis),
                ttl=self.ANALYSIS_CACHE_TTL
            )
        except Exception as e:
            logger.warning(f"Failed to cache analysis in Redis: {e}")
    
    def _format_enhanced_results(self, recommendations: List[Dict], user_input: Dict, start_time: float) -> Dict:
        """Format enhanced results with detailed context"""
        formatted_recommendations = []
        enhanced_count = 0
        
        for rec in recommendations:
            try:
                score = rec.get('similarity_score', 0) * 100
                relevance_score = rec.get('relevance_score', 7)
                
                # Combine scores intelligently
                final_score = (score * 0.6) + (relevance_score * 10 * 0.4)
                
                content = rec.get('content', '') or ''
                
                # Generate dynamic reason if key_benefit is generic
                key_benefit = rec.get('key_benefit', '')
                if key_benefit in ['Relevant content for learning', 'Recommended based on content quality']:
                    dynamic_reason = self._generate_dynamic_reason(content)
                else:
                    dynamic_reason = key_benefit
                
                formatted_rec = {
                    "id": rec.get('id'),
                    "title": content[:100] if content else "No title available",
                    "url": rec.get('url', ''),
                    "notes": content[:200] if content else "No content available",
                    "category": "gemini_enhanced" if rec.get('enhanced') else "general",
                    "score": round(final_score, 1),
                    "reason": dynamic_reason,
                    "confidence": rec.get('confidence', 75.0),
                    "enhanced": rec.get('enhanced', False),
                    "enhancement_status": rec.get('enhancement_status', 'none'),
                    "difficulty": rec.get('difficulty', 'intermediate'),
                    "relevance_score": relevance_score
                }
                
                if rec.get('enhanced'):
                    enhanced_count += 1
                
                formatted_recommendations.append(formatted_rec)
                
            except Exception as e:
                logger.warning(f"Error formatting recommendation: {e}")
                continue
        
                    # Sort by final score
            formatted_recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            # Add diversity sampling to ensure varied content types
            diverse_recommendations = self._add_diversity_sampling(formatted_recommendations, max_recommendations=len(formatted_recommendations))
            
            return {
                "recommendations": diverse_recommendations
            }
    
    def clear_caches(self):
        """Clear all caches"""
        self.session_cache.clear()
        self.request_cache.clear()
        self.analysis_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.batch_operations = 0
        logger.info("Cleared all advanced caches")
    
    def get_cache_stats(self):
        """Get detailed cache statistics"""
        return {
            'session_cache_size': len(self.session_cache),
            'request_cache_size': len(self.request_cache),
            'analysis_cache_size': len(self.analysis_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'api_calls': self.api_calls,
            'batch_operations': self.batch_operations,
            'hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    
    def _semantic_fallback_enhancement(self, candidates: List[Dict], user_input: Dict) -> List[Dict]:
        """Basic semantic enhancement when Gemini is not available or fails"""
        enhanced_candidates = []
        
        try:
            for candidate in candidates:
                enhanced_candidate = self._semantic_fallback_enhancement_single(candidate, user_input)
                enhanced_candidates.append(enhanced_candidate)
            
            logger.info(f"Applied semantic fallback enhancement to {len(candidates)} candidates")
            return enhanced_candidates
            
        except Exception as e:
            logger.error(f"Error in semantic fallback enhancement: {e}")
            # Ultimate fallback: return original candidates with basic enhancement
            for candidate in candidates:
                candidate['enhanced'] = False
                candidate['enhancement_status'] = 'semantic_fallback_failed'
                candidate['reason'] = "High-quality content from your saved bookmarks"
            return candidates
    
    def _semantic_fallback_enhancement_single(self, candidate: Dict, user_input: Dict) -> Dict:
        """Apply semantic enhancement to a single candidate"""
        try:
            enhanced_candidate = candidate.copy()
            
            # Generate basic enhancement using content analysis
            title = candidate.get('title', '').lower()
            content = candidate.get('content', '').lower()
            
            # Extract technologies
            tech_keywords = ['python', 'javascript', 'java', 'react', 'node', 'sql', 'docker', 'aws', 'git', 'html', 'css', 'typescript', 'vue', 'angular', 'mongodb', 'postgresql', 'redis', 'kubernetes', 'terraform', 'jenkins', 'github', 'gitlab']
            found_techs = [tech for tech in tech_keywords if tech in title or content]
            
            # Determine content type
            if any(word in title for word in ['tutorial', 'guide', 'learn', 'getting started']):
                content_type = 'tutorial'
            elif any(word in title for word in ['docs', 'documentation', 'api', 'reference']):
                content_type = 'documentation'
            elif any(word in title for word in ['project', 'github', 'repo', 'repository']):
                content_type = 'project'
            elif any(word in title for word in ['leetcode', 'interview', 'question', 'problem']):
                content_type = 'practice'
            elif any(word in title for word in ['best practice', 'pattern', 'architecture']):
                content_type = 'best practice'
            else:
                content_type = 'resource'
            
            # Build reason
            reason_parts = []
            if found_techs:
                reason_parts.append(f"Content about {', '.join(found_techs[:2])}")
            else:
                reason_parts.append("High-quality technical content")
            
            if content_type != 'resource':
                reason_parts.append(f"({content_type})")
            
            if user_input.get('title'):
                reason_parts.append(f"relevant to {user_input['title']}")
            
            # Add quality indicator
            quality_score = candidate.get('quality_score', 7)
            if quality_score >= 9:
                reason_parts.append("- Excellent quality")
            elif quality_score >= 7:
                reason_parts.append("- High quality")
            
            enhanced_candidate['reason'] = ' '.join(reason_parts)
            enhanced_candidate['enhanced'] = True
            enhanced_candidate['enhancement_status'] = 'semantic_fallback'
            enhanced_candidate['enhancement_type'] = 'semantic_fallback'
            
            return enhanced_candidate
            
        except Exception as e:
            logger.error(f"Error in semantic fallback enhancement for single candidate: {e}")
            candidate['enhanced'] = False
            candidate['enhancement_status'] = 'semantic_fallback_failed'
            candidate['reason'] = "High-quality content from your saved bookmarks"
            return candidate
    
    def _add_diversity_sampling(self, recommendations: List[Dict], max_recommendations: int) -> List[Dict]:
        """Add diversity sampling to ensure varied content types and categories"""
        if not recommendations:
            return recommendations
        
        try:
            # Categorize recommendations by content type
            categorized_recommendations = {}
            diverse_recommendations = []
            
            for rec in recommendations:
                # Determine content category
                category = self._determine_content_category(rec)
                rec['category'] = category
                
                if category not in categorized_recommendations:
                    categorized_recommendations[category] = []
                categorized_recommendations[category].append(rec)
            
            # Add diverse recommendations from each category
            categories_used = set()
            max_per_category = max(1, max_recommendations // len(categorized_recommendations)) if categorized_recommendations else 1
            
            # First pass: add top recommendations from each category
            for category, recs in categorized_recommendations.items():
                if len(diverse_recommendations) >= max_recommendations:
                    break
                
                # Add top recommendations from this category
                category_recs = recs[:max_per_category]
                diverse_recommendations.extend(category_recs)
                categories_used.add(category)
            
            # Second pass: fill remaining slots with best overall recommendations
            remaining_slots = max_recommendations - len(diverse_recommendations)
            if remaining_slots > 0:
                # Get recommendations not yet included
                used_ids = {rec.get('id', 0) for rec in diverse_recommendations}
                remaining_recs = [rec for rec in recommendations if rec.get('id', 0) not in used_ids]
                
                # Add best remaining recommendations
                diverse_recommendations.extend(remaining_recs[:remaining_slots])
            
            # Ensure we don't exceed max_recommendations
            diverse_recommendations = diverse_recommendations[:max_recommendations]
            
            logger.info(f"Fast Gemini diversity sampling: {len(categories_used)} categories, {len(diverse_recommendations)} recommendations")
            return diverse_recommendations
            
        except Exception as e:
            logger.error(f"Error in fast Gemini diversity sampling: {e}")
            return recommendations[:max_recommendations]
    
    def _determine_content_category(self, recommendation: Dict) -> str:
        """Determine content category based on title and content"""
        try:
            title = recommendation.get('title', '').lower()
            content = recommendation.get('content', '').lower()
            
            # Fallback to title/content analysis
            if any(word in title for word in ['tutorial', 'guide', 'learn', 'getting started', 'how to']):
                return 'tutorial'
            elif any(word in title for word in ['docs', 'documentation', 'api', 'reference', 'manual']):
                return 'documentation'
            elif any(word in title for word in ['project', 'github', 'repo', 'repository', 'demo', 'example']):
                return 'project'
            elif any(word in title for word in ['leetcode', 'interview', 'question', 'problem', 'challenge']):
                return 'practice'
            elif any(word in title for word in ['best practice', 'pattern', 'architecture', 'design']):
                return 'best_practice'
            elif any(word in title for word in ['news', 'article', 'blog', 'post']):
                return 'article'
            else:
                return 'general'
                
        except Exception as e:
            logger.error(f"Error determining content category: {e}")
            return 'general'

# Global instance
fast_gemini_engine = AdvancedGeminiEngine() 