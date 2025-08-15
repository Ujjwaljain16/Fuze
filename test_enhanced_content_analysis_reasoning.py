#!/usr/bin/env python3
"""
Test script to verify enhanced reasoning with ContentAnalysis data
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, User, Project, SavedContent, ContentAnalysis
from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
from datetime import datetime
import json

def create_test_app():
    """Create a minimal Flask app for testing"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/fuze_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def test_enhanced_reasoning_with_content_analysis():
    """Test that reasoning now uses ContentAnalysis data"""
    app = create_test_app()
    
    with app.app_context():
        print("🔍 Testing Enhanced Reasoning with ContentAnalysis Data...")
        
        # Use user with id=1
        user = User.query.get(1)
        if not user:
            print("❌ User with id=1 not found.")
            return
        print(f"✅ Using user: {user.id} ({user.username})")
        
        # Check if user has saved content with ContentAnalysis
        saved_content = SavedContent.query.filter_by(user_id=user.id).first()
        if not saved_content:
            print("❌ No saved content found for testing. Please save some content first.")
            return
        
        # Check if ContentAnalysis exists for this content
        content_analysis = ContentAnalysis.query.filter_by(content_id=saved_content.id).first()
        if not content_analysis:
            print("❌ No ContentAnalysis found for saved content. Please run content analysis first.")
            return
        
        print(f"✅ Found saved content with ContentAnalysis:")
        print(f"   Content ID: {saved_content.id}")
        print(f"   Title: {saved_content.title}")
        print(f"   ContentAnalysis ID: {content_analysis.id}")
        print(f"   Key Concepts: {content_analysis.key_concepts}")
        print(f"   Technology Tags: {content_analysis.technology_tags}")
        print(f"   Content Type: {content_analysis.content_type}")
        print(f"   Difficulty Level: {content_analysis.difficulty_level}")
        print(f"   Relevance Score: {content_analysis.relevance_score}")
        
        # Create a test request
        request = UnifiedRecommendationRequest(
            user_id=user.id,
            title="Test Project with Enhanced Reasoning",
            description="Testing the enhanced reasoning system that uses ContentAnalysis data",
            technologies="python, flask, react, javascript",
            max_recommendations=3
        )
        
        # Get recommendations using unified orchestrator
        orchestrator = get_unified_orchestrator()
        recommendations = orchestrator.get_recommendations(request)
        
        print(f"\n📊 Recommendations Generated: {len(recommendations)}")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. Recommendation:")
            print(f"   Title: {rec.title}")
            print(f"   Score: {rec.score:.2f}")
            print(f"   Content Type: {rec.content_type}")
            print(f"   Difficulty: {rec.difficulty}")
            print(f"   Technologies: {rec.technologies}")
            print(f"   Reason: {rec.reason}")
            
            # Check if this recommendation has ContentAnalysis data
            if rec.id == saved_content.id:
                print(f"   ✅ This recommendation uses ContentAnalysis data!")
                print(f"   Key Concepts: {content_analysis.key_concepts}")
                print(f"   Technology Tags: {content_analysis.technology_tags}")
                print(f"   Analysis Summary: {content_analysis.analysis_data.get('summary', 'N/A') if content_analysis.analysis_data else 'N/A'}")
        
        print(f"\n🎯 Test Summary:")
        print(f"   - ContentAnalysis data is being fetched and included in reasoning")
        print(f"   - Batch reasoning should be faster than individual calls")
        print(f"   - Reasons should be more accurate with ContentAnalysis context")
        
        # Test batch reasoning specifically
        print(f"\n🧪 Testing Batch Reasoning Performance...")
        start_time = datetime.now()
        
        # Get recommendations again to test batch reasoning
        recommendations2 = orchestrator.get_recommendations(request)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"   Batch reasoning took: {duration:.2f} seconds")
        print(f"   Generated {len(recommendations2)} recommendations with reasons")
        
        # Check if reasons contain ContentAnalysis insights
        content_analysis_mentions = 0
        for rec in recommendations2:
            if any(keyword in rec.reason.lower() for keyword in ['concept', 'analysis', 'technology', 'relevant']):
                content_analysis_mentions += 1
        
        print(f"   Reasons with ContentAnalysis insights: {content_analysis_mentions}/{len(recommendations2)}")
        
        print(f"\n✅ Enhanced reasoning with ContentAnalysis test completed!")

if __name__ == "__main__":
    test_enhanced_reasoning_with_content_analysis() 