#!/usr/bin/env python3
"""
Test script for direct recommendation functions (no API needed)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from blueprints.recommendations import get_basic_recommendations, get_enhanced_recommendations, get_phase3_recommendations
from models import db, SavedContent
from app import create_app

def test_direct_recommendations():
    """Test recommendation functions directly"""
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print("🧪 Testing Direct Recommendation Functions")
        print("=" * 50)
        
        # Test data for DSA visualizer project
        test_data = {
            "project_title": "DSA Visualizer",
            "project_description": "I want to build an interactive data structure and algorithm visualizer",
            "technologies": "javascript, html, css, canvas",
            "learning_goals": "Master data structures and algorithms through interactive visualization",
            "content_type": "all",
            "difficulty": "all",
            "max_recommendations": 10,
            "use_phase1": True,
            "use_phase2": True,
            "use_phase3": True,
            "use_gemini": True
        }
        
        # Get a test user ID (assuming user ID 1 exists)
        test_user_id = 1
        
        print(f"Test User ID: {test_user_id}")
        print(f"Test Data: {test_data}")
        print()
        
        # Test Phase 1 (Smart Match)
        print("🔍 Testing Phase 1: Smart Match")
        print("-" * 30)
        try:
            phase1_result = get_basic_recommendations(test_user_id, test_data)
            recommendations = phase1_result.get('recommendations', [])
            print(f"✅ Phase 1 generated {len(recommendations)} recommendations")
            
            if recommendations:
                print("Top 3 Phase 1 recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    print(f"  {i+1}. {rec.get('title', 'No title')} (Score: {rec.get('score', 0):.1f})")
                    print(f"     Reasoning: {rec.get('reasoning', 'No reasoning')}")
                print()
            else:
                print("⚠️  No Phase 1 recommendations found")
                print()
                
        except Exception as e:
            print(f"❌ Phase 1 error: {e}")
            print()
        
        # Test Phase 2 (Power Boost)
        print("🚀 Testing Phase 2: Power Boost")
        print("-" * 30)
        try:
            phase2_result = get_enhanced_recommendations(test_user_id, test_data)
            recommendations = phase2_result.get('recommendations', [])
            print(f"✅ Phase 2 generated {len(recommendations)} recommendations")
            
            if recommendations:
                print("Top 3 Phase 2 recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    print(f"  {i+1}. {rec.get('title', 'No title')} (Score: {rec.get('score', 0):.1f})")
                    print(f"     Reasoning: {rec.get('reasoning', 'No reasoning')}")
                print()
            else:
                print("⚠️  No Phase 2 recommendations found")
                print()
                
        except Exception as e:
            print(f"❌ Phase 2 error: {e}")
            print()
        
        # Test Phase 3 (Genius Mode)
        print("🧠 Testing Phase 3: Genius Mode")
        print("-" * 30)
        try:
            phase3_result = get_phase3_recommendations(test_user_id, test_data)
            recommendations = phase3_result.get('recommendations', [])
            print(f"✅ Phase 3 generated {len(recommendations)} recommendations")
            
            if recommendations:
                print("Top 3 Phase 3 recommendations:")
                for i, rec in enumerate(recommendations[:3]):
                    print(f"  {i+1}. {rec.get('title', 'No title')} (Score: {rec.get('score', 0):.1f})")
                    print(f"     Reasoning: {rec.get('reasoning', 'No reasoning')}")
                print()
            else:
                print("⚠️  No Phase 3 recommendations found")
                print()
                
        except Exception as e:
            print(f"❌ Phase 3 error: {e}")
            print()
        
        # Overall analysis
        print("📊 Overall Analysis")
        print("-" * 30)
        
        all_scores = []
        all_recommendations = []
        
        # Collect all recommendations and scores
        for phase_name, phase_result in [("Phase 1", phase1_result), ("Phase 2", phase2_result), ("Phase 3", phase3_result)]:
            try:
                recs = phase_result.get('recommendations', [])
                scores = [rec.get('score', 0) for rec in recs]
                all_scores.extend(scores)
                all_recommendations.extend(recs)
                print(f"{phase_name}: {len(recs)} recommendations, avg score: {sum(scores)/len(scores) if scores else 0:.2f}")
            except:
                print(f"{phase_name}: Error occurred")
        
        if all_scores:
            print(f"\nTotal recommendations: {len(all_recommendations)}")
            print(f"Average score across all phases: {sum(all_scores)/len(all_scores):.2f}")
            print(f"Score range: {min(all_scores):.2f} - {max(all_scores):.2f}")
            
            if sum(all_scores)/len(all_scores) > 3.0:
                print("✅ Overall scores look good!")
            else:
                print("⚠️  Overall scores might be too low")
        else:
            print("❌ No recommendations found across all phases")

if __name__ == "__main__":
    test_direct_recommendations() 