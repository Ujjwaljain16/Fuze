#!/usr/bin/env python3
"""
Test Ensemble Engine Fix
Quick test to verify the ensemble engines are working after fixes
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ensemble_fix():
    """Quick test to verify ensemble engines work after fixes"""
    print("🔧 Testing Ensemble Engine Fixes")
    print("=" * 40)
    
    # Test data
    test_data = {
        'title': 'React Development',
        'description': 'Building modern web applications with React',
        'technologies': 'React, JavaScript, TypeScript',
        'max_recommendations': 5,
        'engines': ['unified', 'smart', 'enhanced']
    }
    
    user_id = 1  # Test user ID
    
    try:
        # Test Fast Ensemble Engine
        print("\n🔥 Testing Fast Ensemble Engine...")
        from fast_ensemble_engine import get_fast_ensemble_recommendations
        
        start_time = time.time()
        fast_results = get_fast_ensemble_recommendations(user_id, test_data)
        fast_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {fast_response_time:.2f}ms")
        print(f"   Results: {len(fast_results) if fast_results else 0}")
        print(f"   Status: {'✅ WORKING' if fast_results and len(fast_results) > 0 else '❌ NOT WORKING'}")
        
        # Test Optimized Ensemble Engine
        print("\n⚖️ Testing Optimized Ensemble Engine...")
        from ensemble_engine import get_ensemble_recommendations
        
        start_time = time.time()
        optimized_results = get_ensemble_recommendations(user_id, test_data)
        optimized_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {optimized_response_time:.2f}ms")
        print(f"   Results: {len(optimized_results) if optimized_results else 0}")
        print(f"   Status: {'✅ WORKING' if optimized_results and len(optimized_results) > 0 else '❌ NOT WORKING'}")
        
        # Test Quality Ensemble Engine
        print("\n⭐ Testing Quality Ensemble Engine...")
        from quality_ensemble_engine import get_quality_ensemble_recommendations
        
        start_time = time.time()
        quality_results = get_quality_ensemble_recommendations(user_id, test_data)
        quality_response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {quality_response_time:.2f}ms")
        print(f"   Results: {len(quality_results) if quality_results else 0}")
        print(f"   Status: {'✅ WORKING' if quality_results and len(quality_results) > 0 else '❌ NOT WORKING'}")
        
        # Summary
        print(f"\n📊 Summary:")
        working_engines = 0
        if fast_results and len(fast_results) > 0:
            working_engines += 1
        if optimized_results and len(optimized_results) > 0:
            working_engines += 1
        if quality_results and len(quality_results) > 0:
            working_engines += 1
        
        print(f"   Working engines: {working_engines}/3")
        
        if working_engines == 3:
            print(f"   🎉 All engines are working!")
        elif working_engines > 0:
            print(f"   ⚠️ Some engines are working")
        else:
            print(f"   ❌ No engines are working")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_fix() 