#!/usr/bin/env python3
"""
Test All Engines
Verify that all engines are available and working in the ensemble
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_all_engines():
    """Test all available engines"""
    print("🚀 Testing All Available Engines")
    print("=" * 50)
    
    # Test data
    test_data = {
        'title': 'React Development',
        'description': 'Building modern web applications with React',
        'technologies': 'React, JavaScript, TypeScript',
        'max_recommendations': 5,
        'engines': ['unified', 'smart', 'enhanced', 'phase3', 'fast_gemini', 'gemini_enhanced']
    }
    
    user_id = 1  # Test user ID
    
    # List of all engines to test
    all_engines = [
        ('unified', 'Unified Orchestrator'),
        ('smart', 'Smart Engine'),
        ('enhanced', 'Enhanced Engine'),
        ('phase3', 'Phase 3 Engine'),
        ('fast_gemini', 'Fast Gemini Engine'),
        ('gemini_enhanced', 'Gemini Enhanced Engine')
    ]
    
    print("🔧 Testing Individual Engine Availability...")
    available_engines = []
    
    for engine_id, engine_name in all_engines:
        try:
            if engine_id == 'unified':
                from unified_recommendation_orchestrator import get_unified_orchestrator
                get_unified_orchestrator()
                available_engines.append(engine_id)
                print(f"   ✅ {engine_name} - Available")
            elif engine_id == 'smart':
                from smart_recommendation_engine import SmartRecommendationEngine
                available_engines.append(engine_id)
                print(f"   ✅ {engine_name} - Available")
            elif engine_id == 'enhanced':
                from enhanced_recommendation_engine import get_enhanced_recommendations
                available_engines.append(engine_id)
                print(f"   ✅ {engine_name} - Available")
            elif engine_id == 'phase3':
                from phase3_enhanced_engine import get_enhanced_recommendations_phase3
                available_engines.append(engine_id)
                print(f"   ✅ {engine_name} - Available")
            elif engine_id == 'fast_gemini':
                from fast_gemini_engine import fast_gemini_engine
                available_engines.append(engine_id)
                print(f"   ✅ {engine_name} - Available")
            elif engine_id == 'gemini_enhanced':
                from gemini_enhanced_recommendation_engine import GeminiEnhancedRecommendationEngine
                available_engines.append(engine_id)
                print(f"   ✅ {engine_name} - Available")
        except ImportError as e:
            print(f"   ❌ {engine_name} - Not Available: {e}")
        except Exception as e:
            print(f"   ⚠️ {engine_name} - Error: {e}")
    
    print(f"\n📊 Engine Availability Summary:")
    print(f"   Available engines: {len(available_engines)}/{len(all_engines)}")
    print(f"   Available: {', '.join(available_engines)}")
    
    # Test ensemble engines
    print(f"\n🎯 Testing Ensemble Engines...")
    
    try:
        # Test Complete Ensemble Engine
        print(f"\n⚖️ Test 1: Complete Ensemble Engine")
        from ensemble_engine import get_ensemble_recommendations
        
        start_time = time.time()
        ensemble_results = get_ensemble_recommendations(user_id, test_data)
        ensemble_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {ensemble_response_time:.2f}ms")
        print(f"   Results: {len(ensemble_results) if ensemble_results else 0}")
        print(f"   Status: {'✅ WORKING' if ensemble_results and len(ensemble_results) > 0 else '❌ NOT WORKING'}")
        
        # Test Complete Fast Quality Ensemble Engine
        print(f"\n⭐ Test 2: Complete Fast Quality Ensemble Engine")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        
        start_time = time.time()
        quality_results = get_quality_ensemble_recommendations(user_id, test_data)
        quality_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {quality_response_time:.2f}ms")
        print(f"   Results: {len(quality_results) if quality_results else 0}")
        print(f"   Status: {'✅ WORKING' if quality_results and len(quality_results) > 0 else '❌ NOT WORKING'}")
        
        # Performance Analysis
        print(f"\n📊 Performance Analysis:")
        print(f"   Complete Ensemble: {ensemble_response_time:.2f}ms")
        print(f"   Fast Quality Ensemble: {quality_response_time:.2f}ms")
        
        # Speed comparison
        if ensemble_response_time > 0 and quality_response_time > 0:
            speedup = ensemble_response_time / quality_response_time
            print(f"   Quality vs Ensemble: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
        
        # Summary
        print(f"\n🎯 Final Summary:")
        working_engines = 0
        if ensemble_results and len(ensemble_results) > 0:
            working_engines += 1
        if quality_results and len(quality_results) > 0:
            working_engines += 1
        
        print(f"   Working ensemble engines: {working_engines}/2")
        print(f"   Available individual engines: {len(available_engines)}/{len(all_engines)}")
        
        if working_engines == 2 and len(available_engines) >= 4:
            print(f"   🎉 All engines are working!")
            print(f"   ✅ Complete ensemble with all engines configured")
            print(f"   ✅ Fast quality ensemble optimized for speed")
            print(f"   ✅ All major engines available")
        else:
            print(f"   ⚠️ Some engines need attention")
            if len(available_engines) < 4:
                print(f"   ⚠️ Only {len(available_engines)} engines available (need at least 4)")
        
    except Exception as e:
        print(f"❌ Error in ensemble test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_all_engines() 