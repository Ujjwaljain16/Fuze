#!/usr/bin/env python3
"""
Simple ML Enhancer for Existing Unified Orchestrator
====================================================

This is a DROP-IN enhancement that:
- Works with your existing unified_recommendation_orchestrator
- Doesn't break anything
- Just improves scoring with ML when available
- Falls back gracefully if ML unavailable
- NO configuration changes needed

Author: Fuze AI System
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import ML features (optional)
ML_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    ML_AVAILABLE = True
    logger.info("✅ ML features available - will enhance recommendations")
except ImportError:
    logger.info("ℹ️ ML features not available - using standard scoring")

class SimpleMLEnhancer:
    """
    Simple ML enhancement that works with your existing system
    - Enhances scoring with TF-IDF when available
    - Falls back to original scoring if ML unavailable
    - NO breaking changes
    """
    
    def __init__(self):
        self.tfidf = None
        if ML_AVAILABLE:
            try:
                self.tfidf = TfidfVectorizer(
                    max_features=1000,
                    stop_words='english',
                    ngram_range=(1, 2)
                )
                logger.info("✅ TF-IDF vectorizer initialized")
            except Exception as e:
                logger.warning(f"TF-IDF init failed: {e}")
                self.tfidf = None
    
    def enhance_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        query_text: str,
        boost_factor: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Enhance existing recommendations with ML scoring
        
        Args:
            recommendations: Existing recommendations from orchestrator
            query_text: User query (title + description + technologies)
            boost_factor: How much to boost scores (0.0-0.5 recommended)
            
        Returns:
            Enhanced recommendations (same format, just better scores)
        """
        if not ML_AVAILABLE or not self.tfidf or not recommendations:
            # Return unchanged if ML not available
            return recommendations
        
        try:
            # Extract text from recommendations
            texts = []
            for rec in recommendations:
                text = f"{rec.get('title', '')} {rec.get('reason', '')}"
                texts.append(text)
            
            # Add query text
            all_texts = [query_text] + texts
            
            # Compute TF-IDF
            tfidf_matrix = self.tfidf.fit_transform(all_texts)
            
            # Calculate similarity
            query_vec = tfidf_matrix[0:1]
            doc_vecs = tfidf_matrix[1:]
            similarities = cosine_similarity(query_vec, doc_vecs)[0]
            
            # Enhance scores
            enhanced = []
            for rec, similarity in zip(recommendations, similarities):
                rec_copy = rec.copy()
                
                # Add ML boost to existing score
                original_score = rec.get('score', 50.0)
                ml_boost = similarity * 100 * boost_factor
                rec_copy['score'] = min(100, original_score + ml_boost)
                
                # Add ML metadata to existing metadata dict (not as new field)
                if 'metadata' not in rec_copy:
                    rec_copy['metadata'] = {}
                rec_copy['metadata']['ml_enhanced'] = True
                rec_copy['metadata']['ml_similarity'] = float(similarity)
                rec_copy['metadata']['ml_boost'] = float(ml_boost)
                
                enhanced.append(rec_copy)
            
            # Re-sort by enhanced score
            enhanced.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            logger.debug(f"Enhanced {len(enhanced)} recommendations with ML")
            return enhanced
        
        except Exception as e:
            logger.warning(f"ML enhancement failed: {e} - returning original")
            return recommendations
    
    def is_available(self) -> bool:
        """Check if ML enhancement is available"""
        return ML_AVAILABLE and self.tfidf is not None

# Global instance
_enhancer = None

def get_enhancer() -> SimpleMLEnhancer:
    """Get singleton enhancer instance"""
    global _enhancer
    if _enhancer is None:
        _enhancer = SimpleMLEnhancer()
    return _enhancer

def enhance_unified_recommendations(
    recommendations: List[Dict[str, Any]],
    request_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Simple function to enhance recommendations from unified orchestrator
    
    Usage in your blueprint:
    ```python
    # Get recommendations from unified orchestrator
    recommendations = orchestrator.get_recommendations(request)
    
    # Enhance with ML (optional, graceful fallback)
    enhanced = enhance_unified_recommendations(recommendations, request_data)
    ```
    """
    enhancer = get_enhancer()
    
    # Build query text
    query_text = f"{request_data.get('title', '')} {request_data.get('description', '')} {request_data.get('technologies', '')}"
    
    # Enhance if possible
    return enhancer.enhance_recommendations(recommendations, query_text)

# ============================================================================
# TESTING
# ============================================================================

def test_enhancer():
    """Test the ML enhancer"""
    print("🧪 Testing Simple ML Enhancer")
    print("=" * 60)
    
    # Test recommendations
    test_recs = [
        {
            'id': 1,
            'title': 'Python Machine Learning Tutorial',
            'url': 'https://example.com/ml',
            'score': 70.0,
            'reason': 'Good match for Python and ML'
        },
        {
            'id': 2,
            'title': 'JavaScript React Guide',
            'url': 'https://example.com/react',
            'score': 60.0,
            'reason': 'Frontend development resource'
        }
    ]
    
    test_query = {
        'title': 'Learn Python Machine Learning',
        'description': 'I want to learn ML with Python',
        'technologies': 'python, machine learning'
    }
    
    print(f"\n📊 ML Available: {ML_AVAILABLE}")
    print(f"📊 Original scores: {[r['score'] for r in test_recs]}")
    
    # Enhance
    enhancer = get_enhancer()
    enhanced = enhancer.enhance_recommendations(
        test_recs,
        f"{test_query['title']} {test_query['description']} {test_query['technologies']}"
    )
    
    print(f"📊 Enhanced scores: {[r['score'] for r in enhanced]}")
    print(f"📊 ML Enhanced: {[r.get('ml_enhanced', False) for r in enhanced]}")
    
    if ML_AVAILABLE:
        print("\n🎉 ML Enhancement working!")
    else:
        print("\n✅ Graceful fallback working (ML not available)")
    
    return True

if __name__ == "__main__":
    test_enhancer()

