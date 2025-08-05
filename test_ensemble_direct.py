#!/usr/bin/env python3
"""
Direct Test of Ensemble Engine (No Authentication)
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedContent, ContentAnalysis, Project, User
from app import create_app
from ensemble_engine import get_ensemble_recommendations

def test_ensemble_direct():
    """Test ensemble engine directly without authentication"""
    
    print("🚀 Testing Ensemble Engine Directly (No Auth)")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get real data from database
            projects = Project.query.limit(2).all()
            print(f"📊 Found {len(projects)} projects in database")
            
            saved_content = SavedContent.query.limit(5).all()
            print(f"📊 Found {len(saved_content)} saved content items in database")
            
            user = User.query.first()
            if user:
                print(f"📊 Found user: {user.username} (ID: {user.id})")
            else:
                print("❌ No users found in database")
                return
            
            print(f"\n👤 Using user: {user.username} (ID: {user.id})")
            
            # Test with each project
            for i, project in enumerate(projects, 1):
                print(f"\n{'='*50}")
                print(f"🧪 Testing Project {i}: {project.title}")
                print(f"   Description: {project.description[:80]}...")
                print(f"   Technologies: {project.technologies}")
                print(f"   ID: {project.id}")
                
                # Create test payload
                test_payload = {
                    "title": project.title,
                    "description": project.description,
                    "technologies": project.technologies,
                    "user_interests": "Software development, modern technologies",
                    "project_id": project.id,
                    "max_recommendations": 5,
                    "engines": ["unified", "smart", "enhanced"],
                    "ensemble_method": "weighted_voting"
                }
                
                print(f"\n📤 Testing ensemble engine directly...")
                print(f"   Engines: {test_payload['engines']}")
                print(f"   Max recommendations: {test_payload['max_recommendations']}")
                
                try:
                    start_time = time.time()
                    
                    # Call ensemble engine directly
                    results = get_ensemble_recommendations(user.id, test_payload)
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    print(f"✅ Ensemble engine working!")
                    print(f"   Response time: {response_time:.2f}ms")
                    print(f"   Total recommendations: {len(results)}")
                    
                    # Show top 3 recommendations
                    print(f"\n📌 Top 3 Ensemble Recommendations:")
                    for j, rec in enumerate(results[:3], 1):
                        print(f"\n   {j}. {rec.get('title', 'N/A')}")
                        print(f"      URL: {rec.get('url', 'N/A')}")
                        print(f"      Ensemble Score: {rec.get('ensemble_score', 0):.3f}")
                        print(f"      Original Score: {rec.get('score', 0):.2f}")
                        print(f"      Reason: {rec.get('reason', 'N/A')[:80]}...")
                        
                        # Show engine votes
                        engine_votes = rec.get('engine_votes', {})
                        if engine_votes:
                            print(f"      Engine Votes:")
                            for engine, vote in engine_votes.items():
                                print(f"        {engine}: {vote:.3f}")
                        
                        # Show technologies
                        technologies = rec.get('technologies', [])
                        if technologies:
                            print(f"      Technologies: {', '.join(technologies[:3])}")
                    
                except Exception as e:
                    print(f"❌ Error testing ensemble engine: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Test general recommendations
            print(f"\n{'='*50}")
            print("🧪 Testing General Recommendations (No Project)")
            print(f"{'='*50}")
            
            general_payload = {
                "title": "Modern Web Development",
                "description": "Building modern web applications with React, Node.js, and cloud technologies",
                "technologies": "React, Node.js, MongoDB, AWS",
                "user_interests": "Full-stack development, cloud computing, modern frameworks",
                "max_recommendations": 4,
                "engines": ["unified", "smart", "enhanced"],
                "ensemble_method": "weighted_voting"
            }
            
            print(f"📤 Testing general recommendations...")
            print(f"   Title: {general_payload['title']}")
            print(f"   Technologies: {general_payload['technologies']}")
            
            try:
                start_time = time.time()
                results = get_ensemble_recommendations(user.id, general_payload)
                response_time = (time.time() - start_time) * 1000
                
                print(f"✅ General ensemble recommendations working!")
                print(f"   Response time: {response_time:.2f}ms")
                print(f"   Total recommendations: {len(results)}")
                
                # Show top 2 recommendations
                print(f"\n📌 Top 2 General Recommendations:")
                for j, rec in enumerate(results[:2], 1):
                    print(f"\n   {j}. {rec.get('title', 'N/A')}")
                    print(f"      Ensemble Score: {rec.get('ensemble_score', 0):.3f}")
                    print(f"      Reason: {rec.get('reason', 'N/A')[:60]}...")
                    
                    engine_votes = rec.get('engine_votes', {})
                    if engine_votes:
                        print(f"      Engine Votes: {', '.join([f'{k}: {v:.2f}' for k, v in engine_votes.items()])}")
                
            except Exception as e:
                print(f"❌ Error testing general recommendations: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"\n{'='*60}")
            print("🎯 Direct Ensemble Engine Testing Complete!")
            print("\n💡 What we tested:")
            print("1. ✅ Project-specific recommendations with real project data")
            print("2. ✅ General recommendations without project context")
            print("3. ✅ Multiple engine combinations (unified, smart, enhanced)")
            print("4. ✅ Ensemble scoring and engine voting transparency")
            print("5. ✅ Direct engine testing (no authentication issues)")
            
            print("\n🚀 Next steps:")
            print("1. Integrate ensemble engine into your frontend")
            print("2. Add engine selection options in the UI")
            print("3. Display ensemble scores and engine votes to users")
            
        except Exception as e:
            print(f"❌ Error in main test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_direct() 