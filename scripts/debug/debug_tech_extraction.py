#!/usr/bin/env python3
"""
Debug script for technology extraction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tech_extraction():
    """Test technology extraction with different inputs"""
    print("🔍 Debugging Technology Extraction")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'name': 'Java DSA Project',
            'text': 'DSA visualiser a visualizer for data structure and algorithms that make it easier to understand the complexity easier just copy paste yr code and get a dynamic visualization of that with a detailed dry run for now available in java language only java instrumentation byte buddy ast jvm'
        },
        {
            'name': 'React Native Project',
            'text': 'Building a cross-platform mobile application with React Native and TypeScript using Firebase for backend services'
        },
        {
            'name': 'Python Backend',
            'text': 'Building a RESTful API with Django and PostgreSQL using Redis for caching'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        print("-" * 30)
        print(f"Input text: {test_case['text'][:100]}...")
        
        # Test advanced tech detector
        try:
            from advanced_tech_detection import advanced_tech_detector
            techs = advanced_tech_detector.extract_technologies(test_case['text'])
            print(f"✅ Advanced Tech Detector: {len(techs)} technologies found")
            for tech in techs:
                print(f"   - {tech['category']}: {tech['keyword']} (confidence: {tech['confidence']:.2f})")
        except Exception as e:
            print(f"❌ Advanced Tech Detector failed: {e}")
        
        # Test unified engine tech extraction
        try:
            from unified_recommendation_engine import UnifiedRecommendationEngine
            engine = UnifiedRecommendationEngine()
            techs = engine._extract_technologies(test_case['text'])
            print(f"✅ Unified Engine Tech Extraction: {len(techs)} technologies found")
            for tech in techs:
                if isinstance(tech, dict):
                    print(f"   - {tech.get('category', 'unknown')}: {tech.get('keyword', 'unknown')}")
                else:
                    print(f"   - {tech}")
        except Exception as e:
            print(f"❌ Unified Engine Tech Extraction failed: {e}")
        
        # Test basic regex extraction
        try:
            import re
            basic_techs = []
            tech_keywords = ['java', 'jvm', 'byte buddy', 'ast', 'react native', 'typescript', 'firebase', 'python', 'django', 'postgresql', 'redis']
            for keyword in tech_keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', test_case['text'].lower()):
                    basic_techs.append(keyword)
            print(f"✅ Basic Regex Extraction: {len(basic_techs)} technologies found")
            print(f"   - {', '.join(basic_techs)}")
        except Exception as e:
            print(f"❌ Basic Regex Extraction failed: {e}")

if __name__ == "__main__":
    test_tech_extraction() 