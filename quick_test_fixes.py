#!/usr/bin/env python3
"""
Quick test script to verify fixes work within Flask app context
"""

def test_fixes():
    """Test the fixes we implemented"""
    print("🧪 Testing Fixes Within Flask Context")
    print("=" * 50)
    
    try:
        # Test 1: Check if FastSemanticEngine has the required method
        print("\n📊 Test 1: Checking FastSemanticEngine methods...")
        
        # Import within Flask context
        from unified_recommendation_orchestrator import FastSemanticEngine, UnifiedDataLayer
        
        # Test data layer
        data_layer = UnifiedDataLayer()
        print("✅ UnifiedDataLayer initialized")
        
        # Test database session method
        db_session = data_layer.get_db_session()
        if db_session:
            print("✅ Database session method working")
        else:
            print("❌ Database session method failed")
            return False
        
        # Test engine initialization
        engine = FastSemanticEngine(data_layer)
        print("✅ FastSemanticEngine initialized")
        
        # Test if the method exists
        if hasattr(engine, '_calculate_technology_overlap'):
            print("✅ _calculate_technology_overlap method exists")
        else:
            print("❌ _calculate_technology_overlap method missing")
            return False
        
        # Test method functionality
        test_techs = ['python', 'django']
        content_techs = ['python', 'flask']
        overlap = engine._calculate_technology_overlap(content_techs, test_techs)
        print(f"✅ Technology overlap calculation working: {overlap:.3f}")
        
        print("\n🎉 All tests passed! Your fixes are working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_fixes()
