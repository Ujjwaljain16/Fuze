#!/usr/bin/env python3
"""
Check existing intent analysis for saved projects
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Project, User

def check_existing_intent_analysis():
    """Check which projects have intent analysis"""
    with app.app_context():
        projects = Project.query.all()
        
        print("🔍 Checking Intent Analysis for Existing Projects")
        print("=" * 60)
        
        projects_with_analysis = 0
        projects_without_analysis = 0
        
        for project in projects:
            print(f"\n📁 Project: {project.title}")
            print(f"   ID: {project.id}")
            print(f"   Technologies: {project.technologies}")
            
            if hasattr(project, 'intent_analysis') and project.intent_analysis:
                try:
                    analysis = json.loads(project.intent_analysis)
                    updated_at = analysis.get('updated_at', 'Unknown')
                    
                    print(f"   ✅ Has Intent Analysis")
                    print(f"   📅 Last Updated: {updated_at}")
                    print(f"   🎯 Primary Goal: {analysis.get('primary_goal', 'N/A')}")
                    print(f"   📚 Learning Stage: {analysis.get('learning_stage', 'N/A')}")
                    print(f"   🏗️ Project Type: {analysis.get('project_type', 'N/A')}")
                    print(f"   ⚡ Urgency: {analysis.get('urgency_level', 'N/A')}")
                    print(f"   🛠️ Technologies: {analysis.get('specific_technologies', [])}")
                    
                    projects_with_analysis += 1
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON in intent_analysis")
            else:
                print(f"   ❌ No Intent Analysis")
                projects_without_analysis += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Summary:")
        print(f"   Total Projects: {len(projects)}")
        print(f"   With Analysis: {projects_with_analysis}")
        print(f"   Without Analysis: {projects_without_analysis}")
        print(f"   Coverage: {(projects_with_analysis/len(projects)*100):.1f}%")

if __name__ == "__main__":
    check_existing_intent_analysis() 