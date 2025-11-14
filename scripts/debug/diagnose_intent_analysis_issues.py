#!/usr/bin/env python3
"""
Diagnose Intent Analysis Issues
Identifies and fixes problems in the intent analysis system
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def diagnose_intent_analysis():
    """Comprehensive diagnosis of intent analysis system"""
    print("🔍 **Intent Analysis System Diagnosis**")
    print("=" * 50)
    
    issues_found = []
    
    # 1. Check database schema
    print("\n📊 **1. Database Schema Check**")
    try:
        from models import db, Project
        from app import create_app
        
        app = create_app()
        with app.app_context():
            # Check if intent_analysis columns exist
            try:
                # Test query to see if columns exist
                result = db.session.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'project' 
                    AND column_name IN ('intent_analysis', 'intent_analysis_updated')
                """))
                columns = {row[0]: row[1] for row in result}
                
                if 'intent_analysis' not in columns:
                    issues_found.append("❌ Missing intent_analysis column in Project table")
                    print("❌ Missing intent_analysis column")
                else:
                    print(f"✅ intent_analysis column exists: {columns['intent_analysis']}")
                
                if 'intent_analysis_updated' not in columns:
                    issues_found.append("❌ Missing intent_analysis_updated column in Project table")
                    print("❌ Missing intent_analysis_updated column")
                else:
                    print(f"✅ intent_analysis_updated column exists: {columns['intent_analysis_updated']}")
                    
            except Exception as e:
                issues_found.append(f"❌ Database schema check failed: {e}")
                print(f"❌ Schema check failed: {e}")
                
    except Exception as e:
        issues_found.append(f"❌ Database connection failed: {e}")
        print(f"❌ Database connection failed: {e}")
    
    # 2. Check intent analysis engine
    print("\n🤖 **2. Intent Analysis Engine Check**")
    try:
        from intent_analysis_engine import IntentAnalysisEngine, analyze_user_intent
        
        # Test engine initialization
        engine = IntentAnalysisEngine()
        print("✅ IntentAnalysisEngine initialized successfully")
        
        # Test basic analysis
        test_input = "I want to build a React web app with Python backend"
        try:
            intent = analyze_user_intent(test_input)
            print(f"✅ Basic intent analysis works: {intent.primary_goal}")
        except Exception as e:
            issues_found.append(f"❌ Basic intent analysis failed: {e}")
            print(f"❌ Basic analysis failed: {e}")
            
    except Exception as e:
        issues_found.append(f"❌ Intent analysis engine import failed: {e}")
        print(f"❌ Engine import failed: {e}")
    
    # 3. Check Gemini integration
    print("\n🔑 **3. Gemini AI Integration Check**")
    try:
        from gemini_utils import GeminiAnalyzer
        
        # Check API key
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            issues_found.append("❌ GEMINI_API_KEY environment variable not set")
            print("❌ GEMINI_API_KEY not set")
        else:
            print(f"✅ GEMINI_API_KEY found: {api_key[:10]}...")
            
        # Test Gemini connection
        try:
            analyzer = GeminiAnalyzer()
            print("✅ GeminiAnalyzer initialized successfully")
        except Exception as e:
            issues_found.append(f"❌ GeminiAnalyzer initialization failed: {e}")
            print(f"❌ Gemini initialization failed: {e}")
            
    except Exception as e:
        issues_found.append(f"❌ Gemini utils import failed: {e}")
        print(f"❌ Gemini import failed: {e}")
    
    # 4. Check existing intent analysis data
    print("\n💾 **4. Existing Intent Analysis Data Check**")
    try:
        from models import db, Project
        from app import create_app
        
        app = create_app()
        with app.app_context():
            # Check projects with intent analysis
            projects_with_intent = Project.query.filter(
                Project.intent_analysis.isnot(None)
            ).count()
            
            print(f"✅ Projects with intent analysis: {projects_with_intent}")
            
            if projects_with_intent > 0:
                # Check data quality
                sample_project = Project.query.filter(
                    Project.intent_analysis.isnot(None)
                ).first()
                
                if sample_project:
                    try:
                        analysis_data = json.loads(sample_project.intent_analysis)
                        print(f"✅ Sample analysis data valid: {analysis_data.get('primary_goal', 'N/A')}")
                    except json.JSONDecodeError as e:
                        issues_found.append(f"❌ Invalid JSON in intent_analysis: {e}")
                        print(f"❌ Invalid JSON in sample project: {e}")
                        
    except Exception as e:
        issues_found.append(f"❌ Data check failed: {e}")
        print(f"❌ Data check failed: {e}")
    
    # 5. Performance test
    print("\n⚡ **5. Intent Analysis Performance Test**")
    try:
        from intent_analysis_engine import analyze_user_intent
        
        test_inputs = [
            "Build a React app",
            "Learn Python for data science",
            "Create a REST API with Node.js",
            "Mobile app development with Flutter"
        ]
        
        start_time = time.time()
        for i, test_input in enumerate(test_inputs):
            try:
                intent = analyze_user_intent(test_input)
                print(f"✅ Test {i+1}: {intent.primary_goal} ({time.time() - start_time:.2f}s)")
            except Exception as e:
                issues_found.append(f"❌ Performance test {i+1} failed: {e}")
                print(f"❌ Test {i+1} failed: {e}")
                
        total_time = time.time() - start_time
        avg_time = total_time / len(test_inputs)
        print(f"📊 Average analysis time: {avg_time:.2f}s")
        
        if avg_time > 5.0:
            issues_found.append(f"⚠️ Slow intent analysis: {avg_time:.2f}s average")
            
    except Exception as e:
        issues_found.append(f"❌ Performance test failed: {e}")
        print(f"❌ Performance test failed: {e}")
    
    # 6. Summary and recommendations
    print("\n📋 **6. Summary & Recommendations**")
    print("=" * 50)
    
    if not issues_found:
        print("🎉 **No critical issues found!** Intent analysis system is working correctly.")
    else:
        print(f"🚨 **Found {len(issues_found)} issues:**")
        for issue in issues_found:
            print(f"  {issue}")
        
        print("\n🔧 **Recommended Fixes:**")
        
        if any("Missing intent_analysis column" in issue for issue in issues_found):
            print("  • Run: python add_intent_analysis_fields.py")
            
        if any("GEMINI_API_KEY" in issue for issue in issues_found):
            print("  • Set GEMINI_API_KEY environment variable")
            
        if any("Invalid JSON" in issue for issue in issues_found):
            print("  • Run: python check_existing_intent_analysis.py")
            print("  • Clean up corrupted intent analysis data")
            
        if any("Slow intent analysis" in issue for issue in issues_found):
            print("  • Check Gemini API rate limits")
            print("  • Implement better caching strategy")
    
    return issues_found

def fix_intent_analysis_issues():
    """Attempt to fix common intent analysis issues"""
    print("\n🔧 **Attempting to Fix Issues**")
    print("=" * 50)
    
    fixes_applied = []
    
    # 1. Add missing database columns
    try:
        print("📊 Adding missing database columns...")
        from add_intent_analysis_fields import add_intent_analysis_fields
        add_intent_analysis_fields()
        fixes_applied.append("✅ Added missing database columns")
    except Exception as e:
        print(f"❌ Failed to add columns: {e}")
    
    # 2. Check and clean corrupted data
    try:
        print("🧹 Checking for corrupted intent analysis data...")
        from check_existing_intent_analysis import check_existing_intent_analysis
        check_existing_intent_analysis()
        fixes_applied.append("✅ Checked for corrupted data")
    except Exception as e:
        print(f"❌ Failed to check data: {e}")
    
    # 3. Generate fresh intent analysis for projects
    try:
        print("🔄 Generating fresh intent analysis...")
        from generate_intent_analysis_for_projects import generate_intent_analysis_for_projects
        generate_intent_analysis_for_projects()
        fixes_applied.append("✅ Generated fresh intent analysis")
    except Exception as e:
        print(f"❌ Failed to generate analysis: {e}")
    
    if fixes_applied:
        print(f"\n✅ **Applied {len(fixes_applied)} fixes:**")
        for fix in fixes_applied:
            print(f"  {fix}")
    else:
        print("\n⚠️ **No automatic fixes could be applied**")
    
    return fixes_applied

if __name__ == "__main__":
    print("🚀 **Intent Analysis System Diagnosis & Repair**")
    print("=" * 60)
    
    # Run diagnosis
    issues = diagnose_intent_analysis()
    
    # Offer to fix issues
    if issues:
        print(f"\n🔧 **Found {len(issues)} issues. Attempt to fix them? (y/n):**")
        try:
            response = input().lower().strip()
            if response in ['y', 'yes']:
                fixes = fix_intent_analysis_issues()
                
                # Re-run diagnosis to check if fixes worked
                print("\n🔄 **Re-running diagnosis to verify fixes...**")
                remaining_issues = diagnose_intent_analysis()
                
                if len(remaining_issues) < len(issues):
                    print(f"\n🎉 **Fixes successful! Reduced issues from {len(issues)} to {len(remaining_issues)}**")
                else:
                    print(f"\n⚠️ **Some issues remain. Manual intervention may be required.**")
            else:
                print("\n⏭️ **Skipping automatic fixes. Manual intervention required.**")
        except KeyboardInterrupt:
            print("\n\n⏹️ **Diagnosis interrupted by user**")
    else:
        print("\n🎉 **No issues found! System is working correctly.**")
    
    print("\n✨ **Diagnosis complete!**")
