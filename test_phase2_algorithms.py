#!/usr/bin/env python3
"""
Test script for Phase 2: Advanced Algorithms & Intelligence
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_recommendation_engine import get_enhanced_recommendations, unified_engine

def test_phase2_algorithms():
    """Test all Phase 2 algorithms"""
    print("🧪 Testing Phase 2: Advanced Algorithms & Intelligence")
    print("=" * 60)
    
    # Clear cache to test fresh recommendations
    unified_engine.cache_manager.memory_cache.clear()
    
    test_cases = [
        {
            'name': 'Semantic Algorithm - Concept Focused',
            'request_data': {
                'algorithm': 'semantic',
                'description': 'Building a machine learning model for image classification using deep learning techniques with convolutional neural networks and transfer learning approaches',
                'content_type': 'tutorial',
                'difficulty': 'advanced'
            }
        },
        {
            'name': 'Content-Based Algorithm - Technology Focused',
            'request_data': {
                'algorithm': 'content_based',
                'technologies': ['react', 'typescript', 'node.js', 'express'],
                'content_type': 'tutorial',
                'difficulty': 'intermediate'
            }
        },
        {
            'name': 'Hybrid Algorithm - Project Specific',
            'request_data': {
                'algorithm': 'hybrid',
                'project_title': 'E-commerce Platform',
                'description': 'Building a full-stack e-commerce platform with React frontend, Node.js backend, and PostgreSQL database',
                'technologies': ['react', 'node.js', 'postgresql', 'express'],
                'content_type': 'project',
                'difficulty': 'intermediate'
            }
        },
        {
            'name': 'Auto-Select Algorithm - Technology Only',
            'request_data': {
                'technologies': ['python', 'django', 'postgresql'],
                'content_type': 'tutorial',
                'difficulty': 'beginner'
            }
        },
        {
            'name': 'Auto-Select Algorithm - Description Only',
            'request_data': {
                'description': 'Learning about microservices architecture, containerization with Docker, and orchestration with Kubernetes for scalable application deployment',
                'content_type': 'guide',
                'difficulty': 'advanced'
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Get recommendations
            recommendations = get_enhanced_recommendations(
                user_id=1, 
                request_data=test_case['request_data'],
                limit=5
            )
            
            response_time = (time.time() - start_time) * 1000
            
            print(f"⏱️  Response Time: {response_time:.2f}ms")
            print(f"📊 Algorithm Used: {test_case['request_data'].get('algorithm', 'auto-selected')}")
            print(f"🎯 Recommendations Found: {len(recommendations)}")
            
            # Display top recommendations
            for j, rec in enumerate(recommendations[:3], 1):
                print(f"\n  {j}. {rec.title}")
                print(f"     Score: {rec.score:.2f}/10")
                print(f"     Type: {rec.content_type}")
                print(f"     Difficulty: {rec.difficulty}")
                print(f"     Technologies: {', '.join(rec.technologies[:3])}")
                print(f"     Algorithm: {rec.algorithm_used}")
                print(f"     Confidence: {rec.confidence:.2f}")
                print(f"     Reasoning: {rec.reasoning[:100]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test diversity optimization
    print(f"\n🔍 Test 6: Diversity Optimization")
    print("-" * 50)
    
    try:
        # Get recommendations that should be diverse
        recommendations = get_enhanced_recommendations(
            user_id=1,
            request_data={
                'technologies': ['python', 'javascript', 'react'],
                'content_type': 'tutorial',
                'difficulty': 'intermediate'
            },
            limit=10
        )
        
        print(f"📊 Total Recommendations: {len(recommendations)}")
        
        # Check for diversity in technologies
        all_technologies = []
        for rec in recommendations:
            all_technologies.extend(rec.technologies)
        
        unique_technologies = set(all_technologies)
        print(f"🔧 Unique Technologies: {len(unique_technologies)}")
        print(f"🔧 Technology Diversity: {', '.join(list(unique_technologies)[:10])}")
        
        # Check for diversity in content types
        content_types = [rec.type for rec in recommendations]
        unique_types = set(content_types)
        print(f"📝 Content Type Diversity: {', '.join(unique_types)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test feedback integration
    print(f"\n🔍 Test 7: Feedback Integration")
    print("-" * 50)
    
    try:
        # Simulate user feedback
        if recommendations:
            first_rec = recommendations[0]
            unified_engine.integrate_user_feedback(
                user_id=1,
                recommendation_id=first_rec.id,
                feedback_type='relevant',
                feedback_data={'rating': 5, 'comment': 'Very helpful!'}
            )
            print(f"✅ Feedback integrated for recommendation: {first_rec.title}")
        else:
            print("⚠️  No recommendations to test feedback with")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Display performance metrics
    print(f"\n📊 Performance Metrics")
    print("-" * 50)
    
    try:
        metrics = unified_engine.get_performance_metrics()
        print(f"⏱️  Average Response Time: {metrics.response_time_ms:.2f}ms")
        print(f"🎯 Cache Hit Rate: {metrics.cache_hit_rate:.1%}")
        print(f"📈 Throughput: {metrics.throughput} requests/min")
        print(f"❌ Error Rate: {metrics.error_rate:.1%}")
        
        cache_stats = unified_engine.get_cache_stats()
        print(f"💾 Memory Cache Hits: {cache_stats.get('memory_hits', 0)}")
        print(f"💾 Memory Cache Misses: {cache_stats.get('memory_misses', 0)}")
        if 'redis_hits' in cache_stats:
            print(f"🔴 Redis Cache Hits: {cache_stats['redis_hits']}")
            print(f"🔴 Redis Cache Misses: {cache_stats['redis_misses']}")
            
    except Exception as e:
        print(f"❌ Error getting metrics: {e}")

def test_algorithm_comparison():
    """Compare different algorithms on the same request"""
    print(f"\n🔍 Test 8: Algorithm Comparison")
    print("-" * 50)
    
    base_request = {
        'technologies': ['react', 'typescript'],
        'content_type': 'tutorial',
        'difficulty': 'intermediate'
    }
    
    algorithms = ['hybrid', 'semantic', 'content_based']
    
    for algorithm in algorithms:
        print(f"\n🔧 Testing {algorithm.upper()} Algorithm:")
        
        request_data = base_request.copy()
        request_data['algorithm'] = algorithm
        
        start_time = time.time()
        
        try:
            recommendations = get_enhanced_recommendations(
                user_id=1,
                request_data=request_data,
                limit=3
            )
            
            response_time = (time.time() - start_time) * 1000
            
            print(f"  ⏱️  Response Time: {response_time:.2f}ms")
            print(f"  🎯 Recommendations: {len(recommendations)}")
            
            if recommendations:
                avg_score = sum(rec.score for rec in recommendations) / len(recommendations)
                print(f"  📊 Average Score: {avg_score:.2f}/10")
                
                # Show top recommendation
                top_rec = recommendations[0]
                print(f"  🏆 Top: {top_rec.title}")
                print(f"     Score: {top_rec.score:.2f}, Confidence: {top_rec.confidence:.2f}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_phase2_algorithms()
    test_algorithm_comparison()
    print(f"\n🎉 Phase 2 Testing Complete!") 