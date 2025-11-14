#!/usr/bin/env python3
"""
Test script for Intent Analysis Engine
Demonstrates how the system analyzes user intent and provides better recommendations
"""

import os
import sys
import json
from datetime import datetime
import time # Added for enhanced_recommendations_with_intent

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from intent_analysis_engine import analyze_user_intent, UserIntent
from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest

def test_intent_analysis():
    """Test intent analysis with various user inputs"""
    
    test_cases = [
        {
            "title": "Learn React Basics",
            "description": "I'm a beginner and want to learn React fundamentals",
            "technologies": "react, javascript, html, css",
            "expected_intent": "beginner learning React"
        },
        {
            "title": "Build Mobile App",
            "description": "Need to create a mobile app for my startup, urgent deadline",
            "technologies": "react native, firebase, javascript",
            "expected_intent": "urgent mobile app development"
        },
        {
            "title": "API Development",
            "description": "Building a REST API for my web application",
            "technologies": "node.js, express, mongodb, postgresql",
            "expected_intent": "API development with Node.js"
        },
        {
            "title": "Data Science Project",
            "description": "Advanced machine learning project for data analysis",
            "technologies": "python, tensorflow, pandas, numpy",
            "expected_intent": "advanced ML data analysis"
        },
        {
            "title": "Quick Tutorial",
            "description": "Need a quick tutorial on Docker deployment",
            "technologies": "docker, aws, deployment",
            "expected_intent": "quick Docker tutorial"
        }
    ]
    
    print("🧠 Testing Intent Analysis Engine")
    print("=" * 50)
    
    with app.app_context():
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test Case {i}: {test_case['title']}")
            print("-" * 30)
            
            # Combine user input
            user_input = f"{test_case['title']} {test_case['description']} {test_case['technologies']}"
            
            # Analyze intent
            intent = analyze_user_intent(user_input)
            
            # Display results
            print(f"Input: {user_input[:100]}...")
            print(f"Primary Goal: {intent.primary_goal}")
            print(f"Learning Stage: {intent.learning_stage}")
            print(f"Project Type: {intent.project_type}")
            print(f"Urgency Level: {intent.urgency_level}")
            print(f"Technologies: {intent.specific_technologies}")
            print(f"Complexity: {intent.complexity_preference}")
            print(f"Time Constraint: {intent.time_constraint}")
            print(f"Focus Areas: {intent.focus_areas}")
            print(f"Context Hash: {intent.context_hash[:16]}...")

def test_recommendations_with_intent():
    """Test recommendations with intent analysis"""
    
    print("\n\n🎯 Testing Recommendations with Intent Analysis")
    print("=" * 50)
    
    with app.app_context():
        # Test user ID (you may need to adjust this)
        test_user_id = 1
        
        test_requests = [
            {
                "title": "Learn React Basics",
                "description": "I'm a beginner and want to learn React fundamentals",
                "technologies": "react, javascript, html, css",
                "max_recommendations": 5
            },
            {
                "title": "Build Mobile App",
                "description": "Need to create a mobile app for my startup, urgent deadline",
                "technologies": "react native, firebase, javascript",
                "max_recommendations": 5
            }
        ]
        
        orchestrator = get_unified_orchestrator()
        
        for i, request_data in enumerate(test_requests, 1):
            print(f"\n🔍 Test Request {i}: {request_data['title']}")
            print("-" * 40)
            
            # Create request
            request = UnifiedRecommendationRequest(
                user_id=test_user_id,
                title=request_data['title'],
                description=request_data['description'],
                technologies=request_data['technologies'],
                max_recommendations=request_data['max_recommendations']
            )
            
            # Get recommendations with intent analysis
            recommendations = orchestrator.get_recommendations(request)
            
            print(f"Found {len(recommendations)} recommendations:")
            for j, rec in enumerate(recommendations[:3], 1):  # Show top 3
                print(f"  {j}. {rec.title}")
                print(f"     Score: {rec.score:.2f} | Engine: {rec.engine_used}")
                print(f"     Reason: {rec.reason[:100]}...")
                print()

def test_caching_behavior():
    """Test caching behavior of intent analysis"""
    
    print("\n\n💾 Testing Intent Analysis Caching")
    print("=" * 40)
    
    with app.app_context():
        # Same input multiple times
        user_input = "Learn React basics for beginners"
        
        print("First analysis (should be fresh):")
        start_time = datetime.now()
        intent1 = analyze_user_intent(user_input)
        time1 = (datetime.now() - start_time).total_seconds()
        print(f"Time: {time1:.3f}s | Hash: {intent1.context_hash[:16]}...")
        
        print("\nSecond analysis (should be cached):")
        start_time = datetime.now()
        intent2 = analyze_user_intent(user_input)
        time2 = (datetime.now() - start_time).total_seconds()
        print(f"Time: {time2:.3f}s | Hash: {intent2.context_hash[:16]}...")
        
        print(f"\nSpeed improvement: {time1/time2:.1f}x faster")
        print(f"Same result: {intent1.context_hash == intent2.context_hash}")

def test_enhanced_recommendations_with_intent():
    """Test enhanced recommendations with intent analysis using the orchestrator"""
    
    print("\n\n🚀 Testing Enhanced Recommendations with Intent Analysis")
    print("=" * 60)
    
    with app.app_context():
        # Test user ID (you may need to adjust this)
        test_user_id = 1
        
        test_requests = [
            {
                "title": "Learn React Basics",
                "description": "I'm a beginner and want to learn React fundamentals",
                "technologies": "react, javascript, html, css",
                "max_recommendations": 5,
                "engine_preference": "context"
            },
            {
                "title": "Build Mobile App",
                "description": "Need to create a mobile app for my startup, urgent deadline",
                "technologies": "react native, firebase, javascript",
                "max_recommendations": 5,
                "engine_preference": "context"
            },
            {
                "title": "API Development",
                "description": "Building a REST API for my web application",
                "technologies": "node.js, express, mongodb, postgresql",
                "max_recommendations": 5,
                "engine_preference": "context"
            },
            {
                "title": "Data Science Project",
                "description": "Advanced machine learning project for data analysis",
                "technologies": "python, tensorflow, pandas, numpy",
                "max_recommendations": 5,
                "engine_preference": "context"
            },
            {
                "title": "Quick Tutorial",
                "description": "Need a quick tutorial on Docker deployment",
                "technologies": "docker, aws, deployment",
                "max_recommendations": 5,
                "engine_preference": "context"
            }
        ]
        
        for i, test_request in enumerate(test_requests, 1):
            print(f"\n📝 Test Request {i}: {test_request['title']}")
            print("-" * 40)
            
            try:
                # Test using the unified orchestrator
                from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
                
                orchestrator = get_unified_orchestrator()
                if not orchestrator:
                    print("❌ Orchestrator not available")
                    continue
                
                # Create request
                request = UnifiedRecommendationRequest(
                    user_id=test_user_id,
                    title=test_request['title'],
                    description=test_request['description'],
                    technologies=test_request['technologies'],
                    user_interests="",
                    project_id=None,
                    max_recommendations=test_request['max_recommendations'],
                    engine_preference=test_request['engine_preference']
                )
                
                # Get recommendations
                start_time = time.time()
                recommendations = orchestrator.get_recommendations(request)
                response_time = (time.time() - start_time) * 1000
                
                print(f"✅ Recommendations generated in {response_time:.2f}ms")
                print(f"📊 Total recommendations: {len(recommendations)}")
                
                if recommendations:
                    print(f"🏆 Top recommendation: {recommendations[0].title[:50]}...")
                    print(f"📈 Score: {recommendations[0].score:.1f}")
                    print(f"🎯 Engine used: {recommendations[0].engine_used}")
                    print(f"💡 Reason: {recommendations[0].reason[:100]}...")
                    
                    # Show intent analysis details
                    if hasattr(request, 'intent_analysis') and request.intent_analysis:
                        intent = request.intent_analysis
                        print(f"🧠 Intent Analysis:")
                        print(f"   - Primary Goal: {intent.get('primary_goal', 'N/A')}")
                        print(f"   - Learning Stage: {intent.get('learning_stage', 'N/A')}")
                        print(f"   - Project Type: {intent.get('project_type', 'N/A')}")
                        print(f"   - Urgency: {intent.get('urgency_level', 'N/A')}")
                        print(f"   - Focus Areas: {intent.get('focus_areas', [])}")
                else:
                    print("⚠️ No recommendations generated")
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()

def test_intent_analysis_performance():
    """Test intent analysis performance and caching"""
    
    print("\n\n⚡ Testing Intent Analysis Performance and Caching")
    print("=" * 60)
    
    with app.app_context():
        test_inputs = [
            "Learn React basics for beginners",
            "Build a mobile app with React Native",
            "Create a REST API with Node.js",
            "Implement machine learning with Python",
            "Deploy application to AWS"
        ]
        
        from intent_analysis_engine import analyze_user_intent
        
        for i, test_input in enumerate(test_inputs, 1):
            print(f"\n🧪 Test {i}: {test_input}")
            print("-" * 30)
            
            # First analysis (should use LLM)
            start_time = time.time()
            intent1 = analyze_user_intent(test_input)
            first_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ First analysis: {first_time:.2f}ms")
            print(f"🎯 Result: {intent1.primary_goal} - {intent1.project_type}")
            
            # Second analysis (should use cache)
            start_time = time.time()
            intent2 = analyze_user_intent(test_input)
            second_time = (time.time() - start_time) * 1000
            
            print(f"⏱️ Second analysis: {second_time:.2f}ms")
            print(f"🔄 Cache hit: {'Yes' if second_time < 100 else 'No'}")
            
            # Verify consistency
            if intent1.context_hash == intent2.context_hash:
                print("✅ Cache consistency verified")
            else:
                print("⚠️ Cache inconsistency detected")

def test_project_intent_integration():
    """Test intent analysis integration with project creation"""
    
    print("\n\n🏗️ Testing Project Intent Integration")
    print("=" * 60)
    
    with app.app_context():
        try:
            from models import Project, User
            from intent_analysis_engine import analyze_user_intent
            
            # Test project data
            test_project_data = {
                "title": "Advanced React Performance Optimization",
                "description": "Need to optimize a large React application for better performance and user experience",
                "technologies": "react, javascript, performance, optimization, webpack"
            }
            
            print(f"📝 Project: {test_project_data['title']}")
            print(f"📋 Description: {test_project_data['description']}")
            print(f"🔧 Technologies: {test_project_data['technologies']}")
            
            # Simulate intent analysis
            user_input = f"{test_project_data['title']} {test_project_data['description']} {test_project_data['technologies']}"
            intent = analyze_user_intent(user_input)
            
            print(f"\n🧠 Intent Analysis Results:")
            print(f"   - Primary Goal: {intent.primary_goal}")
            print(f"   - Learning Stage: {intent.learning_stage}")
            print(f"   - Project Type: {intent.project_type}")
            print(f"   - Urgency Level: {intent.urgency_level}")
            print(f"   - Specific Technologies: {intent.specific_technologies}")
            print(f"   - Complexity Preference: {intent.complexity_preference}")
            print(f"   - Time Constraint: {intent.time_constraint}")
            print(f"   - Focus Areas: {intent.focus_areas}")
            print(f"   - Context Hash: {intent.context_hash[:16]}...")
            
            # Test recommendation request with this intent
            print(f"\n🎯 Testing Recommendation Request with Intent...")
            
            from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
            
            orchestrator = get_unified_orchestrator()
            if orchestrator:
                request = UnifiedRecommendationRequest(
                    user_id=1,
                    title=test_project_data['title'],
                    description=test_project_data['description'],
                    technologies=test_project_data['technologies'],
                    user_interests="",
                    project_id=None,
                    max_recommendations=3,
                    engine_preference="context"
                )
                
                recommendations = orchestrator.get_recommendations(request)
                print(f"✅ Generated {len(recommendations)} recommendations")
                
                if recommendations:
                    print(f"🏆 Top recommendation score: {recommendations[0].score:.1f}")
                    print(f"💡 Reason: {recommendations[0].reason[:80]}...")
            else:
                print("❌ Orchestrator not available")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🧠 Enhanced Intent Analysis System Test Suite")
    print("=" * 60)
    
    # Run all tests
    test_intent_analysis()
    test_recommendations_with_intent()
    test_enhanced_recommendations_with_intent()
    test_intent_analysis_performance()
    test_project_intent_integration()
    
    print("\n\n🎉 All tests completed!")
    print("=" * 60) 