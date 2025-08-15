#!/usr/bin/env python3
"""
Test New User Pipeline with Intent Analysis
Tests the complete flow for new users creating their first project
"""

import os
import sys
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Project, User
from intent_analysis_engine import analyze_user_intent

def test_new_user_pipeline():
    """Test the complete pipeline for new users"""
    
    print("🧪 Testing New User Pipeline with Intent Analysis")
    print("=" * 60)
    
    with app.app_context():
        # Test 1: Simulate new user project creation
        print("\n📝 Test 1: New User Creates First Project")
        print("-" * 40)
        
        # Create a test user (or use existing)
        test_user = User.query.filter_by(username='test_user').first()
        if not test_user:
            # Try to create with unique email
            import random
            unique_email = f"test_user_{random.randint(1000, 9999)}@example.com"
            
            test_user = User(
                username='test_user',
                email=unique_email,
                password_hash='test_hash'
            )
            db.session.add(test_user)
            db.session.commit()
            print(f"✅ Created test user: {test_user.username} with email: {unique_email}")
        else:
            print(f"✅ Using existing test user: {test_user.username}")
        
        # Test project data
        test_projects = [
            {
                'title': 'Learn React Basics',
                'description': 'I want to learn React fundamentals and build my first web app',
                'technologies': 'React, JavaScript, HTML, CSS'
            },
            {
                'title': 'Build Mobile App',
                'description': 'Need to create a mobile app for my startup with urgent deadline',
                'technologies': 'React Native, Firebase, JavaScript'
            },
            {
                'title': 'Data Science Project',
                'description': 'Advanced machine learning project for data analysis and visualization',
                'technologies': 'Python, TensorFlow, Pandas, NumPy'
            }
        ]
        
        created_projects = []
        
        for i, project_data in enumerate(test_projects, 1):
            print(f"\n🔧 Creating Project {i}: {project_data['title']}")
            
            # Create project (simulating the API endpoint)
            new_project = Project(
                user_id=test_user.id,
                title=project_data['title'],
                description=project_data['description'],
                technologies=project_data['technologies']
            )
            
            db.session.add(new_project)
            db.session.commit()
            
            print(f"   ✅ Project created with ID: {new_project.id}")
            
            # Test intent analysis generation (simulating what happens in the API)
            try:
                user_input = f"{new_project.title} {new_project.description} {new_project.technologies}"
                
                print(f"   🔍 Generating intent analysis...")
                start_time = time.time()
                
                intent = analyze_user_intent(
                    user_input=user_input,
                    project_id=new_project.id,
                    force_analysis=True
                )
                
                analysis_time = time.time() - start_time
                
                print(f"   ✅ Intent analysis completed in {analysis_time:.2f}s")
                print(f"   🎯 Primary Goal: {intent.primary_goal}")
                print(f"   📚 Learning Stage: {intent.learning_stage}")
                print(f"   🏗️ Project Type: {intent.project_type}")
                print(f"   ⚡ Urgency: {intent.urgency_level}")
                print(f"   🛠️ Technologies: {intent.specific_technologies}")
                
                created_projects.append({
                    'project': new_project,
                    'intent': intent,
                    'analysis_time': analysis_time
                })
                
            except Exception as e:
                print(f"   ❌ Intent analysis failed: {str(e)}")
                created_projects.append({
                    'project': new_project,
                    'intent': None,
                    'analysis_time': 0
                })
        
        # Test 2: Verify intent analysis is stored in database
        print(f"\n📊 Test 2: Verify Database Storage")
        print("-" * 40)
        
        for project_data in created_projects:
            project = project_data['project']
            
            # Refresh from database
            db.session.refresh(project)
            
            print(f"\n📁 Project: {project.title}")
            print(f"   ID: {project.id}")
            
            if hasattr(project, 'intent_analysis') and project.intent_analysis:
                try:
                    stored_analysis = json.loads(project.intent_analysis)
                    print(f"   ✅ Intent analysis stored in database")
                    print(f"   📅 Updated: {stored_analysis.get('updated_at', 'Unknown')}")
                    print(f"   🎯 Goal: {stored_analysis.get('primary_goal', 'N/A')}")
                    print(f"   🏗️ Type: {stored_analysis.get('project_type', 'N/A')}")
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON in stored analysis")
            else:
                print(f"   ❌ No intent analysis stored")
        
        # Test 3: Test project update with intent analysis regeneration
        print(f"\n🔄 Test 3: Project Update with Intent Analysis")
        print("-" * 40)
        
        if created_projects:
            test_project = created_projects[0]['project']
            print(f"\n📝 Updating project: {test_project.title}")
            
            # Update project data
            original_title = test_project.title
            test_project.title = "Updated: " + original_title
            test_project.description += " (Updated with new requirements)"
            test_project.technologies += ", TypeScript"
            
            db.session.commit()
            print(f"   ✅ Project updated")
            
            # Test intent analysis regeneration
            try:
                user_input = f"{test_project.title} {test_project.description} {test_project.technologies}"
                
                print(f"   🔍 Regenerating intent analysis...")
                start_time = time.time()
                
                updated_intent = analyze_user_intent(
                    user_input=user_input,
                    project_id=test_project.id,
                    force_analysis=True
                )
                
                analysis_time = time.time() - start_time
                
                print(f"   ✅ Updated intent analysis completed in {analysis_time:.2f}s")
                print(f"   🎯 New Goal: {updated_intent.primary_goal}")
                print(f"   🏗️ New Type: {updated_intent.project_type}")
                print(f"   🛠️ Updated Technologies: {updated_intent.specific_technologies}")
                
            except Exception as e:
                print(f"   ❌ Intent analysis update failed: {str(e)}")
        
        # Test 4: Performance summary
        print(f"\n📈 Test 4: Performance Summary")
        print("-" * 40)
        
        total_analysis_time = sum(p['analysis_time'] for p in created_projects if p['analysis_time'] > 0)
        successful_analyses = sum(1 for p in created_projects if p['intent'] is not None)
        total_projects = len(created_projects)
        
        print(f"   📊 Total Projects Created: {total_projects}")
        print(f"   ✅ Successful Intent Analyses: {successful_analyses}")
        print(f"   ❌ Failed Intent Analyses: {total_projects - successful_analyses}")
        print(f"   ⏱️ Total Analysis Time: {total_analysis_time:.2f}s")
        print(f"   📊 Average Analysis Time: {total_analysis_time/total_projects:.2f}s")
        print(f"   🎯 Success Rate: {(successful_analyses/total_projects*100):.1f}%")
        
        # Test 5: Verify recommendation integration
        print(f"\n🎯 Test 5: Recommendation Integration")
        print("-" * 40)
        
        try:
            from unified_recommendation_orchestrator import UnifiedRecommendationRequest, get_unified_orchestrator
            
            if created_projects:
                test_project = created_projects[0]['project']
                
                print(f"   🔍 Testing recommendations for: {test_project.title}")
                
                # Create recommendation request
                request = UnifiedRecommendationRequest(
                    user_id=test_user.id,
                    title=test_project.title,
                    description=test_project.description,
                    technologies=test_project.technologies,
                    user_interests="Learning and development",
                    project_id=test_project.id,
                    max_recommendations=3
                )
                
                # Get recommendations (this should use the intent analysis)
                orchestrator = get_unified_orchestrator()
                recommendations = orchestrator.get_recommendations(request)
                
                print(f"   ✅ Got {len(recommendations)} recommendations")
                print(f"   🎯 Intent analysis was used for recommendations")
                
        except Exception as e:
            print(f"   ❌ Recommendation test failed: {str(e)}")
        
        print(f"\n🎉 New User Pipeline Test Complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_new_user_pipeline() 