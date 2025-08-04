#!/usr/bin/env python3
"""
Simple test for Phase 2 algorithms without cache
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_recommendation_engine import unified_engine

def test_simple_phase2():
    """Test Phase 2 algorithms directly"""
    print("🧪 Simple Phase 2 Test")
    print("=" * 40)
    
    # Clear all caches
    unified_engine.cache_manager.memory_cache.clear()
    
    # Test hybrid algorithm directly
    print("\n🔧 Testing Hybrid Algorithm Directly:")
    start_time = time.time()
    
    try:
        recommendations = unified_engine._hybrid_algorithm(
            user_id=1,
            request_data={
                'technologies': ['python', 'javascript'],
                'content_type': 'tutorial',
                'difficulty': 'intermediate'
            },
            limit=5
        )
        
        response_time = (time.time() - start_time) * 1000
        print(f"⏱️  Response Time: {response_time:.2f}ms")
        print(f"🎯 Recommendations: {len(recommendations)}")
        
        if recommendations:
            print(f"🏆 Top Recommendation:")
            top = recommendations[0]
            print(f"   Title: {top.title}")
            print(f"   Score: {top.score:.2f}/10")
            print(f"   Technologies: {', '.join(top.technologies[:3])}")
            print(f"   Reasoning: {top.reasoning[:100]}...")
        else:
            print("❌ No recommendations found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test semantic algorithm directly
    print("\n🔧 Testing Semantic Algorithm Directly:")
    start_time = time.time()
    
    try:
        recommendations = unified_engine._semantic_algorithm(
            user_id=1,
            request_data={
                'description': 'Learning Python programming and web development',
                'content_type': 'tutorial',
                'difficulty': 'beginner'
            }
        )
        
        response_time = (time.time() - start_time) * 1000
        print(f"⏱️  Response Time: {response_time:.2f}ms")
        print(f"🎯 Recommendations: {len(recommendations)}")
        
        if recommendations:
            print(f"🏆 Top Recommendation:")
            top = recommendations[0]
            print(f"   Title: {top.title}")
            print(f"   Score: {top.score:.2f}/10")
            print(f"   Technologies: {', '.join(top.technologies[:3])}")
            print(f"   Reasoning: {top.reasoning[:100]}...")
        else:
            print("❌ No recommendations found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_phase2() 