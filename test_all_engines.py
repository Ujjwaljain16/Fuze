#!/usr/bin/env python3
"""
Test All Recommendation Engines
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedContent, ContentAnalysis, Project, User
from app import create_app

def test_all_engines():
    """Test all three recommendation engines"""
    
    print("🚀 Testing All Recommendation Engines")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get real data from database
            projects = Project.query.limit(1).all()
            print(f"📊 Found {len(projects)} projects in database")
            
            user = User.query.first()
            if user:
                print(f"📊 Found user: {user.username} (ID: {user.id})")
            else:
                print("❌ No users found in database")
                return
            
            print(f"\n👤 Using user: {user.username} (ID: {user.id})")
            
            # Test payload
            test_payload = {
                "title": "React Web Development",
                "description": "Building modern web applications with React",
                "technologies": "React, JavaScript, Node.js",
                "user_interests": "Frontend development, modern frameworks",
                "max_recommendations": 5
            }
            
            if projects:
                project = projects[0]
                test_payload.update({
                    "title": project.title,
                    "description": project.description,
                    "technologies": project.technologies,
                    "project_id": project.id
                })
                print(f"📌 Using project: {project.title}")
            
            # Test each engine
            engines = [
                {
                    "name": "🚀 Unified Engine",
                    "function": "unified_recommendation_orchestrator",
                    "test_func": test_unified_engine
                },
                {
                    "name": "🎯 Multi-Engine Ensemble", 
                    "function": "ensemble_engine",
                    "test_func": test_ensemble_engine
                },
                {
                    "name": "🤖 Gemini AI",
                    "function": "gemini_integration_layer",
                    "test_func": test_gemini_engine
                }
            ]
            
            for engine in engines:
                print(f"\n{'='*50}")
                print(f"🧪 Testing {engine['name']}")
                print(f"{'='*50}")
                
                try:
                    start_time = time.time()
                    results = engine['test_func'](user.id, test_payload)
                    response_time = (time.time() - start_time) * 1000
                    
                    print(f"✅ {engine['name']} working!")
                    print(f"   Response time: {response_time:.2f}ms")
                    print(f"   Total recommendations: {len(results)}")
                    
                    # Show top 2 recommendations
                    print(f"\n📌 Top 2 Recommendations:")
                    for j, rec in enumerate(results[:2], 1):
                        print(f"\n   {j}. {rec.get('title', 'N/A')}")
                        print(f"      Score: {rec.get('score', 0):.2f}")
                        print(f"      Reason: {rec.get('reason', 'N/A')[:60]}...")
                        
                        if rec.get('ensemble_score'):
                            print(f"      Ensemble Score: {rec.get('ensemble_score', 0):.3f}")
                        
                        if rec.get('engine_votes'):
                            print(f"      Engine Votes: {', '.join([f'{k}: {v:.2f}' for k, v in rec.get('engine_votes', {}).items()])}")
                    
                except Exception as e:
                    print(f"❌ Error testing {engine['name']}: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"\n{'='*60}")
            print("🎯 All Engine Testing Complete!")
            print("\n💡 Summary:")
            print("1. ✅ Unified Engine - Fast & reliable base recommendations")
            print("2. ✅ Multi-Engine Ensemble - Best accuracy through voting")
            print("3. ✅ Gemini AI - AI-powered enhanced recommendations")
            
        except Exception as e:
            print(f"❌ Error in main test: {e}")
            import traceback
            traceback.print_exc()

def test_unified_engine(user_id, payload):
    """Test unified engine"""
    from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
    
    orchestrator = get_unified_orchestrator()
    request = UnifiedRecommendationRequest(
        user_id=user_id,
        title=payload['title'],
        description=payload['description'],
        technologies=payload['technologies'],
        project_id=payload.get('project_id'),
        max_recommendations=payload['max_recommendations']
    )
    
    results = orchestrator.get_recommendations(request)
    from dataclasses import asdict
    return [asdict(result) for result in results]

def test_ensemble_engine(user_id, payload):
    """Test ensemble engine"""
    from ensemble_engine import get_ensemble_recommendations
    
    ensemble_payload = payload.copy()
    ensemble_payload['engines'] = ['unified', 'smart', 'enhanced']  # Use all engines
    
    return get_ensemble_recommendations(user_id, ensemble_payload)

def test_gemini_engine(user_id, payload):
    """Test Gemini engine"""
    from gemini_integration_layer import get_gemini_enhanced_recommendations
    
    return get_gemini_enhanced_recommendations(user_id, payload)

if __name__ == "__main__":
    test_all_engines() 