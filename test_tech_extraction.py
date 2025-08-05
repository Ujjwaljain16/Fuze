#!/usr/bin/env python3
"""
Simple test for technology extraction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tech_extraction():
    """Test technology extraction directly"""
    print("🔍 Testing Technology Extraction")
    print("=" * 50)
    
    # Test the advanced tech detector directly
    try:
        from advanced_tech_detection import advanced_tech_detector
        
        test_text = "DSA visualiser a visualizer for data structure and algorithms that make it easier to understand the complexity easier just copy paste yr code and get a dynamic visualization of that with a detailed dry run for now available in java language only java instrumentation byte buddy ast jvm"
        
        print(f"📋 Test text: {test_text[:100]}...")
        
        # Test advanced tech detector
        techs = advanced_tech_detector.extract_technologies(test_text)
        print(f"✅ Advanced Tech Detector: {len(techs)} technologies found")
        for tech in techs:
            print(f"   - {tech['category']}: {tech['keyword']} (confidence: {tech['confidence']:.2f})")
        
        # Test unified engine tech extraction
        from unified_recommendation_engine import UnifiedRecommendationEngine
        engine = UnifiedRecommendationEngine()
        techs = engine._extract_technologies(test_text)
        print(f"✅ Unified Engine Tech Extraction: {len(techs)} technologies found")
        for tech in techs:
            if isinstance(tech, dict):
                print(f"   - {tech.get('category', 'unknown')}: {tech.get('keyword', 'unknown')}")
            else:
                print(f"   - {tech}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tech_extraction() 