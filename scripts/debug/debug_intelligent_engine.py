#!/usr/bin/env python3
"""
Debug script to test intelligent engine initialization and method calls
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_intelligent_engine():
    """Test intelligent engine initialization and method calls"""
    try:
        print("🧠 Testing Intelligent Engine Initialization...")
        
        # Test import
        from intelligent_recommendation_engine import IntelligentRecommendationEngine
        print("✅ Import successful")
        
        # Test initialization
        engine = IntelligentRecommendationEngine()
        print("✅ Engine initialization successful")
        
        # Test attributes
        print(f"Engine type: {type(engine)}")
        print(f"Has context_analyzer: {hasattr(engine, 'context_analyzer')}")
        print(f"Context analyzer type: {type(engine.context_analyzer)}")
        print(f"Has analyze_user_input: {hasattr(engine.context_analyzer, 'analyze_user_input')}")
        
        # Test method call
        print("\n🧠 Testing analyze_user_input method...")
        analysis = engine.context_analyzer.analyze_user_input(
            title="Test Project",
            description="A test project description",
            technologies="python,flask",
            user_interests="web development"
        )
        print("✅ Method call successful")
        print(f"Analysis type: {type(analysis)}")
        print(f"Primary intent: {analysis.primary_intent}")
        print(f"Domain: {analysis.domain}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_unified_orchestrator():
    """Test unified orchestrator intelligent engine integration"""
    try:
        print("\n🎯 Testing Unified Orchestrator Integration...")
        
        # Test import
        from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator
        print("✅ Import successful")
        
        # Test initialization
        orchestrator = UnifiedRecommendationOrchestrator()
        print("✅ Orchestrator initialization successful")
        
        # Test intelligent engine
        print(f"Intelligent engine available: {orchestrator.intelligent_engine_available}")
        if orchestrator.intelligent_engine:
            print(f"Intelligent engine type: {type(orchestrator.intelligent_engine)}")
            print(f"Has context_analyzer: {hasattr(orchestrator.intelligent_engine, 'context_analyzer')}")
            if orchestrator.intelligent_engine.context_analyzer:
                print(f"Context analyzer type: {type(orchestrator.intelligent_engine.context_analyzer)}")
                print(f"Has analyze_user_input: {hasattr(orchestrator.intelligent_engine.context_analyzer, 'analyze_user_input')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Debugging Intelligent Engine Issues\n")
    
    # Test 1: Direct intelligent engine
    success1 = test_intelligent_engine()
    
    # Test 2: Unified orchestrator integration
    success2 = test_unified_orchestrator()
    
    print(f"\n📊 Results:")
    print(f"Intelligent Engine: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Unified Orchestrator: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The intelligent engine should work correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")
