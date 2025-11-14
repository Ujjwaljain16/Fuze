import numpy as np
from typing import List, Dict, Optional
from unified_recommendation_engine import UnifiedRecommendationEngine
from gemini_utils import GeminiAnalyzer
from rate_limit_handler import gemini_rate_limiter
import logging

logger = logging.getLogger(__name__)

class GeminiEnhancedRecommendationEngine:
    """
    Enhanced recommendation engine that combines unified engine with Gemini AI
    for superior content analysis and intelligent recommendations
    """
    
    def __init__(self):
        try:
            self.gemini_analyzer = GeminiAnalyzer()
            self.unified_engine = UnifiedRecommendationEngine()
            self.use_gemini = True
            # Cache for storing Gemini analysis results
            self.analysis_cache = {}
            logger.info("Gemini Enhanced Recommendation Engine initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}. Falling back to unified engine only.")
            self.gemini_analyzer = None
            self.unified_engine = UnifiedRecommendationEngine()
            self.use_gemini = False
    
    def get_enhanced_recommendations(self, bookmarks: List[Dict], user_input: Dict, max_recommendations: int = 10) -> Dict:
        """
        Get enhanced recommendations using both unified engine and Gemini AI
        """
        try:
            # Step 1: Extract context using unified engine
            context = self.unified_engine.extract_context_from_input(
                title=user_input.get('title', ''),
                description=user_input.get('description', ''),
                technologies=user_input.get('technologies', ''),
                user_interests=user_input.get('user_interests', '')
            )
            
            # Step 2: Enhance context with Gemini if available
            if self.use_gemini:
                try:
                    # Check rate limiting status
                    rate_status = gemini_rate_limiter.get_status()
                    if not rate_status['can_make_request']:
                        logger.warning(f"Rate limit reached, skipping Gemini context enhancement. Wait time: {rate_status['wait_time_seconds']} seconds")
                    else:
                        gemini_context = self.gemini_analyzer.analyze_user_context(
                            title=user_input.get('title', ''),
                            description=user_input.get('description', ''),
                            technologies=user_input.get('technologies', ''),
                            user_interests=user_input.get('user_interests', '')
                        )
                        # Merge Gemini insights with unified context
                        context = self._merge_contexts(context, gemini_context)
                        logger.info("Enhanced user context with Gemini analysis")
                except Exception as e:
                    logger.warning(f"Gemini context enhancement failed: {e}")
            
            # Step 3: Get initial recommendations first (without Gemini analysis)
            initial_recommendations = self.unified_engine.get_recommendations(
                bookmarks, context, max_recommendations * 2
            )
            
            # Step 4: Only enhance the top candidates with Gemini analysis
            enhanced_bookmarks = []
            total_bookmarks = len(bookmarks)
            analyzed_count = 0
            
            for i, bookmark in enumerate(bookmarks):
                # Only analyze top candidates or bookmarks that are likely to be recommended
                should_analyze = (
                    i < max_recommendations * 2 or  # Top candidates
                    any(rec.get('id') == bookmark.get('id') for rec in initial_recommendations[:max_recommendations * 3])  # Likely to be recommended
                )
                
                if should_analyze:
                    enhanced_bookmark = self._enhance_bookmark(bookmark)
                    analyzed_count += 1
                else:
                    enhanced_bookmark = bookmark  # Skip Gemini analysis for less relevant bookmarks
                
                enhanced_bookmarks.append(enhanced_bookmark)
            
            logger.info(f"Optimized Gemini analysis: analyzed {analyzed_count}/{total_bookmarks} bookmarks ({analyzed_count/total_bookmarks*100:.1f}%)")
            
            # Step 5: Get final recommendations with enhanced bookmarks
            final_recommendations = self.unified_engine.get_recommendations(
                enhanced_bookmarks, context, max_recommendations * 2
            )
            
            # Step 6: Enhance recommendations with Gemini insights
            enhanced_recommendations = []
            for rec in final_recommendations:
                enhanced_rec = self._enhance_recommendation(rec, context)
                enhanced_recommendations.append(enhanced_rec)
            
            # Step 7: Use Gemini for final ranking and reasoning (only for top recommendations)
            if self.use_gemini and enhanced_recommendations:
                try:
                    # Check rate limiting before ranking
                    rate_status = gemini_rate_limiter.get_status()
                    if not rate_status['can_make_request']:
                        logger.warning(f"Rate limit reached, skipping Gemini ranking. Wait time: {rate_status['wait_time_seconds']} seconds")
                        final_recommendations = enhanced_recommendations
                    else:
                        # Only rank the top recommendations to save time
                        top_recommendations = enhanced_recommendations[:max_recommendations * 2]
                        ranked_recommendations = self.gemini_analyzer.rank_recommendations(
                            top_recommendations, context
                        )
                        # Combine ranked top recommendations with the rest
                        final_recommendations = ranked_recommendations + enhanced_recommendations[max_recommendations * 2:]
                        logger.info("Applied Gemini ranking to top recommendations")
                except Exception as e:
                    logger.warning(f"Gemini ranking failed: {e}")
                    final_recommendations = enhanced_recommendations
            else:
                final_recommendations = enhanced_recommendations
            
            # Step 8: Format and return results
            return self._format_results(final_recommendations[:max_recommendations], context)
            
        except Exception as e:
            logger.error(f"Enhanced recommendation generation failed: {e}")
            # Fallback to unified engine only
            return self._get_fallback_recommendations(bookmarks, user_input, max_recommendations)
    
    def _enhance_bookmark(self, bookmark: Dict) -> Dict:
        """Enhance bookmark with Gemini analysis (with caching)"""
        if not self.use_gemini:
            return bookmark
        
        try:
            # Check if bookmark already has Gemini analysis
            if 'gemini_analysis' in bookmark:
                return bookmark
            
            # Create cache key based on bookmark content
            cache_key = f"{bookmark.get('title', '')}_{bookmark.get('url', '')}"
            
            # Check cache first
            if cache_key in self.analysis_cache:
                logger.info(f"Using cached Gemini analysis for: {bookmark.get('title', '')}")
                enhanced_bookmark = bookmark.copy()
                enhanced_bookmark['gemini_analysis'] = self.analysis_cache[cache_key]
                if self.analysis_cache[cache_key].get('technologies'):
                    enhanced_bookmark['enhanced_technologies'] = self.analysis_cache[cache_key]['technologies']
                return enhanced_bookmark
            
            # Analyze with Gemini (only for uncached bookmarks)
            logger.info(f"Analyzing bookmark with Gemini: {bookmark.get('title', '')}")
            gemini_analysis = self.gemini_analyzer.analyze_bookmark_content(
                title=bookmark.get('title', ''),
                description=bookmark.get('notes', ''),
                content=bookmark.get('extracted_text', ''),
                url=bookmark.get('url', '')
            )
            
            # Cache the analysis (limit cache size to prevent memory issues)
            if len(self.analysis_cache) >= 100:  # Limit to 100 cached analyses
                # Remove oldest entries (simple FIFO)
                oldest_keys = list(self.analysis_cache.keys())[:20]
                for key in oldest_keys:
                    del self.analysis_cache[key]
            
            self.analysis_cache[cache_key] = gemini_analysis
            
            # Merge Gemini analysis with bookmark
            enhanced_bookmark = bookmark.copy()
            enhanced_bookmark['gemini_analysis'] = gemini_analysis
            
            # Update technologies if Gemini found better ones
            if gemini_analysis.get('technologies'):
                enhanced_bookmark['enhanced_technologies'] = gemini_analysis['technologies']
            
            return enhanced_bookmark
            
        except Exception as e:
            logger.warning(f"Failed to enhance bookmark {bookmark.get('title', '')}: {e}")
            return bookmark
    
    def clear_cache(self):
        """Clear the Gemini analysis cache"""
        self.analysis_cache.clear()
        logger.info("Cleared Gemini analysis cache")
    
    def get_cache_stats(self):
        """Get cache statistics"""
        return {
            'cache_size': len(self.analysis_cache),
            'cached_analyses': list(self.analysis_cache.keys())
        }
    
    def _enhance_recommendation(self, recommendation: Dict, context: Dict) -> Dict:
        """Enhance recommendation with Gemini insights"""
        if not self.use_gemini:
            return recommendation
        
        try:
            # Generate intelligent reasoning
            reasoning = self.gemini_analyzer.generate_recommendation_reasoning(
                recommendation, context
            )
            
            # Update recommendation with Gemini insights
            enhanced_rec = recommendation.copy()
            enhanced_rec['gemini_reasoning'] = reasoning
            
            # Enhance score if Gemini analysis is available
            if 'gemini_analysis' in recommendation:
                gemini_score = recommendation['gemini_analysis'].get('relevance_score', 0)
                # Blend scores: 70% unified engine + 30% Gemini
                original_score = enhanced_rec.get('score_data', {}).get('total_score', 0)
                enhanced_score = (original_score * 0.7) + (gemini_score * 0.3)
                enhanced_rec['enhanced_score'] = enhanced_score
            
            return enhanced_rec
            
        except Exception as e:
            logger.warning(f"Failed to enhance recommendation: {e}")
            return recommendation
    
    def _merge_contexts(self, unified_context: Dict, gemini_context: Dict) -> Dict:
        """Merge unified engine context with Gemini insights"""
        merged = unified_context.copy()
        
        # Merge technologies (prefer Gemini's more accurate detection)
        if gemini_context.get('technologies'):
            gemini_techs = [{'category': tech, 'weight': 1.0} for tech in gemini_context['technologies']]
            merged['technologies'] = gemini_techs
        
        # Add Gemini-specific insights
        merged['gemini_insights'] = {
            'project_type': gemini_context.get('project_type', 'general'),
            'complexity_level': gemini_context.get('complexity_level', 'moderate'),
            'development_stage': gemini_context.get('development_stage', 'development'),
            'learning_needs': gemini_context.get('learning_needs', []),
            'technical_requirements': gemini_context.get('technical_requirements', []),
            'preferred_content_types': gemini_context.get('preferred_content_types', []),
            'difficulty_preference': gemini_context.get('difficulty_preference', 'intermediate'),
            'focus_areas': gemini_context.get('focus_areas', []),
            'project_summary': gemini_context.get('project_summary', '')
        }
        
        return merged
    
    def _format_results(self, recommendations: List[Dict], context: Dict) -> Dict:
        """Format final results for API response"""
        formatted_recommendations = []
        
        for rec in recommendations:
            # Get the best available score
            score = rec.get('enhanced_score') or rec.get('score_data', {}).get('total_score', 0)
            
            # Get the best available reasoning
            reasoning = rec.get('gemini_reasoning') or rec.get('score_data', {}).get('reason', '')
            
            formatted_rec = {
                "id": rec.get('id'),
                "title": rec.get('title'),
                "url": rec.get('url'),
                "notes": rec.get('notes'),
                "category": rec.get('category'),
                "score": round(score, 1),
                "reason": reasoning,
                "confidence": self._calculate_confidence(rec),
                "analysis": self._format_analysis(rec, context)
            }
            
            formatted_recommendations.append(formatted_rec)
        
        # Prepare context analysis
        context_analysis = {
            "input_analysis": {
                "title": context.get('title'),
                "technologies": [tech['category'] for tech in context.get('technologies', [])],
                "content_type": context.get('content_type'),
                "difficulty": context.get('difficulty'),
                "intent": context.get('intent'),
                "complexity_score": round(context.get('complexity_score', 0) * 100, 1),
                "key_concepts": context.get('key_concepts', [])[:10],
                "requirements": context.get('requirements', [])
            },
            "gemini_insights": context.get('gemini_insights', {}),
            "processing_stats": {
                "total_bookmarks_analyzed": len(recommendations),
                "relevant_bookmarks_found": len(formatted_recommendations),
                "gemini_enhanced": self.use_gemini
            }
        }
        
        return {
            "recommendations": formatted_recommendations,
            "context_analysis": context_analysis
        }
    
    def _format_analysis(self, recommendation: Dict, context: Dict) -> Dict:
        """Format analysis data for frontend"""
        analysis = {}
        
        # Get unified engine analysis
        if 'score_data' in recommendation:
            score_data = recommendation['score_data']
            analysis.update({
                "technology_match": round(score_data.get('scores', {}).get('tech_match', 0), 1),
                "content_relevance": round(score_data.get('scores', {}).get('content_relevance', 0), 1),
                "difficulty_alignment": round(score_data.get('scores', {}).get('difficulty_alignment', 0), 1),
                "intent_alignment": round(score_data.get('scores', {}).get('intent_alignment', 0), 1),
                "semantic_similarity": round(score_data.get('scores', {}).get('semantic_similarity', 0), 1),
                "bookmark_technologies": [tech['category'] for tech in score_data.get('bookmark_analysis', {}).get('technologies', [])],
                "content_type": score_data.get('bookmark_analysis', {}).get('content_type', ''),
                "difficulty": score_data.get('bookmark_analysis', {}).get('difficulty', ''),
                "intent": score_data.get('bookmark_analysis', {}).get('intent', ''),
                "key_concepts": score_data.get('bookmark_analysis', {}).get('key_concepts', [])[:5]
            })
        
        # Add Gemini analysis if available
        if 'gemini_analysis' in recommendation:
            gemini_analysis = recommendation['gemini_analysis']
            analysis.update({
                "gemini_technologies": gemini_analysis.get('technologies', []),
                "gemini_content_type": gemini_analysis.get('content_type', ''),
                "gemini_difficulty": gemini_analysis.get('difficulty', ''),
                "gemini_summary": gemini_analysis.get('summary', ''),
                "quality_indicators": gemini_analysis.get('quality_indicators', {}),
                "learning_objectives": gemini_analysis.get('learning_objectives', [])[:3],
                "target_audience": gemini_analysis.get('target_audience', ''),
                "prerequisites": gemini_analysis.get('prerequisites', [])[:3]
            })
        
        return analysis
    
    def _calculate_confidence(self, recommendation: Dict) -> float:
        """Calculate confidence score for recommendation"""
        confidence = 50.0  # Base confidence
        
        # Boost confidence if Gemini analysis is available
        if 'gemini_analysis' in recommendation:
            confidence += 20.0
            
            # Boost based on quality indicators
            quality = recommendation['gemini_analysis'].get('quality_indicators', {})
            if quality.get('completeness', 0) > 80:
                confidence += 10.0
            if quality.get('clarity', 0) > 80:
                confidence += 10.0
        
        # Boost based on score
        score = recommendation.get('enhanced_score') or recommendation.get('score_data', {}).get('total_score', 0)
        if score > 80:
            confidence += 10.0
        elif score > 60:
            confidence += 5.0
        
        return min(100.0, confidence)
    
    def _get_fallback_recommendations(self, bookmarks: List[Dict], user_input: Dict, max_recommendations: int) -> Dict:
        """Fallback to unified engine only"""
        logger.info("Using fallback unified engine recommendations")
        
        context = self.unified_engine.extract_context_from_input(
            title=user_input.get('title', ''),
            description=user_input.get('description', ''),
            technologies=user_input.get('technologies', ''),
            user_interests=user_input.get('user_interests', '')
        )
        
        recommendations = self.unified_engine.get_recommendations(
            bookmarks, context, max_recommendations
        )
        
        return self._format_results(recommendations, context)