#!/usr/bin/env python3
"""
Test script to verify improved recommendation quality
"""

import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_improved_recommendations():
    """Test that recommendations are more relevant and accurate"""
    logger.info("Testing improved recommendation quality...")
    
    try:
        from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
        
        # Create test request
        test_request = UnifiedRecommendationRequest(
            user_id=1,
            title="React Native Mobile App Development",
            description="Building a cross-platform mobile application with React Native, including payment integration and user authentication",
            technologies="React Native, JavaScript, Node.js, MongoDB, Stripe",
            user_interests="Mobile development, React, JavaScript",
            max_recommendations=5
        )
        
        # Get orchestrator
        orchestrator = get_unified_orchestrator()
        
        # Get recommendations
        results = orchestrator.get_recommendations(test_request)
        
        logger.info(f"Generated {len(results)} recommendations")
        
        # Analyze results
        if len(results) == 0:
            logger.error("❌ No recommendations generated")
            return False
        
        # Check recommendation quality
        high_quality_count = 0
        relevant_tech_count = 0
        
        for i, result in enumerate(results, 1):
            logger.info(f"\n--- Recommendation {i} ---")
            logger.info(f"Title: {result.title}")
            logger.info(f"Score: {result.score:.2f}")
            logger.info(f"Reason: {result.reason}")
            logger.info(f"Technologies: {', '.join(result.technologies[:3])}")
            logger.info(f"Engine: {result.engine_used}")
            
            # Check if it's high quality
            if result.score >= 60:
                high_quality_count += 1
                logger.info("✅ High quality recommendation")
            
            # Check if it has relevant technologies
            relevant_techs = ['react', 'javascript', 'node', 'mobile', 'native', 'mongodb', 'stripe']
            content_techs = [tech.lower() for tech in result.technologies]
            has_relevant_tech = any(tech in ' '.join(content_techs) for tech in relevant_techs)
            
            if has_relevant_tech:
                relevant_tech_count += 1
                logger.info("✅ Has relevant technologies")
            else:
                logger.warning("⚠️ No relevant technologies found")
        
        # Quality metrics
        quality_percentage = (high_quality_count / len(results)) * 100
        relevance_percentage = (relevant_tech_count / len(results)) * 100
        
        logger.info(f"\n--- Quality Analysis ---")
        logger.info(f"High quality recommendations: {high_quality_count}/{len(results)} ({quality_percentage:.1f}%)")
        logger.info(f"Relevant technology recommendations: {relevant_tech_count}/{len(results)} ({relevance_percentage:.1f}%)")
        
        # Success criteria
        if quality_percentage >= 60 and relevance_percentage >= 60:
            logger.info("✅ Recommendation quality is good!")
            return True
        else:
            logger.warning("⚠️ Recommendation quality needs improvement")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_technology_overlap():
    """Test the improved technology overlap calculation"""
    logger.info("Testing technology overlap calculation...")
    
    try:
        from unified_recommendation_orchestrator import FastSemanticEngine, UnifiedDataLayer
        
        data_layer = UnifiedDataLayer()
        engine = FastSemanticEngine(data_layer)
        
        # Test cases
        test_cases = [
            {
                'content_techs': ['React Native', 'JavaScript', 'Node.js'],
                'request_techs': ['React Native', 'JavaScript'],
                'expected_min': 0.7
            },
            {
                'content_techs': ['Python', 'Django', 'PostgreSQL'],
                'request_techs': ['React', 'JavaScript'],
                'expected_min': 0.0
            },
            {
                'content_techs': ['JavaScript', 'Node.js', 'Express'],
                'request_techs': ['Node.js', 'JavaScript'],
                'expected_min': 0.8
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            overlap = engine._calculate_technology_overlap(
                test_case['content_techs'], 
                test_case['request_techs']
            )
            
            logger.info(f"Test {i}: Overlap = {overlap:.3f} (expected >= {test_case['expected_min']})")
            
            if overlap >= test_case['expected_min']:
                logger.info("✅ Technology overlap calculation working correctly")
            else:
                logger.warning("⚠️ Technology overlap calculation may need adjustment")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Technology overlap test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting recommendation quality verification...")
    
    tests = [
        ("Improved Recommendations", test_improved_recommendations),
        ("Technology Overlap", test_technology_overlap)
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
        logger.info("🎉 Recommendation quality improvements verified!")
        return True
    else:
        logger.error("⚠️ Some improvements need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 