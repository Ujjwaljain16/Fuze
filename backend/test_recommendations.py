#!/usr/bin/env python3
"""
Test recommendation system improvements
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

def test_recommendations():
    """Test recommendation system with Go backend request"""
    try:
        from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator
        from ml.unified_recommendation_orchestrator import UnifiedRecommendationRequest

        # Create test request for Go backend learning
        request = UnifiedRecommendationRequest(
            title="Learn and develop backend in Go lang",
            description="Learn go lang backend concepts",
            technologies=["Go lang", "Backend", "RESTful"],
            user_interests="",
            project_id=None,
            task_id=None,
            subtask_id=None
        )

        # Create orchestrator
        orchestrator = UnifiedRecommendationOrchestrator()

        # Test with sample content that should match
        test_content = [
            {
                'id': 1,
                'title': 'Go Backend Tutorial: Building REST APIs',
                'extracted_text': 'Learn Go programming for backend development with REST APIs',
                'technologies': ['Go', 'Backend', 'REST'],
                'quality_score': 9,
                'content_type': 'tutorial',
                'embedding': [0.1] * 384  # Dummy embedding
            },
            {
                'id': 2,
                'title': 'Reddit - The heart of the internet',
                'extracted_text': 'Reddit is a social media platform',
                'technologies': ['social media'],
                'quality_score': 3,
                'content_type': 'social',
                'embedding': [0.2] * 384
            },
            {
                'id': 3,
                'title': 'JavaScript React Tutorial',
                'extracted_text': 'Learn React JavaScript framework',
                'technologies': ['JavaScript', 'React'],
                'quality_score': 8,
                'content_type': 'tutorial',
                'embedding': [0.3] * 384
            }
        ]

        print("🧪 TESTING RECOMMENDATION SYSTEM")
        print("=" * 50)
        print(f"Request: {request.title}")
        print(f"Technologies: {request.technologies}")
        print()

        # Get recommendations
        recommendations = orchestrator.get_recommendations(test_content, request)

        print(f"📊 GOT {len(recommendations)} RECOMMENDATIONS:")
        print()

        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec.title}")
            print(f"   Score: {rec.score:.1f}")
            print(f"   Confidence: {rec.confidence:.3f}")
            print(f"   Technologies: {rec.technologies}")
            print(f"   Reason: {rec.reason}")
            print()

        # Check if we got Go-related content
        go_related = [r for r in recommendations if any('go' in tech.lower() for tech in r.technologies)]
        print(f"✅ Go-related recommendations: {len(go_related)}")
        print(f"❌ Non-Go recommendations: {len(recommendations) - len(go_related)}")

        if len(go_related) > 0:
            print("✅ SUCCESS: Recommendation system is working correctly!")
        else:
            print("❌ ISSUE: No Go-related content recommended")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_recommendations()

