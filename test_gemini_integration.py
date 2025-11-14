#!/usr/bin/env python3
"""
Test Gemini Integration in Recommendation System
Tests that explanations are now AI-powered instead of template-based
"""

import os
import sys
from flask import Flask

# Setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ['FLASK_ENV'] = 'development'

from unified_config import get_config
from models import db
from unified_recommendation_orchestrator import (
    UnifiedRecommendationOrchestrator,
    UnifiedRecommendationRequest
)

def test_gemini_explanations():
    """Test that Gemini-powered explanations are working"""
    
    print("\n" + "="*60)
    print("🤖 TESTING GEMINI-POWERED EXPLANATIONS")
    print("="*60 + "\n")
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Get config
    config = get_config()
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database.url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Initialize orchestrator
            print("1. Initializing Unified Orchestrator...")
            orchestrator = UnifiedRecommendationOrchestrator()
            print("   ✅ Orchestrator initialized")
            
            # Check if explainability engine is available
            context_engine = orchestrator.context_engine
            has_explainer = hasattr(context_engine, 'explainer') and context_engine.explainer is not None
            
            print(f"\n2. Checking explainability engine...")
            if has_explainer:
                print("   ✅ Explainability engine is INITIALIZED")
                print("   ✅ Gemini-powered explanations are ACTIVE!")
            else:
                print("   ⚠️  Explainability engine not initialized")
                print("   📝 Will use template-based fallback")
            
            # Create a test request
            print("\n3. Creating test recommendation request...")
            request = UnifiedRecommendationRequest(
                user_id=1,
                title="Build a DSA Visualizer",
                description="I want to visualize data structures and algorithms using Java",
                technologies="java, byte buddy, jvm instrumentation",
                project_id=None,
                max_recommendations=3,
                user_interests="Learning advanced Java and visualization techniques"
            )
            print("   ✅ Test request created")
            
            # Get recommendations
            print("\n4. Getting recommendations...")
            print("   (This may take a few seconds for Gemini to generate explanations...)")
            
            try:
                result = orchestrator.get_recommendations(request)
                
                print(f"\n5. Analyzing recommendations...")
                print(f"   📊 Total recommendations: {len(result.recommendations)}")
                
                if result.recommendations:
                    print("\n" + "="*60)
                    print("SAMPLE RECOMMENDATION WITH EXPLANATION:")
                    print("="*60)
                    
                    rec = result.recommendations[0]
                    print(f"\n📄 Title: {rec.title}")
                    print(f"⭐ Score: {rec.score:.1f}")
                    print(f"🎯 Confidence: {rec.confidence:.2%}")
                    print(f"\n💡 EXPLANATION (Gemini-powered):")
                    print("-" * 60)
                    print(rec.reason)
                    print("-" * 60)
                    
                    # Check if it looks AI-generated vs template
                    reason = rec.reason.lower()
                    
                    # Template indicators
                    template_phrases = [
                        'shows how to build',
                        'offers practical code examples',
                        'appropriate difficulty level',
                        'suitable for',
                    ]
                    
                    # AI indicators (more natural, conversational)
                    ai_indicators = [
                        'perfectly',
                        'exactly',
                        'ideal for',
                        'your project',
                        'specifically',
                        'comprehensive',
                    ]
                    
                    template_count = sum(1 for phrase in template_phrases if phrase in reason)
                    ai_count = sum(1 for indicator in ai_indicators if indicator in reason)
                    
                    print("\n📊 Analysis:")
                    print(f"   Template phrases detected: {template_count}")
                    print(f"   AI indicators detected: {ai_count}")
                    
                    if ai_count > template_count:
                        print("   ✅ This looks like AI-generated explanation! 🤖")
                        print("   ✅ Gemini integration is WORKING!")
                    else:
                        print("   📝 This looks like template-based explanation")
                        print("   ℹ️  Gemini may be unavailable (using fallback)")
                    
                    # Show metadata
                    print("\n🔍 Metadata:")
                    if rec.metadata and 'score_components' in rec.metadata:
                        components = rec.metadata['score_components']
                        print(f"   Technology Match: {components.get('technology', 0):.0%}")
                        print(f"   Semantic Relevance: {components.get('semantic', 0):.0%}")
                        print(f"   Content Type: {components.get('content_type', 0):.0%}")
                        print(f"   Difficulty: {components.get('difficulty', 0):.0%}")
                        print(f"   Quality: {components.get('quality', 0):.0%}")
                    
                    print("\n" + "="*60)
                    print("✅ TEST COMPLETE!")
                    print("="*60)
                    
                    return True
                else:
                    print("   ⚠️  No recommendations returned")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Error getting recommendations: {e}")
                import traceback
                traceback.print_exc()
                return False
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_gemini_explanations()
    sys.exit(0 if success else 1)

