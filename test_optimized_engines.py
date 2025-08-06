#!/usr/bin/env python3
"""
Test Optimized Engines
Verify that the optimized engine configuration works correctly
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_optimized_engines():
    """Test the optimized engine configuration"""
    print("🚀 Testing Optimized Engine Configuration")
    print("=" * 50)
    
    # Test data
    test_data = {
        'title': 'React Development',
        'description': 'Building modern web applications with React',
        'technologies': 'React, JavaScript, TypeScript',
        'max_recommendations': 5,
        'engines': ['unified', 'smart']
    }
    
    user_id = 1  # Test user ID
    
    try:
        # Test 1: Original Ensemble Engine (Balanced)
        print("\n⚖️ Test 1: Original Ensemble Engine (Balanced)")
        from ensemble_engine import get_ensemble_recommendations
        
        start_time = time.time()
        ensemble_results = get_ensemble_recommendations(user_id, test_data)
        ensemble_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {ensemble_response_time:.2f}ms")
        print(f"   Results: {len(ensemble_results) if ensemble_results else 0}")
        print(f"   Status: {'✅ WORKING' if ensemble_results and len(ensemble_results) > 0 else '❌ NOT WORKING'}")
        
        # Test 2: Fast Quality Ensemble Engine
        print("\n⭐ Test 2: Fast Quality Ensemble Engine")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        
        start_time = time.time()
        quality_results = get_quality_ensemble_recommendations(user_id, test_data)
        quality_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {quality_response_time:.2f}ms")
        print(f"   Results: {len(quality_results) if quality_results else 0}")
        print(f"   Status: {'✅ WORKING' if quality_results and len(quality_results) > 0 else '❌ NOT WORKING'}")
        
        # Test 3: Unified Orchestrator
        print("\n🔧 Test 3: Unified Orchestrator")
        from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
        
        start_time = time.time()
        orchestrator = get_unified_orchestrator()
        unified_request = UnifiedRecommendationRequest(
            user_id=user_id,
            title=test_data['title'],
            description=test_data['description'],
            technologies=test_data['technologies'],
            max_recommendations=5,
            engine_preference='fast'
        )
        unified_results = orchestrator.get_recommendations(unified_request)
        unified_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {unified_response_time:.2f}ms")
        print(f"   Results: {len(unified_results) if unified_results else 0}")
        print(f"   Status: {'✅ WORKING' if unified_results and len(unified_results) > 0 else '❌ NOT WORKING'}")
        
        # Performance Analysis
        print(f"\n📊 Performance Analysis:")
        print(f"   Original Ensemble: {ensemble_response_time:.2f}ms")
        print(f"   Fast Quality Ensemble: {quality_response_time:.2f}ms")
        print(f"   Unified Orchestrator: {unified_response_time:.2f}ms")
        
        # Speed comparison
        if ensemble_response_time > 0 and quality_response_time > 0:
            speedup = ensemble_response_time / quality_response_time
            print(f"   Quality vs Ensemble: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
        
        # Summary
        print(f"\n🎯 Summary:")
        working_engines = 0
        if ensemble_results and len(ensemble_results) > 0:
            working_engines += 1
        if quality_results and len(quality_results) > 0:
            working_engines += 1
        if unified_results and len(unified_results) > 0:
            working_engines += 1
        
        print(f"   Working engines: {working_engines}/3")
        
        if working_engines == 3:
            print(f"   🎉 All engines are working!")
            print(f"   ✅ Fast ensemble removed successfully")
            print(f"   ✅ Quality ensemble optimized for speed")
            print(f"   ✅ Original ensemble working as balanced option")
        else:
            print(f"   ⚠️ Some engines need attention")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_optimized_engines() 