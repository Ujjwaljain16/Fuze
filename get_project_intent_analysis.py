#!/usr/bin/env python3
"""
Get intent analysis for a specific project
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Project, User
from intent_analysis_engine import analyze_user_intent

def get_project_intent_analysis(project_id):
    """Get or generate intent analysis for a specific project"""
    with app.app_context():
        project = Project.query.get(project_id)
        
        if not project:
            print(f"❌ Project with ID {project_id} not found")
            return
        
        print(f"🔍 Intent Analysis for Project: {project.title}")
        print("=" * 60)
        print(f"📁 Project ID: {project.id}")
        print(f"📝 Description: {project.description}")
        print(f"🛠️ Technologies: {project.technologies}")
        print(f"👤 User ID: {project.user_id}")
        print(f"📅 Created: {project.created_at}")
        
        # Check if already has analysis
        if hasattr(project, 'intent_analysis') and project.intent_analysis:
            try:
                analysis = json.loads(project.intent_analysis)
                print(f"\n✅ Existing Intent Analysis:")
                print(f"   📅 Last Updated: {analysis.get('updated_at', 'Unknown')}")
                print(f"   🎯 Primary Goal: {analysis.get('primary_goal', 'N/A')}")
                print(f"   📚 Learning Stage: {analysis.get('learning_stage', 'N/A')}")
                print(f"   🏗️ Project Type: {analysis.get('project_type', 'N/A')}")
                print(f"   ⚡ Urgency Level: {analysis.get('urgency_level', 'N/A')}")
                print(f"   🛠️ Specific Technologies: {analysis.get('specific_technologies', [])}")
                print(f"   📊 Complexity Preference: {analysis.get('complexity_preference', 'N/A')}")
                print(f"   ⏰ Time Constraint: {analysis.get('time_constraint', 'N/A')}")
                print(f"   🎯 Focus Areas: {analysis.get('focus_areas', [])}")
                print(f"   🔑 Context Hash: {analysis.get('context_hash', 'N/A')}")
                print(f"   📈 Confidence Score: {analysis.get('confidence_score', 'N/A')}")
                
                return analysis
                
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON in existing analysis, regenerating...")
        
        # Generate new analysis
        print(f"\n🔄 Generating New Intent Analysis...")
        
        try:
            # Build user input from project data
            user_input = f"{project.title} {project.description} {project.technologies}"
            
            # Generate intent analysis
            intent = analyze_user_intent(
                user_input=user_input,
                project_id=project.id,
                force_analysis=True
            )
            
            print(f"✅ New Intent Analysis Generated:")
            print(f"   🎯 Primary Goal: {intent.primary_goal}")
            print(f"   📚 Learning Stage: {intent.learning_stage}")
            print(f"   🏗️ Project Type: {intent.project_type}")
            print(f"   ⚡ Urgency Level: {intent.urgency_level}")
            print(f"   🛠️ Specific Technologies: {intent.specific_technologies}")
            print(f"   📊 Complexity Preference: {intent.complexity_preference}")
            print(f"   ⏰ Time Constraint: {intent.time_constraint}")
            print(f"   🎯 Focus Areas: {intent.focus_areas}")
            print(f"   🔑 Context Hash: {intent.context_hash}")
            
            return intent
            
        except Exception as e:
            print(f"❌ Failed to generate analysis: {str(e)}")
            return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python get_project_intent_analysis.py <project_id>")
        print("Example: python get_project_intent_analysis.py 1")
        sys.exit(1)
    
    try:
        project_id = int(sys.argv[1])
        get_project_intent_analysis(project_id)
    except ValueError:
        print("❌ Project ID must be a number")
        sys.exit(1) 