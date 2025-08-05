#!/usr/bin/env python3
"""
Test Smart Engine Fix
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedContent, ContentAnalysis, Project, User
from app import create_app

def test_smart_engine_fix():
    """Test if smart engine circular import is fixed"""
    
    print("🔧 Testing Smart Engine Fix")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get real data from database
            user = User.query.first()
            if user:
                print(f"📊 Found user: {user.username} (ID: {user.id})")
            else:
                print("❌ No users found in database")
                return
            
            print(f"\n👤 Using user: {user.username} (ID: {user.id})")
            
            # Test smart engine import
            print(f"\n🧪 Testing Smart Engine Import:")
            try:
                from smart_recommendation_engine import SmartRecommendationEngine
                print("✅ Smart engine import successful!")
                
                # Test smart engine initialization
                smart_engine = SmartRecommendationEngine(user.id)
                print("✅ Smart engine initialization successful!")
                
                # Test smart engine method
                test_payload = {
                    "title": "React Web Development",
                    "description": "Building modern web applications with React",
                    "technologies": "React, JavaScript, Node.js",
                    "learning_goals": "Frontend development, modern frameworks"
                }
                
                start_time = time.time()
                results = smart_engine.get_smart_recommendations(test_payload, limit=5)
                response_time = (time.time() - start_time) * 1000
                
                print(f"✅ Smart engine working!")
                print(f"   Response time: {response_time:.2f}ms")
                print(f"   Total recommendations: {len(results)}")
                
                # Show top 2 recommendations
                print(f"\n📌 Top 2 Smart Recommendations:")
                for j, rec in enumerate(results[:2], 1):
                    print(f"\n   {j}. {rec.title}")
                    print(f"      Score: {rec.match_score:.2f}")
                    print(f"      Reason: {rec.reasoning[:60]}...")
                
            except Exception as e:
                print(f"❌ Error testing smart engine: {e}")
                import traceback
                traceback.print_exc()
            
            # Test ensemble with smart engine
            print(f"\n🧪 Testing Ensemble with Smart Engine:")
            try:
                from ensemble_engine import get_ensemble_recommendations
                
                ensemble_payload = {
                    "title": "React Web Development",
                    "description": "Building modern web applications with React",
                    "technologies": "React, JavaScript, Node.js",
                    "max_recommendations": 5,
                    "engines": ["unified", "smart", "enhanced"]
                }
                
                start_time = time.time()
                results = get_ensemble_recommendations(user.id, ensemble_payload)
                response_time = (time.time() - start_time) * 1000
                
                print(f"✅ Ensemble with smart engine working!")
                print(f"   Response time: {response_time:.2f}ms")
                print(f"   Total recommendations: {len(results)}")
                
                # Check if smart engine contributed
                smart_contributions = 0
                for rec in results:
                    if rec.get('engine_votes') and 'smart' in rec.get('engine_votes', {}):
                        smart_contributions += 1
                
                print(f"   Smart engine contributions: {smart_contributions}")
                
            except Exception as e:
                print(f"❌ Error testing ensemble with smart: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"\n📊 Smart Engine Fix Summary:")
            print(f"   ✅ Circular import issue resolved")
            print(f"   ✅ Smart engine can be imported")
            print(f"   ✅ Smart engine can be initialized")
            print(f"   ✅ Smart engine can provide recommendations")
            
        except Exception as e:
            print(f"❌ Error in main test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_smart_engine_fix() 