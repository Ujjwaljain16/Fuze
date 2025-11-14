#!/usr/bin/env python3
"""
Test script to verify AI insights are included in unified orchestrator reasoning
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator

def test_ai_insights_in_reasoning():
    """Test that AI insights are included in reasoning"""
    
    with app.app_context():
        # Create a test request with rich content to trigger intent analysis
        request = UnifiedRecommendationRequest(
            user_id=1,
            title="Build a React Native Expense Tracker",
            description="I want to create a mobile app for tracking expenses with categories, charts, and export functionality. Need to learn about React Native, state management, and mobile UI patterns.",
            technologies="React Native, JavaScript, Expo, Redux, React Navigation",
            user_interests="Mobile development, React, JavaScript, UI/UX",
            project_id=None,
            max_recommendations=5,
            engine_preference="context"  # Use ContextAwareEngine which includes AI insights
        )
        
        # Get recommendations
        orchestrator = get_unified_orchestrator()
        recommendations = orchestrator.get_recommendations(request)
        
        print(f"\n=== AI Insights Reasoning Test ===")
        print(f"Request: {request.title}")
        print(f"Description: {request.description}")
        print(f"Technologies: {request.technologies}")
        print(f"Total recommendations: {len(recommendations)}")
        
        # Check each recommendation for AI insights
        ai_insights_found = False
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n--- Recommendation {i} ---")
            print(f"Title: {rec.title}")
            print(f"Score: {rec.score}")
            print(f"Engine: {rec.engine_used}")
            print(f"Reason: {rec.reason}")
            
            # Check if AI insights are mentioned in the reason
            if any(keyword in rec.reason.lower() for keyword in [
                'ai analysis', 'ai-powered', 'intent analysis', 'tailored for', 'focuses on'
            ]):
                ai_insights_found = True
                print("✅ AI insights found in reasoning!")
            else:
                print("❌ No AI insights detected in reasoning")
        
        print(f"\n=== Summary ===")
        if ai_insights_found:
            print("✅ AI insights are being included in reasoning!")
        else:
            print("❌ AI insights are NOT being included in reasoning")
        
        return ai_insights_found

if __name__ == "__main__":
    success = test_ai_insights_in_reasoning()
    if success:
        print("\n🎉 Test PASSED: AI insights are working correctly!")
    else:
        print("\n💥 Test FAILED: AI insights are not working as expected!") 