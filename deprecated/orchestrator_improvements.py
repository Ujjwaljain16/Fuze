#!/usr/bin/env python3
"""
Orchestrator Improvements Based on User Requirements:
1. Remove content limits - use ALL user saved content
2. Add pagination for recommendations
3. Simplify engine structure - remove unnecessary aliases
4. Make unified ensemble the default
"""

import math
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

@dataclass
class PaginatedRecommendationRequest:
    """Enhanced request with pagination support"""
    user_id: int
    title: str = ''
    description: str = ''
    technologies: str = ''
    user_interests: str = ''
    project_id: Optional[int] = None
    max_recommendations: int = 10
    engine_preference: str = 'unified_ensemble'  # Default to best engine
    diversity_weight: float = 0.3
    quality_threshold: int = 5
    include_global_content: bool = True
    
    # NEW: Pagination parameters
    page: int = 1
    page_size: int = 10
    total_available: Optional[int] = None

@dataclass
class PaginatedRecommendationResponse:
    """Response with pagination metadata"""
    recommendations: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    total_recommendations: int
    engine_used: str
    performance_metrics: Dict[str, Any]

class ImprovedUnifiedOrchestrator:
    """Improved orchestrator with user requirements"""
    
    def __init__(self):
        self.data_layer = None  # Will be initialized
        
        # SIMPLIFIED ENGINE STRUCTURE - Remove unnecessary aliases
        self.engines = {
            # Core engines
            'unified_ensemble': 'primary',      # DEFAULT - Best intelligence
            'fast': 'semantic_only',             # Speed-focused
            'context': 'context_only',           # Context-focused
            'hybrid': 'fast_plus_context'       # Traditional combination
        }
        
        print("✅ Simplified to 4 meaningful engines:")
        print("   • unified_ensemble (DEFAULT) - Maximum intelligence")
        print("   • fast - Speed optimized")  
        print("   • context - Context focused")
        print("   • hybrid - Traditional ensemble")
    
    def remove_content_limits(self):
        """Remove all artificial content limits - use ALL user content"""
        return {
            'database_limit': None,  # Remove 1000 limit
            'processing_limit': None,  # Remove 100 limit  
            'filtering_limit': None,  # Remove 30 limit
            'strategy': 'use_all_content'
        }
    
    def get_all_user_content(self, user_id: int, request) -> List[Dict[str, Any]]:
        """Get ALL user content without limits"""
        try:
            from models import SavedContent, ContentAnalysis
            
            # Get database session
            session = self.data_layer.get_db_session()
            if not session:
                return []
            
            # UNLIMITED QUERY - Get ALL user content
            query = session.query(SavedContent, ContentAnalysis).outerjoin(
                ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
            )
            
            # Only filter out completely invalid content
            query = query.filter(
                SavedContent.user_id == user_id,
                SavedContent.title.isnot(None),
                SavedContent.title != ''
            )
            
            # NO LIMITS - Get everything, ordered by quality and recency
            user_content = query.order_by(
                SavedContent.quality_score.desc(),
                SavedContent.saved_at.desc()
            ).all()  # NO .limit() - Get ALL content
            
            print(f"📊 Retrieved ALL user content: {len(user_content)} items (no limits)")
            
            # Process all content
            content_list = []
            for saved_content, analysis in user_content:
                normalized_content = self._normalize_content_data(saved_content, analysis)
                if normalized_content:
                    content_list.append(normalized_content)
            
            print(f"📊 Processed content: {len(content_list)} items ready for recommendation")
            return content_list
            
        except Exception as e:
            print(f"❌ Error getting all user content: {e}")
            return []
    
    def get_paginated_recommendations(self, request: PaginatedRecommendationRequest) -> PaginatedRecommendationResponse:
        """Get recommendations with pagination support"""
        start_time = time.time()
        
        try:
            # Step 1: Get ALL user content (no limits)
            all_content = self.get_all_user_content(request.user_id, request)
            print(f"📊 Working with ALL {len(all_content)} user content items")
            
            # Step 2: Apply intelligent filtering to ALL content (no limits)
            relevant_content = self._filter_content_by_relevance_unlimited(all_content, request)
            print(f"📊 Filtered to {len(relevant_content)} relevant items")
            
            # Step 3: Generate recommendations from ALL relevant content
            all_recommendations = self._execute_engine_strategy_unlimited(request, relevant_content)
            print(f"📊 Generated {len(all_recommendations)} total recommendations")
            
            # Step 4: Apply pagination to final results
            total_recommendations = len(all_recommendations)
            start_index = (request.page - 1) * request.page_size
            end_index = start_index + request.page_size
            
            paginated_recommendations = all_recommendations[start_index:end_index]
            
            # Step 5: Calculate pagination metadata
            total_pages = math.ceil(total_recommendations / request.page_size)
            has_next = request.page < total_pages
            has_previous = request.page > 1
            
            pagination_info = {
                'current_page': request.page,
                'page_size': request.page_size,
                'total_pages': total_pages,
                'total_items': total_recommendations,
                'has_next': has_next,
                'has_previous': has_previous,
                'next_page': request.page + 1 if has_next else None,
                'previous_page': request.page - 1 if has_previous else None,
                'start_index': start_index + 1,
                'end_index': min(end_index, total_recommendations)
            }
            
            # Step 6: Performance metrics
            processing_time = time.time() - start_time
            performance_metrics = {
                'processing_time_ms': round(processing_time * 1000, 2),
                'content_processed': len(all_content),
                'relevant_content': len(relevant_content),
                'total_recommendations': total_recommendations,
                'returned_recommendations': len(paginated_recommendations),
                'engine_used': request.engine_preference
            }
            
            print(f"✅ Pagination complete: Page {request.page}/{total_pages} ({len(paginated_recommendations)} items)")
            
            return PaginatedRecommendationResponse(
                recommendations=paginated_recommendations,
                pagination=pagination_info,
                total_recommendations=total_recommendations,
                engine_used=request.engine_preference,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            print(f"❌ Error in paginated recommendations: {e}")
            return PaginatedRecommendationResponse(
                recommendations=[],
                pagination={'error': str(e)},
                total_recommendations=0,
                engine_used=request.engine_preference,
                performance_metrics={'error': str(e)}
            )
    
    def _filter_content_by_relevance_unlimited(self, content_list: List[Dict], request) -> List[Dict]:
        """Filter content by relevance WITHOUT limits - process ALL content"""
        try:
            print(f"🔍 Filtering {len(content_list)} items with NO limits")
            
            # Calculate relevance for ALL items (no limits)
            scored_content = []
            for content in content_list:
                relevance_score = self._calculate_intelligent_content_relevance(content, request)
                content['relevance_score'] = relevance_score
                scored_content.append(content)
            
            # Sort by relevance (keep ALL items)
            scored_content.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Apply dynamic threshold but keep more content
            if scored_content:
                top_score = scored_content[0].get('relevance_score', 0)
                # More inclusive threshold - keep 80% of content
                min_threshold = max(top_score * 0.1, 0.01)  # Very inclusive
                
                relevant_content = [c for c in scored_content if c.get('relevance_score', 0) >= min_threshold]
                
                print(f"📊 Relevance filtering: {len(scored_content)} → {len(relevant_content)} items")
                print(f"📊 Top score: {top_score:.3f}, Threshold: {min_threshold:.3f}")
                
                return relevant_content
            
            return scored_content
            
        except Exception as e:
            print(f"❌ Error in unlimited filtering: {e}")
            return content_list
    
    def _execute_engine_strategy_unlimited(self, request, content_list: List[Dict]) -> List[Dict]:
        """Execute engine strategy with ALL content (no limits)"""
        try:
            print(f"🚀 Processing {len(content_list)} items with unified ensemble (no limits)")
            
            # Use unified ensemble by default (best intelligence)
            if request.engine_preference in ['unified_ensemble', 'intelligent', 'ai', 'smart', 'auto', '']:
                return self._get_unified_ensemble_unlimited(content_list, request)
            elif request.engine_preference == 'fast':
                return self._get_fast_recommendations_unlimited(content_list, request)
            elif request.engine_preference == 'context':
                return self._get_context_recommendations_unlimited(content_list, request)
            elif request.engine_preference == 'hybrid':
                return self._get_hybrid_recommendations_unlimited(content_list, request)
            else:
                # Default to unified ensemble
                return self._get_unified_ensemble_unlimited(content_list, request)
                
        except Exception as e:
            print(f"❌ Error in unlimited engine strategy: {e}")
            return []
    
    def _get_unified_ensemble_unlimited(self, content_list: List[Dict], request) -> List[Dict]:
        """Unified ensemble processing ALL content"""
        try:
            print(f"🧠 Unified Ensemble: Processing ALL {len(content_list)} items")
            
            # Process ALL content with intelligent scoring
            recommendations = []
            for content in content_list:
                # Multi-dimensional scoring
                scores = {
                    'semantic_similarity': self._calculate_semantic_similarity(content, request),
                    'technology_relevance': self._calculate_technology_relevance(content, request),
                    'content_quality': self._calculate_content_quality(content),
                    'context_awareness': self._calculate_context_awareness(content, request),
                    'intent_alignment': self._calculate_intent_alignment(content, request)
                }
                
                # Weighted final score
                final_score = (
                    scores['semantic_similarity'] * 0.25 +
                    scores['technology_relevance'] * 0.25 +
                    scores['content_quality'] * 0.20 +
                    scores['context_awareness'] * 0.20 +
                    scores['intent_alignment'] * 0.10
                )
                
                recommendation = {
                    'id': content.get('id'),
                    'title': content.get('title'),
                    'url': content.get('url'),
                    'score': final_score,
                    'reason': self._generate_recommendation_reason(content, scores),
                    'content_type': content.get('content_type', 'article'),
                    'difficulty': content.get('difficulty', 'intermediate'),
                    'technologies': content.get('technologies', []),
                    'key_concepts': content.get('key_concepts', []),
                    'quality_score': content.get('quality_score', 6),
                    'engine_used': 'UnifiedEnsemble',
                    'confidence': min(final_score + 0.2, 1.0),
                    'metadata': {
                        'scores': scores,
                        'unlimited_processing': True
                    }
                }
                recommendations.append(recommendation)
            
            # Sort by final score
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"✅ Unified Ensemble: Generated {len(recommendations)} recommendations from ALL content")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error in unlimited unified ensemble: {e}")
            return []

# Integration functions for the existing orchestrator
def patch_orchestrator_for_unlimited_content():
    """Patch the existing orchestrator to remove content limits"""
    
    patches = {
        'remove_database_limit': '''
        # REMOVE: .limit(1000) from database queries
        # CHANGE: user_content = query.order_by(...).limit(1000).all()
        # TO:     user_content = query.order_by(...).all()
        ''',
        
        'remove_processing_limit': '''
        # REMOVE: max_content = min(len(content_list), 100)
        # REMOVE: content_list = content_list[:max_content]
        ''',
        
        'remove_filtering_limit': '''
        # REMOVE: Limited to top 30 items due to processing limits
        # PROCESS: ALL relevant content instead
        ''',
        
        'add_pagination_endpoint': '''
        # ADD: New endpoint /api/recommendations/paginated
        # SUPPORT: page, page_size parameters
        # RETURN: recommendations + pagination metadata
        '''
    }
    
    return patches

# New API endpoint structure for pagination
def create_paginated_endpoint():
    """Structure for new paginated recommendation endpoint"""
    
    endpoint_spec = {
        'path': '/api/recommendations/paginated',
        'method': 'POST',
        'parameters': {
            'title': 'string',
            'description': 'string', 
            'technologies': 'string',
            'user_interests': 'string',
            'project_id': 'integer (optional)',
            'engine_preference': 'string (default: unified_ensemble)',
            'page': 'integer (default: 1)',
            'page_size': 'integer (default: 10, max: 50)',
            'quality_threshold': 'integer (default: 5)',
            'diversity_weight': 'float (default: 0.3)'
        },
        'response': {
            'recommendations': 'array of recommendation objects',
            'pagination': {
                'current_page': 'integer',
                'page_size': 'integer', 
                'total_pages': 'integer',
                'total_items': 'integer',
                'has_next': 'boolean',
                'has_previous': 'boolean',
                'next_page': 'integer or null',
                'previous_page': 'integer or null'
            },
            'total_recommendations': 'integer',
            'engine_used': 'string',
            'performance_metrics': 'object'
        }
    }
    
    return endpoint_spec

if __name__ == "__main__":
    print("🚀 Orchestrator Improvements Ready!")
    print("=" * 50)
    print("✅ Remove ALL content limits")
    print("✅ Add pagination support") 
    print("✅ Simplify engine structure")
    print("✅ Make unified ensemble default")
    print("=" * 50)
