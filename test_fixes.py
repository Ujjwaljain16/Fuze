#!/usr/bin/env python3
"""
Test script to verify fixes for technologies KeyError and meta tensor issues
"""

import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_embedding_model_fix():
    """Test that embedding models initialize without meta tensor errors"""
    logger.info("Testing embedding model initialization...")
    
    try:
        # Test unified recommendation orchestrator
        from unified_recommendation_orchestrator import UnifiedDataLayer
        data_layer = UnifiedDataLayer()
        logger.info("✅ UnifiedDataLayer embedding model initialized successfully")
        
        # Test unified recommendation engine
        from unified_recommendation_engine import UnifiedRecommendationEngine
        unified_engine = UnifiedRecommendationEngine()
        logger.info("✅ UnifiedRecommendationEngine embedding model initialized successfully")
        
        # Test enhanced recommendation engine
        from enhanced_recommendation_engine import ContentAnalyzer
        content_analyzer = ContentAnalyzer()
        logger.info("✅ ContentAnalyzer embedding model initialized successfully")
        
        # Test enhanced diversity engine
        from enhanced_diversity_engine import EnhancedDiversityEngine
        diversity_engine = EnhancedDiversityEngine()
        logger.info("✅ EnhancedDiversityEngine embedding model initialized successfully")
        
        # Test AI recommendation engine
        from ai_recommendation_engine import SmartRecommendationEngine
        smart_engine = SmartRecommendationEngine()
        logger.info("✅ SmartRecommendationEngine embedding model initialized successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Embedding model initialization failed: {e}")
        return False

def test_technologies_field_fix():
    """Test that content normalization includes technologies field"""
    logger.info("Testing technologies field normalization...")
    
    try:
        from unified_recommendation_orchestrator import UnifiedDataLayer
        from models import SavedContent, ContentAnalysis
        
        data_layer = UnifiedDataLayer()
        
        # Create mock content and analysis
        mock_content = SavedContent(
            id=1,
            title="Test Content",
            url="https://example.com",
            extracted_text="This is test content about Python and React",
            tags="python,react,web",
            quality_score=8,
            user_id=1,
            saved_at=datetime.utcnow()
        )
        
        mock_analysis = ContentAnalysis(
            content_id=1,
            technology_tags="python,react,javascript",
            content_type="tutorial",
            difficulty_level="intermediate",
            key_concepts="web development,frontend,backend"
        )
        
        # Test normalization
        normalized = data_layer.normalize_content_data(mock_content, mock_analysis)
        
        # Check that technologies field exists and is a list
        if 'technologies' not in normalized:
            logger.error("❌ Technologies field missing from normalized content")
            return False
        
        if not isinstance(normalized['technologies'], list):
            logger.error("❌ Technologies field is not a list")
            return False
        
        if len(normalized['technologies']) == 0:
            logger.error("❌ Technologies field is empty")
            return False
        
        logger.info(f"✅ Technologies field normalized correctly: {normalized['technologies']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Technologies field normalization failed: {e}")
        return False

def test_safe_field_access():
    """Test that engines handle missing fields safely"""
    logger.info("Testing safe field access...")
    
    try:
        from unified_recommendation_orchestrator import FastSemanticEngine, UnifiedDataLayer, UnifiedRecommendationRequest
        
        data_layer = UnifiedDataLayer()
        engine = FastSemanticEngine(data_layer)
        
        # Create content with missing fields
        content_with_missing_fields = {
            'id': 1,
            'title': 'Test Content',
            'url': 'https://example.com',
            'extracted_text': 'Test content',
            # Missing technologies, content_type, difficulty, etc.
        }
        
        # Create request
        request = UnifiedRecommendationRequest(
            user_id=1,
            title="Test Request",
            description="Test description",
            technologies="python,react"
        )
        
        # This should not raise KeyError
        try:
            result = engine.get_recommendations([content_with_missing_fields], request)
            logger.info("✅ Safe field access works correctly")
            return True
        except KeyError as e:
            logger.error(f"❌ KeyError still occurs: {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Safe field access test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting fix verification tests...")
    
    tests = [
        ("Embedding Model Fix", test_embedding_model_fix),
        ("Technologies Field Fix", test_technologies_field_fix),
        ("Safe Field Access", test_safe_field_access)
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
        logger.info("🎉 All fixes verified successfully!")
        return True
    else:
        logger.error("⚠️ Some fixes need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 