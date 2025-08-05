#!/usr/bin/env python3
"""
Test Ensemble Engine with All Engines
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedContent, ContentAnalysis, Project, User
from app import create_app

def test_ensemble_all_engines():
    """Test ensemble engine with all engines enabled"""
    
    print("🎯 Testing Ensemble Engine with All Engines")
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
                "max_recommendations": 5,
                "engines": ["unified", "smart", "enhanced"]  # Use all engines
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
            
            print(f"\n🔧 Testing Ensemble with engines: {test_payload['engines']}")
            
            # Test ensemble engine
            try:
                from ensemble_engine import get_ensemble_recommendations
                
                start_time = time.time()
                results = get_ensemble_recommendations(user.id, test_payload)
                response_time = (time.time() - start_time) * 1000
                
                print(f"✅ Ensemble Engine working!")
                print(f"   Response time: {response_time:.2f}ms")
                print(f"   Total recommendations: {len(results)}")
                
                # Show all recommendations with engine votes
                print(f"\n📌 All Recommendations with Engine Votes:")
                for j, rec in enumerate(results, 1):
                    print(f"\n   {j}. {rec.get('title', 'N/A')}")
                    print(f"      Score: {rec.get('score', 0):.2f}")
                    print(f"      Ensemble Score: {rec.get('ensemble_score', 0):.3f}")
                    
                    if rec.get('engine_votes'):
                        votes = rec.get('engine_votes', {})
                        print(f"      Engine Votes: {', '.join([f'{k}: {v:.3f}' for k, v in votes.items()])}")
                        print(f"      Engines Used: {len(votes)} engines")
                    else:
                        print(f"      Engine Votes: No votes recorded")
                    
                    print(f"      Reason: {rec.get('reason', 'N/A')[:80]}...")
                
                # Count engines used
                all_engines_used = set()
                for rec in results:
                    if rec.get('engine_votes'):
                        all_engines_used.update(rec.get('engine_votes', {}).keys())
                
                print(f"\n📊 Summary:")
                print(f"   Total engines used: {len(all_engines_used)}")
                print(f"   Engines: {', '.join(all_engines_used)}")
                print(f"   Expected engines: {', '.join(test_payload['engines'])}")
                
                if len(all_engines_used) == len(test_payload['engines']):
                    print(f"   ✅ All expected engines are working!")
                else:
                    print(f"   ⚠️  Some engines may not be available")
                    missing = set(test_payload['engines']) - all_engines_used
                    if missing:
                        print(f"   Missing engines: {', '.join(missing)}")
                
            except Exception as e:
                print(f"❌ Error testing ensemble engine: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            print(f"❌ Error in main test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_ensemble_all_engines() 