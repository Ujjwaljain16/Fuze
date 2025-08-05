#!/usr/bin/env python3
"""
Gemini Integration Layer for Unified Recommendation Orchestrator
Provides AI-enhanced recommendations with proper fallback strategies
"""

import os
import sys
import time
import logging
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_recommendation_orchestrator import UnifiedRecommendationRequest, UnifiedRecommendationResult, EnginePerformance

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GeminiAnalysisResult:
    """Result from Gemini analysis"""
    content_id: int
    enhanced_reason: str
    confidence_score: float
    learning_path_fit: float
    project_applicability: float
    skill_development: float
    key_insights: List[str]
    suggested_learning_order: List[str]
    analysis_metadata: Dict[str, Any]

class GeminiIntegrationLayer:
    """Gemini integration layer for enhanced recommendations"""
    
    def __init__(self):
        self.gemini_analyzer = None
        self.rate_limiter = None
        self.available = False
        self.performance = EnginePerformance(
            engine_name="GeminiIntegrationLayer",
            response_time_ms=0.0,
            success_rate=1.0,
            cache_hit_rate=0.0,
            error_count=0,
            last_used=datetime.utcnow(),
            total_requests=0
        )
        
        self._init_gemini_components()
    
    def _init_gemini_components(self):
        """Initialize Gemini components with error handling"""
        try:
            from gemini_utils import GeminiAnalyzer
            from rate_limit_handler import GeminiRateLimiter
            from multi_user_api_manager import get_user_api_key
            
            # Initialize components
            self.gemini_analyzer = GeminiAnalyzer()
            self.rate_limiter = GeminiRateLimiter()
            self.available = True
            
            logger.info("Gemini components initialized successfully")
            
        except Exception as e:
            logger.warning(f"Gemini components not available: {e}")
            self.gemini_analyzer = None
            self.rate_limiter = None
            self.available = False
    
    def enhance_recommendations(self, 
                              recommendations: List[UnifiedRecommendationResult], 
                              request: UnifiedRecommendationRequest,
                              user_id: int) -> List[UnifiedRecommendationResult]:
        """Enhance recommendations with Gemini analysis"""
        start_time = time.time()
        
        if not self.available:
            logger.warning("Gemini not available, returning original recommendations")
            return recommendations
        
        try:
            # Check rate limits
            if not self._check_rate_limit(user_id):
                logger.warning("Rate limit exceeded, returning original recommendations")
                return recommendations
            
            # Enhance top recommendations (limit to avoid API costs)
            enhanced_recommendations = []
            top_recommendations = recommendations[:5]  # Only enhance top 5
            
            # Process in parallel for better performance
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_rec = {
                    executor.submit(self._enhance_single_recommendation, rec, request, user_id): rec
                    for rec in top_recommendations
                }
                
                for future in as_completed(future_to_rec):
                    try:
                        enhanced_rec = future.result()
                        if enhanced_rec:
                            enhanced_recommendations.append(enhanced_rec)
                    except Exception as e:
                        logger.error(f"Error enhancing recommendation: {e}")
                        # Add original recommendation as fallback
                        enhanced_recommendations.append(future_to_rec[future])
            
            # Add remaining recommendations without enhancement
            enhanced_recommendations.extend(recommendations[5:])
            
            # Update performance metrics
            self._update_performance(start_time, True)
            
            return enhanced_recommendations
            
        except Exception as e:
            logger.error(f"Error in Gemini enhancement: {e}")
            self._update_performance(start_time, False)
            return recommendations
    
    def _enhance_single_recommendation(self, 
                                     recommendation: UnifiedRecommendationResult, 
                                     request: UnifiedRecommendationRequest,
                                     user_id: int) -> Optional[UnifiedRecommendationResult]:
        """Enhance a single recommendation with Gemini analysis"""
        try:
            # Create analysis prompt
            prompt = self._create_analysis_prompt(recommendation, request)
            
            # Get Gemini analysis
            analysis_result = self._get_gemini_analysis(prompt, user_id)
            
            if not analysis_result:
                return recommendation  # Return original if analysis fails
            
            # Enhance the recommendation
            enhanced_recommendation = self._apply_gemini_enhancement(recommendation, analysis_result)
            
            return enhanced_recommendation
            
        except Exception as e:
            logger.error(f"Error enhancing single recommendation: {e}")
            return recommendation
    
    def _create_analysis_prompt(self, recommendation: UnifiedRecommendationResult, request: UnifiedRecommendationRequest) -> str:
        """Create analysis prompt for Gemini"""
        prompt = f"""
        Analyze this learning content for a user's project and provide insights:
        
        USER PROJECT:
        Title: {request.title}
        Description: {request.description}
        Technologies: {request.technologies}
        User Interests: {request.user_interests}
        
        CONTENT TO ANALYZE:
        Title: {recommendation.title}
        Content Type: {recommendation.content_type}
        Difficulty: {recommendation.difficulty}
        Technologies: {', '.join(recommendation.technologies)}
        Key Concepts: {', '.join(recommendation.key_concepts)}
        
        Please provide analysis in JSON format with these fields:
        {{
            "enhanced_reason": "Detailed explanation of why this content is relevant",
            "confidence_score": 0.0-1.0,
            "learning_path_fit": 0.0-1.0,
            "project_applicability": 0.0-1.0,
            "skill_development": 0.0-1.0,
            "key_insights": ["insight1", "insight2"],
            "suggested_learning_order": ["step1", "step2"],
            "analysis_metadata": {{"complexity": "low/medium/high", "prerequisites": ["req1", "req2"]}}
        }}
        """
        
        return prompt
    
    def _get_gemini_analysis(self, prompt: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis from Gemini API"""
        try:
            if not self.gemini_analyzer:
                return None
            
            # Check rate limit again before API call
            if not self._check_rate_limit(user_id):
                return None
            
            # Make API call - try different method names
            if hasattr(self.gemini_analyzer, 'analyze_text'):
                response = self.gemini_analyzer.analyze_text(prompt)
            elif hasattr(self.gemini_analyzer, 'analyze_content'):
                response = self.gemini_analyzer.analyze_content(prompt)
            elif hasattr(self.gemini_analyzer, 'generate_response'):
                response = self.gemini_analyzer.generate_response(prompt)
            else:
                # Fallback to basic analysis
                logger.warning("No suitable Gemini method found, using fallback")
                return {
                    'enhanced_reason': recommendation.reason,
                    'confidence_score': recommendation.confidence,
                    'learning_path_fit': 0.5,
                    'project_applicability': 0.5,
                    'skill_development': 0.5,
                    'key_insights': [],
                    'suggested_learning_order': [],
                    'analysis_metadata': {}
                }
            
            # Parse JSON response
            try:
                analysis_data = json.loads(response)
                return analysis_data
            except json.JSONDecodeError:
                # Try to extract JSON from text response
                analysis_data = self._extract_json_from_text(response)
                return analysis_data
            
        except Exception as e:
            logger.error(f"Error getting Gemini analysis: {e}")
            return None
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text response"""
        try:
            # Find JSON-like content
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting JSON from text: {e}")
            return None
    
    def _apply_gemini_enhancement(self, 
                                recommendation: UnifiedRecommendationResult, 
                                analysis_result: Dict[str, Any]) -> UnifiedRecommendationResult:
        """Apply Gemini enhancement to recommendation"""
        try:
            # Update reason with enhanced explanation
            enhanced_reason = analysis_result.get('enhanced_reason', recommendation.reason)
            
            # Update confidence score
            confidence = analysis_result.get('confidence_score', recommendation.confidence)
            
            # Update metadata with Gemini insights
            metadata = recommendation.metadata.copy()
            metadata.update({
                'gemini_enhanced': True,
                'learning_path_fit': analysis_result.get('learning_path_fit', 0.5),
                'project_applicability': analysis_result.get('project_applicability', 0.5),
                'skill_development': analysis_result.get('skill_development', 0.5),
                'key_insights': analysis_result.get('key_insights', []),
                'suggested_learning_order': analysis_result.get('suggested_learning_order', []),
                'analysis_metadata': analysis_result.get('analysis_metadata', {})
            })
            
            # Create enhanced recommendation
            enhanced_recommendation = UnifiedRecommendationResult(
                id=recommendation.id,
                title=recommendation.title,
                url=recommendation.url,
                score=recommendation.score,
                reason=enhanced_reason,
                content_type=recommendation.content_type,
                difficulty=recommendation.difficulty,
                technologies=recommendation.technologies,
                key_concepts=recommendation.key_concepts,
                quality_score=recommendation.quality_score,
                engine_used=f"{recommendation.engine_used}+Gemini",
                confidence=confidence,
                metadata=metadata,
                cached=recommendation.cached
            )
            
            return enhanced_recommendation
            
        except Exception as e:
            logger.error(f"Error applying Gemini enhancement: {e}")
            return recommendation
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user can make Gemini API calls"""
        try:
            if not self.rate_limiter:
                return False
            
            from multi_user_api_manager import check_user_rate_limit
            rate_status = check_user_rate_limit(user_id)
            return rate_status.get('can_make_request', False)
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False
    
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
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'available': self.available,
            'response_time_ms': self.performance.response_time_ms,
            'success_rate': self.performance.success_rate,
            'total_requests': self.performance.total_requests,
            'error_count': self.performance.error_count,
            'last_used': self.performance.last_used.isoformat()
        }

# Global Gemini integration instance
_gemini_integration_instance = None

def get_gemini_integration() -> GeminiIntegrationLayer:
    """Get global Gemini integration instance"""
    global _gemini_integration_instance
    if _gemini_integration_instance is None:
        _gemini_integration_instance = GeminiIntegrationLayer()
    return _gemini_integration_instance

def enhance_recommendations_with_gemini(recommendations: List[UnifiedRecommendationResult], 
                                      request: UnifiedRecommendationRequest,
                                      user_id: int) -> List[UnifiedRecommendationResult]:
    """Enhance recommendations with Gemini analysis"""
    gemini_layer = get_gemini_integration()
    return gemini_layer.enhance_recommendations(recommendations, request, user_id) 