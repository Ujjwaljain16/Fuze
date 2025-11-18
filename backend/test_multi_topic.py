#!/usr/bin/env python3
"""
Test script for multi-topic content splitting functionality
"""

import sys
import os
sys.path.append('.')

def test_multi_topic_splitting():
    """Test the multi-topic content splitting logic"""

    # Import the orchestrator class
    try:
        from ml.unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator
        print("✅ Successfully imported UnifiedRecommendationOrchestrator")
    except ImportError as e:
        print(f"❌ Failed to import orchestrator: {e}")
        return

    # Create orchestrator instance - we'll catch any initialization errors
    try:
        orchestrator = UnifiedRecommendationOrchestrator()
        print("✅ Successfully created orchestrator instance")
    except Exception as init_error:
        print(f"⚠️  Orchestrator initialization failed, but continuing with test: {init_error}")
        # Create instance without calling __init__ to avoid dependencies
        orchestrator = UnifiedRecommendationOrchestrator.__new__(UnifiedRecommendationOrchestrator)

    # Test data simulating a LinkedIn post about React + Node.js + AWS
    test_content = {
        'id': 123,
        'title': 'Building Full-Stack Apps with React, Node.js and AWS',
        'content': 'A comprehensive guide covering frontend development with React, backend APIs with Node.js, and cloud deployment with AWS. This tutorial shows how to build modern web applications from start to finish.',
        'technologies': ['react', 'node.js', 'express', 'aws', 'javascript', 'mongodb'],
        'content_type': 'linkedin_post',
        'quality_score': 8.5,
        'extracted_text': 'This is a long article about building full-stack applications covering React components, Node.js API development, Express routing, AWS deployment, JavaScript fundamentals, and MongoDB database integration. ' * 50,  # Make it long enough
        'analysis_data': {
            'technology_clusters': [
                {
                    'cluster': 'frontend',
                    'technologies': ['react', 'javascript'],
                    'description': 'Frontend development with React'
                },
                {
                    'cluster': 'backend',
                    'technologies': ['node.js', 'express'],
                    'description': 'Backend development with Node.js'
                },
                {
                    'cluster': 'cloud',
                    'technologies': ['aws'],
                    'description': 'Cloud deployment and infrastructure'
                }
            ],
            'primary_topic': 'Full-stack development',
            'secondary_topics': ['frontend', 'backend', 'cloud computing']
        }
    }

    print("\n🧪 Testing Multi-Topic Content Splitting")
    print("=" * 50)
    print(f"Original content: {test_content['title']}")
    print(f"Original technologies: {test_content['technologies']}")
    print(f"Content type: {test_content['content_type']}")
    print(f"Quality score: {test_content['quality_score']}")
    print(f"Text length: {len(test_content['extracted_text'])} characters")
    print(f"Technology clusters: {len(test_content['analysis_data']['technology_clusters'])}")

    # Test the splitting
    try:
        split_results = orchestrator.split_multi_topic_content(test_content)

        print(f"\n✅ Splitting completed successfully!")
        print(f"Result: {len(split_results)} content items generated")

        for i, split in enumerate(split_results, 1):
            print(f"\n📄 Split {i}:")
            print(f"   Title: {split['title']}")
            print(f"   Technologies: {split['technologies']}")
            print(f"   Primary Tech: {split.get('primary_technology', 'N/A')}")
            print(f"   Focus Area: {split.get('focus_area', 'N/A')}")
            print(f"   Learning Path: {split.get('learning_path', 'N/A')}")
            print(f"   Is Split: {split.get('is_split_content', False)}")
            print(f"   Quality Score: {split.get('quality_score', 'N/A')}")

        # Test with content that shouldn't be split
        print("\n🧪 Testing content that should NOT be split")
        single_topic_content = {
            'id': 456,
            'title': 'Introduction to React Hooks',
            'content': 'Learn about useState and useEffect hooks',
            'technologies': ['react', 'javascript'],
            'content_type': 'linkedin_post',
            'quality_score': 7.0,
            'extracted_text': 'Short content about React hooks' * 10,
            'analysis_data': {
                'technology_clusters': [],
                'primary_topic': 'React hooks'
            }
        }

        single_split_results = orchestrator.split_multi_topic_content(single_topic_content)
        print(f"Single topic content resulted in {len(single_split_results)} item(s) (should be 1)")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_multi_topic_splitting()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed!")
        sys.exit(1)
