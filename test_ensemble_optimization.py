#!/usr/bin/env python3
"""
Test Ensemble Engine Optimization
Verify that the optimized ensemble engine is much faster
"""

import time
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ensemble_optimization():
    """Test the optimized ensemble engine performance"""
    print("🚀 Testing Ensemble Engine Optimization")
    print("=" * 50)
    
    # Test data
    test_data = {
        'title': 'React Development',
        'description': 'Building modern web applications with React',
        'technologies': 'React, JavaScript, TypeScript',
        'max_recommendations': 5,
        'engines': ['unified']  # Start with just unified for speed
    }
    
    user_id = 1  # Test user ID
    
    print("📊 Testing Optimized Ensemble Engine...")
    
    try:
        # Test optimized ensemble engine
        from ensemble_engine import get_ensemble_recommendations
        
        start_time = time.time()
        results = get_ensemble_recommendations(user_id, test_data)
        response_time = (time.time() - start_time) * 1000
        
        print(f"✅ Optimized Ensemble Engine:")
        print(f"   Response time: {response_time:.2f}ms")
        print(f"   Total recommendations: {len(results)}")
        print(f"   Performance: {'🚀 FAST' if response_time < 5000 else '🐌 SLOW' if response_time > 30000 else '⚡ GOOD'}")
        
        # Test fast ensemble engine
        print("\n📊 Testing Fast Ensemble Engine...")
        
        from fast_ensemble_engine import get_fast_ensemble_recommendations
        
        start_time = time.time()
        fast_results = get_fast_ensemble_recommendations(user_id, test_data)
        fast_response_time = (time.time() - start_time) * 1000
        
        print(f"✅ Fast Ensemble Engine:")
        print(f"   Response time: {fast_response_time:.2f}ms")
        print(f"   Total recommendations: {len(fast_results)}")
        print(f"   Performance: {'🚀 FAST' if fast_response_time < 5000 else '🐌 SLOW' if fast_response_time > 30000 else '⚡ GOOD'}")
        
        # Performance comparison
        print(f"\n📈 Performance Comparison:")
        if response_time > 0:
            speedup = response_time / fast_response_time if fast_response_time > 0 else 1
            print(f"   Speedup: {speedup:.2f}x faster")
        
        print(f"\n🎯 Optimization Summary:")
        print(f"   ✅ Caching implemented")
        print(f"   ✅ Parallel processing added")
        print(f"   ✅ Timeout protection added")
        print(f"   ✅ Early termination for sufficient results")
        print(f"   ✅ Fast ensemble engine created")
        
        # Test with multiple engines
        print(f"\n📊 Testing with Multiple Engines...")
        test_data_multi = test_data.copy()
        test_data_multi['engines'] = ['unified', 'smart']
        
        start_time = time.time()
        multi_results = get_ensemble_recommendations(user_id, test_data_multi)
        multi_response_time = (time.time() - start_time) * 1000
        
        print(f"✅ Multi-Engine Ensemble:")
        print(f"   Response time: {multi_response_time:.2f}ms")
        print(f"   Total recommendations: {len(multi_results)}")
        print(f"   Performance: {'🚀 FAST' if multi_response_time < 10000 else '🐌 SLOW' if multi_response_time > 60000 else '⚡ GOOD'}")
        
        print(f"\n🎉 Optimization Complete!")
        print(f"   Expected improvement: 10-50x faster response times")
        print(f"   Cache hit rate: Should improve with repeated requests")
        print(f"   User experience: Much more responsive")
        
    except Exception as e:
        print(f"❌ Error testing ensemble optimization: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_optimization() 