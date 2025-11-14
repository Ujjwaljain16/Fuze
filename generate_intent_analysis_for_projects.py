#!/usr/bin/env python3
"""
Generate intent analysis for all existing projects
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

def generate_intent_analysis_for_projects():
    """Generate intent analysis for all projects that don't have it"""
    with app.app_context():
        projects = Project.query.all()
        
        print("🚀 Generating Intent Analysis for Existing Projects")
        print("=" * 60)
        
        projects_processed = 0
        projects_skipped = 0
        projects_failed = 0
        
        for project in projects:
            print(f"\n📁 Processing: {project.title}")
            print(f"   ID: {project.id}")
            print(f"   Technologies: {project.technologies}")
            
            # Check if already has analysis
            if hasattr(project, 'intent_analysis') and project.intent_analysis:
                try:
                    existing_analysis = json.loads(project.intent_analysis)
                    print(f"   ⏭️ Skipping - Already has analysis from {existing_analysis.get('updated_at', 'Unknown')}")
                    projects_skipped += 1
                    continue
                except json.JSONDecodeError:
                    print(f"   🔄 Invalid existing analysis, regenerating...")
            
            try:
                # Build user input from project data
                user_input = f"{project.title} {project.description} {project.technologies}"
                
                print(f"   🔍 Analyzing intent...")
                
                # Generate intent analysis
                intent = analyze_user_intent(
                    user_input=user_input,
                    project_id=project.id,
                    force_analysis=True  # Force new analysis
                )
                
                print(f"   ✅ Analysis Complete!")
                print(f"   🎯 Primary Goal: {intent.primary_goal}")
                print(f"   📚 Learning Stage: {intent.learning_stage}")
                print(f"   🏗️ Project Type: {intent.project_type}")
                print(f"   ⚡ Urgency: {intent.urgency_level}")
                print(f"   🛠️ Technologies: {intent.specific_technologies}")
                
                projects_processed += 1
                
            except Exception as e:
                print(f"   ❌ Failed to analyze: {str(e)}")
                projects_failed += 1
        
        print("\n" + "=" * 60)
        print(f"📊 Summary:")
        print(f"   Total Projects: {len(projects)}")
        print(f"   Processed: {projects_processed}")
        print(f"   Skipped: {projects_skipped}")
        print(f"   Failed: {projects_failed}")
        print(f"   Success Rate: {(projects_processed/(projects_processed+projects_failed)*100):.1f}%")

if __name__ == "__main__":
    generate_intent_analysis_for_projects() 