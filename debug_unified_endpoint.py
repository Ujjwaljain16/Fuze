#!/usr/bin/env python3
"""
Debug unified endpoint directly
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(".env")
    if env_file.exists():
        print("📁 Loading environment variables from .env file...")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment variables loaded successfully!")
    else:
        print("⚠️  .env file not found")

def debug_unified_endpoint():
    """Debug unified endpoint directly"""
    print("🔍 Debugging Unified Endpoint Directly")
    print("=" * 40)
    
    # Load environment variables
    load_env_file()
    
    # Set up Flask app context
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from app import app
        from blueprints.recommendations import get_basic_recommendations, get_enhanced_recommendations, get_phase3_recommendations
        from models import SavedContent
        
        with app.app_context():
            print("✅ Flask app context created")
            
            # Test data (same as API test)
            test_data = {
                "project_title": "Learning Project",
                "project_description": "I want to learn and improve my skills",
                "technologies": "mobile app react native expo",
                "learning_goals": "Master relevant technologies and improve skills",
                "content_type": "all",
                "difficulty": "all",
                "max_recommendations": 5,
                "use_phase1": True,
                "use_phase2": False,
                "use_phase3": False,
                "use_gemini": False
            }
            
            # Get user ID (assuming user exists)
            user_id = 1  # You might need to adjust this
            
            print(f"🔍 Testing unified logic with user_id={user_id}")
            print(f"📊 Test data: {test_data}")
            
            # Check if user has saved content
            saved_content = SavedContent.query.filter_by(user_id=user_id).all()
            print(f"📚 User has {len(saved_content)} saved content items")
            
            if not saved_content:
                print("❌ No saved content found for user")
                return
            
            # Extract phase preferences
            use_phase1 = test_data.get('use_phase1', True)
            use_phase2 = test_data.get('use_phase2', True)
            use_phase3 = test_data.get('use_phase3', True)
            use_gemini = test_data.get('use_gemini', True)
            
            print(f"📊 Phase settings: 1={use_phase1}, 2={use_phase2}, 3={use_phase3}, Gemini={use_gemini}")
            
            # Start with basic recommendations (Phase 1)
            recommendations = []
            
            # Phase 1: Basic recommendations
            if use_phase1:
                try:
                    print("Starting Phase 1 (Smart Match)...")
                    basic_response = get_basic_recommendations(user_id, test_data)
                    if basic_response and 'recommendations' in basic_response:
                        recommendations.extend(basic_response['recommendations'])
                        print(f"Phase 1 added {len(basic_response['recommendations'])} recommendations")
                    else:
                        print("Phase 1 returned no recommendations")
                except Exception as e:
                    print(f"Phase 1 error: {e}")
            
            # Phase 2: Enhanced recommendations
            if use_phase2:
                try:
                    print("Starting Phase 2 (Power Boost)...")
                    enhanced_response = get_enhanced_recommendations(user_id, test_data)
                    if enhanced_response and 'recommendations' in enhanced_response:
                        recommendations.extend(enhanced_response['recommendations'])
                        print(f"Phase 2 added {len(enhanced_response['recommendations'])} recommendations")
                    else:
                        print("Phase 2 returned no recommendations")
                except Exception as e:
                    print(f"Phase 2 error: {e}")
            
            # Phase 3: Advanced recommendations with Gemini
            if use_phase3 and use_gemini:
                try:
                    print("Starting Phase 3 (Genius Mode)...")
                    phase3_response = get_phase3_recommendations(user_id, test_data)
                    if phase3_response and 'recommendations' in phase3_response:
                        recommendations.extend(phase3_response['recommendations'])
                        print(f"Phase 3 added {len(phase3_response['recommendations'])} recommendations")
                    else:
                        print("Phase 3 returned no recommendations")
                except Exception as e:
                    print(f"Phase 3 error: {e}")
            
            print(f"\n📊 Final Result:")
            print(f"  - Total recommendations: {len(recommendations)}")
            
            # Check for Gemini-enhanced recommendations
            gemini_enhanced = 0
            enhanced_scores = 0
            
            for i, rec in enumerate(recommendations[:5]):
                print(f"    {i+1}. {rec.get('title', 'No title')}")
                print(f"       Score: {rec.get('score', 0)}")
                print(f"       Algorithm: {rec.get('algorithm_used', 'Unknown')}")
                
                # Check for Gemini enhancements
                if rec.get('algorithm_used') == 'phase3_gemini_enhanced_genius_mode':
                    gemini_enhanced += 1
                    print(f"       🧠 GEMINI ENHANCED!")
                
                if rec.get('score', 0) > 10.0:
                    enhanced_scores += 1
                    print(f"       ⭐ ENHANCED SCORE!")
                
                print(f"       Reasoning: {rec.get('reasoning', 'No reasoning')[:100]}...")
                print()
            
            print(f"📊 Summary:")
            print(f"  - Gemini-enhanced recommendations: {gemini_enhanced}")
            print(f"  - Enhanced scores (>10.0): {enhanced_scores}")
            
            if gemini_enhanced > 0:
                print("✅ Gemini integration is working in unified logic!")
            else:
                print("❌ No Gemini-enhanced recommendations found in unified logic")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_unified_endpoint() 