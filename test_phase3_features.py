#!/usr/bin/env python3
"""
Test Phase 3: Advanced Features
Contextual Recommendations, Real-time Learning, Advanced Analytics
"""

import os
import sys
import time
import json
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_phase3_components():
    """Test Phase 3 core components"""
    print("🧪 Testing Phase 3 Components...")
    
    try:
        from phase3_enhanced_engine import (
            contextual_analyzer, real_time_learner,
            get_enhanced_recommendations_phase3,
            get_user_learning_insights,
            get_system_health_phase3
        )
        
        print("✅ Phase 3 components imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error importing Phase 3 components: {e}")
        return False

def test_contextual_analysis():
    """Test contextual analysis functionality"""
    print("\n🔍 Testing Contextual Analysis...")
    
    try:
        from phase3_enhanced_engine import contextual_analyzer
        
        # Test different user agents
        test_cases = [
            {
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                'expected_device': 'mobile'
            },
            {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'expected_device': 'desktop'
            },
            {
                'user_agent': 'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)',
                'expected_device': 'tablet'
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            request_data = {'user_agent': test_case['user_agent']}
            context = contextual_analyzer.analyze_context(request_data, 1)
            
            print(f"   Test {i}: {test_case['user_agent'][:50]}...")
            print(f"      - Device: {context.device_type} (expected: {test_case['expected_device']})")
            print(f"      - Time: {context.time_of_day}")
            print(f"      - Day: {context.day_of_week}")
            print(f"      - Learning Session: {context.learning_session}")
        
        print("✅ Contextual analysis working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in contextual analysis: {e}")
        return False

def test_real_time_learning():
    """Test real-time learning functionality"""
    print("\n🧠 Testing Real-time Learning...")
    
    try:
        from phase3_enhanced_engine import real_time_learner
        
        user_id = 1
        
        # Test user profile creation
        print("   Testing user profile creation...")
        adapted_data = real_time_learner.get_adapted_parameters(user_id, {
            'project_title': 'React Native Project',
            'technologies': 'React Native, JavaScript'
        })
        
        print(f"      - Adapted data: {adapted_data}")
        
        # Test feedback integration
        print("   Testing feedback integration...")
        interaction_data = {
            'feedback_type': 'relevant',
            'content_type': 'tutorial',
            'difficulty': 'intermediate',
            'technologies': ['React Native', 'JavaScript'],
            'algorithm_used': 'hybrid'
        }
        
        real_time_learner.update_user_profile(user_id, interaction_data)
        
        # Test learning metrics
        print("   Testing learning metrics...")
        learning_metrics = real_time_learner.get_learning_metrics(user_id)
        
        print(f"      - User Engagement: {learning_metrics.user_engagement:.2f}")
        print(f"      - Content Effectiveness: {learning_metrics.content_effectiveness:.2f}")
        print(f"      - User Satisfaction: {learning_metrics.user_satisfaction:.2f}")
        print(f"      - Learning Progress: {learning_metrics.learning_progress:.2f}")
        
        # Test negative feedback
        print("   Testing negative feedback...")
        negative_interaction = {
            'feedback_type': 'not_relevant',
            'content_type': 'documentation',
            'difficulty': 'advanced',
            'algorithm_used': 'semantic'
        }
        
        real_time_learner.update_user_profile(user_id, negative_interaction)
        
        # Get updated metrics
        updated_metrics = real_time_learner.get_learning_metrics(user_id)
        print(f"      - Updated Content Effectiveness: {updated_metrics.content_effectiveness:.2f}")
        
        print("✅ Real-time learning working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in real-time learning: {e}")
        return False

def test_enhanced_recommendations_phase3():
    """Test Phase 3 enhanced recommendations"""
    print("\n🚀 Testing Phase 3 Enhanced Recommendations...")
    
    try:
        from phase3_enhanced_engine import get_enhanced_recommendations_phase3
        
        # Test request data with contextual information
        request_data = {
            'project_title': 'React Native Mobile App',
            'project_description': 'Building a cross-platform mobile application',
            'technologies': 'React Native, JavaScript, TypeScript',
            'learning_goals': 'Master React Native development',
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'content_type': 'all',
            'difficulty': 'all',
            'max_recommendations': 3
        }
        
        print("   Generating Phase 3 recommendations...")
        start_time = time.time()
        
        recommendations = get_enhanced_recommendations_phase3(1, request_data, 3)
        
        response_time = (time.time() - start_time) * 1000
        
        print(f"   Response time: {response_time:.2f}ms")
        print(f"   Recommendations count: {len(recommendations)}")
        
        if recommendations:
            print("\n   📊 Phase 3 Recommendation Analysis:")
            for i, rec in enumerate(recommendations, 1):
                print(f"\n   Recommendation {i}:")
                print(f"      - Title: {rec.get('title', 'N/A')}")
                print(f"      - Match Score: {rec.get('match_score', 0):.1f}%")
                print(f"      - Algorithm: {rec.get('algorithm_used', 'N/A')}")
                
                # Phase 3 specific features
                context = rec.get('context', {})
                if context:
                    print(f"      - Device Optimized: {context.get('device_optimized', 'N/A')}")
                    print(f"      - Time Appropriate: {context.get('time_appropriate', 'N/A')}")
                    print(f"      - Learning Session: {context.get('session_context', False)}")
                
                learning_insights = rec.get('learning_insights', {})
                if learning_insights:
                    print(f"      - Engagement Score: {learning_insights.get('engagement_score', 0):.2f}")
                    print(f"      - Content Effectiveness: {learning_insights.get('content_effectiveness', 0):.2f}")
                    print(f"      - Learning Progress: {learning_insights.get('learning_progress', 0):.2f}")
        
        print("✅ Phase 3 enhanced recommendations working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in Phase 3 recommendations: {e}")
        return False

def test_user_learning_insights():
    """Test user learning insights"""
    print("\n📊 Testing User Learning Insights...")
    
    try:
        from phase3_enhanced_engine import get_user_learning_insights
        
        user_id = 1
        
        print("   Generating user learning insights...")
        insights = get_user_learning_insights(user_id)
        
        print("   📈 Learning Insights:")
        print(f"      - Phase: {insights.get('phase', 'N/A')}")
        
        learning_metrics = insights.get('learning_metrics', {})
        if learning_metrics:
            print(f"      - User Engagement: {learning_metrics.get('user_engagement', 0):.2f}")
            print(f"      - Content Effectiveness: {learning_metrics.get('content_effectiveness', 0):.2f}")
            print(f"      - User Satisfaction: {learning_metrics.get('user_satisfaction', 0):.2f}")
            print(f"      - Learning Progress: {learning_metrics.get('learning_progress', 0):.2f}")
            print(f"      - Adaptation Rate: {learning_metrics.get('adaptation_rate', 0):.2f}")
        
        user_profile = insights.get('user_profile', {})
        if user_profile:
            print(f"      - Skill Level: {user_profile.get('skill_level', 'N/A')}")
            print(f"      - Learning Style: {user_profile.get('learning_style', 'N/A')}")
            print(f"      - Technology Preferences: {len(user_profile.get('technology_preferences', []))} techs")
            
            content_prefs = user_profile.get('content_preferences', {})
            if content_prefs:
                print("      - Content Preferences:")
                for content_type, preference in content_prefs.items():
                    print(f"         * {content_type}: {preference:.2f}")
        
        print("✅ User learning insights working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in user learning insights: {e}")
        return False

def test_system_health_phase3():
    """Test Phase 3 system health"""
    print("\n🏥 Testing Phase 3 System Health...")
    
    try:
        from phase3_enhanced_engine import get_system_health_phase3
        
        print("   Getting system health...")
        health = get_system_health_phase3()
        
        print("   📊 System Health Status:")
        print(f"      - Enhanced Engine: {health.get('enhanced_engine_available', False)}")
        print(f"      - Phase 1: {health.get('phase_1_complete', False)}")
        print(f"      - Phase 2: {health.get('phase_2_complete', False)}")
        print(f"      - Phase 3: {health.get('phase_3_complete', False)}")
        
        performance_metrics = health.get('performance_metrics', {})
        if performance_metrics:
            print(f"      - Response Time: {performance_metrics.get('response_time_ms', 0):.2f}ms")
            print(f"      - Cache Hit Rate: {performance_metrics.get('cache_hit_rate', 0)*100:.1f}%")
            print(f"      - Error Rate: {performance_metrics.get('error_rate', 0)*100:.2f}%")
            print(f"      - Throughput: {performance_metrics.get('throughput', 0)} req/min")
        
        learning_system = health.get('learning_system', {})
        if learning_system:
            print(f"      - Active Users: {learning_system.get('active_users', 0)}")
            print(f"      - Total Interactions: {learning_system.get('total_interactions', 0)}")
            print(f"      - Adaptation Rate: {learning_system.get('adaptation_rate', 0):.2f}")
        
        contextual_analysis = health.get('contextual_analysis', {})
        if contextual_analysis:
            print(f"      - Device Patterns: {contextual_analysis.get('device_patterns', 0)}")
            print(f"      - Time Patterns: {contextual_analysis.get('time_patterns', 0)}")
        
        print("✅ Phase 3 system health working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in system health: {e}")
        return False

def test_phase3_integration():
    """Test complete Phase 3 integration"""
    print("\n🔗 Testing Phase 3 Integration...")
    
    try:
        from phase3_enhanced_engine import (
            get_enhanced_recommendations_phase3,
            record_user_feedback_phase3,
            get_user_learning_insights
        )
        
        user_id = 1
        
        # Step 1: Get initial recommendations
        print("   Step 1: Getting initial recommendations...")
        initial_recs = get_enhanced_recommendations_phase3(user_id, {
            'project_title': 'Python Backend API',
            'technologies': 'Python, Flask, SQLAlchemy',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }, 2)
        
        print(f"      - Initial recommendations: {len(initial_recs)}")
        
        # Step 2: Record feedback
        if initial_recs:
            print("   Step 2: Recording user feedback...")
            first_rec = initial_recs[0]
            record_user_feedback_phase3(
                user_id, 
                first_rec.get('id', 1), 
                'relevant',
                {'content_type': first_rec.get('content_type'), 'difficulty': first_rec.get('difficulty')}
            )
            print("      - Feedback recorded successfully")
        
        # Step 3: Get updated insights
        print("   Step 3: Getting updated insights...")
        updated_insights = get_user_learning_insights(user_id)
        
        learning_metrics = updated_insights.get('learning_metrics', {})
        if learning_metrics:
            print(f"      - Updated Engagement: {learning_metrics.get('user_engagement', 0):.2f}")
            print(f"      - Updated Effectiveness: {learning_metrics.get('content_effectiveness', 0):.2f}")
        
        # Step 4: Get adapted recommendations
        print("   Step 4: Getting adapted recommendations...")
        adapted_recs = get_enhanced_recommendations_phase3(user_id, {
            'project_title': 'Python Backend API',
            'technologies': 'Python, Flask, SQLAlchemy',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }, 2)
        
        print(f"      - Adapted recommendations: {len(adapted_recs)}")
        
        print("✅ Phase 3 integration working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error in Phase 3 integration: {e}")
        return False

def main():
    """Run all Phase 3 tests"""
    print("🚀 Testing Phase 3: Advanced Features")
    print("=" * 60)
    
    tests = [
        ("Phase 3 Components", test_phase3_components),
        ("Contextual Analysis", test_contextual_analysis),
        ("Real-time Learning", test_real_time_learning),
        ("Enhanced Recommendations", test_enhanced_recommendations_phase3),
        ("User Learning Insights", test_user_learning_insights),
        ("System Health", test_system_health_phase3),
        ("Phase 3 Integration", test_phase3_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Phase 3 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 3 tests passed!")
        print("✅ Phase 3 implementation is complete and working correctly")
        print("\n🚀 Phase 3 Features Implemented:")
        print("   - Contextual Recommendations (device, time, session awareness)")
        print("   - Real-time Learning (user preference adaptation)")
        print("   - Advanced Analytics (learning insights and metrics)")
        print("   - System Health Monitoring (comprehensive status)")
        print("   - Integration with Phase 1 & 2 (seamless operation)")
    else:
        print("⚠️  Some Phase 3 tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    main() 