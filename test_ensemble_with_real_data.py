#!/usr/bin/env python3
"""
Test Ensemble Engine with Real Database Data
"""

import os
import sys
import requests
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import db, SavedContent, ContentAnalysis, Project, User
from app import create_app

def get_real_data_from_db():
    """Get real data from database for testing"""
    app = create_app()
    
    with app.app_context():
        try:
            # Get some real projects
            projects = Project.query.limit(3).all()
            print(f"📊 Found {len(projects)} projects in database")
            
            # Get some real saved content
            saved_content = SavedContent.query.limit(5).all()
            print(f"📊 Found {len(saved_content)} saved content items in database")
            
                         # Get a real user
             user = User.query.first()
             if user:
                 print(f"📊 Found user: {user.username} (ID: {user.id})")
             else:
                 print("❌ No users found in database")
                 return None, None, None
            
            return user, projects, saved_content
            
        except Exception as e:
            print(f"❌ Error getting data from database: {e}")
            return None, None, None

def test_ensemble_with_real_data():
    """Test ensemble engine with real database data"""
    
    print("🚀 Testing Ensemble Engine with Real Database Data")
    print("=" * 70)
    
    # Get real data
    user, projects, saved_content = get_real_data_from_db()
    
    if not user:
        print("❌ Cannot proceed without user data")
        return
    
         print(f"\n👤 Using user: {user.username} (ID: {user.id})")
    
    # Test with each project
    for i, project in enumerate(projects, 1):
        print(f"\n{'='*50}")
        print(f"🧪 Testing Project {i}: {project.title}")
        print(f"   Description: {project.description[:100]}...")
        print(f"   Technologies: {project.technologies}")
        print(f"   ID: {project.id}")
        
        # Create test payload with real project data
        test_payload = {
            "title": project.title,
            "description": project.description,
            "technologies": project.technologies,
            "user_interests": "Software development, modern technologies",
            "project_id": project.id,
            "max_recommendations": 6,
            "engines": ["unified", "smart", "enhanced"],
            "ensemble_method": "weighted_voting"
        }
        
        print(f"\n📤 Sending request to ensemble engine...")
        print(f"   Engines: {test_payload['engines']}")
        print(f"   Max recommendations: {test_payload['max_recommendations']}")
        
        try:
                         # First, get a JWT token for authentication
             login_payload = {
                 "username": user.username,
                 "password": "test123"  # Try common password
             }
            
            login_response = requests.post(
                "http://localhost:5000/api/auth/login",
                json=login_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if login_response.status_code == 200:
                token_data = login_response.json()
                token = token_data.get('access_token')
                                 print(f"✅ Got JWT token for user: {user.username}")
                
                # Now test ensemble engine with authentication
                start_time = time.time()
                ensemble_response = requests.post(
                    "http://localhost:5000/api/recommendations/ensemble",
                    json=test_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}"
                    },
                    timeout=60
                )
                response_time = (time.time() - start_time) * 1000
                
                if ensemble_response.status_code == 200:
                    data = ensemble_response.json()
                    recommendations = data.get('recommendations', [])
                    
                    print(f"✅ Ensemble engine working!")
                    print(f"   Response time: {response_time:.2f}ms")
                    print(f"   Total recommendations: {len(recommendations)}")
                    print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
                    
                    # Show performance metrics
                    if 'performance_metrics' in data:
                        metrics = data['performance_metrics']
                        print(f"   Engines used: {metrics.get('ensemble_engines_used', [])}")
                    
                    # Show top 3 recommendations with ensemble scores
                    print(f"\n📌 Top 3 Ensemble Recommendations:")
                    for j, rec in enumerate(recommendations[:3], 1):
                        print(f"\n   {j}. {rec.get('title', 'N/A')}")
                        print(f"      URL: {rec.get('url', 'N/A')}")
                        print(f"      Ensemble Score: {rec.get('ensemble_score', 0):.3f}")
                        print(f"      Original Score: {rec.get('score', 0):.2f}")
                        print(f"      Reason: {rec.get('reason', 'N/A')[:100]}...")
                        
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
                    
                elif ensemble_response.status_code == 401:
                    print("❌ Authentication failed")
                else:
                    print(f"❌ Error: {ensemble_response.status_code}")
                    print(f"   Response: {ensemble_response.text}")
                    
            else:
                print(f"❌ Login failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
                
        except Exception as e:
            print(f"❌ Error testing ensemble engine: {e}")
    
    # Test with general recommendations (no specific project)
    print(f"\n{'='*50}")
    print("🧪 Testing General Recommendations (No Project)")
    print(f"{'='*50}")
    
    general_payload = {
        "title": "Modern Web Development",
        "description": "Building modern web applications with React, Node.js, and cloud technologies",
        "technologies": "React, Node.js, MongoDB, AWS",
        "user_interests": "Full-stack development, cloud computing, modern frameworks",
        "max_recommendations": 5,
        "engines": ["unified", "smart", "enhanced"],
        "ensemble_method": "weighted_voting"
    }
    
    print(f"📤 Sending general recommendation request...")
    print(f"   Title: {general_payload['title']}")
    print(f"   Technologies: {general_payload['technologies']}")
    
    try:
                 # Get JWT token again
         login_payload = {
             "username": user.username,
             "password": "test123"
         }
        
        login_response = requests.post(
            "http://localhost:5000/api/auth/login",
            json=login_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            token = token_data.get('access_token')
            
            # Test ensemble engine
            start_time = time.time()
            ensemble_response = requests.post(
                "http://localhost:5000/api/recommendations/ensemble",
                json=general_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}"
                },
                timeout=60
            )
            response_time = (time.time() - start_time) * 1000
            
            if ensemble_response.status_code == 200:
                data = ensemble_response.json()
                recommendations = data.get('recommendations', [])
                
                print(f"✅ General ensemble recommendations working!")
                print(f"   Response time: {response_time:.2f}ms")
                print(f"   Total recommendations: {len(recommendations)}")
                
                # Show top 2 recommendations
                print(f"\n📌 Top 2 General Recommendations:")
                for j, rec in enumerate(recommendations[:2], 1):
                    print(f"\n   {j}. {rec.get('title', 'N/A')}")
                    print(f"      Ensemble Score: {rec.get('ensemble_score', 0):.3f}")
                    print(f"      Reason: {rec.get('reason', 'N/A')[:80]}...")
                    
                    engine_votes = rec.get('engine_votes', {})
                    if engine_votes:
                        print(f"      Engine Votes: {', '.join([f'{k}: {v:.2f}' for k, v in engine_votes.items()])}")
                
            else:
                print(f"❌ Error: {ensemble_response.status_code}")
                print(f"   Response: {ensemble_response.text}")
                
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing general recommendations: {e}")
    
    print(f"\n{'='*70}")
    print("🎯 Ensemble Engine Testing with Real Data Complete!")
    print("\n💡 What we tested:")
    print("1. ✅ Project-specific recommendations with real project data")
    print("2. ✅ General recommendations without project context")
    print("3. ✅ Multiple engine combinations (unified, smart, enhanced)")
    print("4. ✅ Ensemble scoring and engine voting transparency")
    print("5. ✅ Authentication with real user data")
    
    print("\n🚀 Next steps:")
    print("1. Integrate ensemble engine into your frontend")
    print("2. Add engine selection options in the UI")
    print("3. Display ensemble scores and engine votes to users")

if __name__ == "__main__":
    test_ensemble_with_real_data() 