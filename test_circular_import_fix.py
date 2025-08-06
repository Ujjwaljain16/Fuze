#!/usr/bin/env python3
"""
Test script to verify that the circular import issue is resolved
"""

import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_circular_import_fix():
    """Test that the circular import issue is resolved"""
    logger.info("Testing circular import fix...")
    
    try:
        # Test importing the unified orchestrator
        from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
        logger.info("✅ Successfully imported get_unified_orchestrator")
        
        # Test importing the recommendations blueprint
        from blueprints.recommendations import init_engines
        logger.info("✅ Successfully imported recommendations blueprint")
        
        # Test that we can get the orchestrator instance
        orchestrator = get_unified_orchestrator()
        logger.info("✅ Successfully created orchestrator instance")
        
        # Test that we can create a request
        request = UnifiedRecommendationRequest(
            user_id=1,
            title="Test Request",
            description="Test description",
            technologies="python,react"
        )
        logger.info("✅ Successfully created UnifiedRecommendationRequest")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_app_context_management():
    """Test that app context management works without circular imports"""
    logger.info("Testing app context management...")
    
    try:
        from unified_recommendation_orchestrator import UnifiedDataLayer, UnifiedRecommendationRequest
        
        # Create data layer
        data_layer = UnifiedDataLayer()
        logger.info("✅ Successfully created UnifiedDataLayer")
        
        # Create request
        request = UnifiedRecommendationRequest(
            user_id=1,
            title="Test Request",
            description="Test description",
            technologies="python,react"
        )
        
        # Test getting candidate content (this uses app context internally)
        content_list = data_layer.get_candidate_content(1, request)
        logger.info(f"✅ Successfully got candidate content: {len(content_list)} items")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ App context management error: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting circular import fix verification...")
    
    tests = [
        ("Circular Import Fix", test_circular_import_fix),
        ("App Context Management", test_app_context_management)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 Circular import issue resolved successfully!")
        return True
    else:
        logger.error("⚠️ Circular import issue still needs attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 