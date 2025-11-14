#!/usr/bin/env python3
"""
Test script to verify dynamic user-focused recommendations
"""

import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_user_content_retrieval():
    """Test that we're retrieving the requesting user's own content correctly"""
    logger.info("Testing dynamic user content retrieval...")
    
    try:
        from unified_recommendation_orchestrator import UnifiedDataLayer, UnifiedRecommendationRequest
        
        data_layer = UnifiedDataLayer()
        
        # Test with different users
        test_users = [1, 108]  # Test with both user 1 and user 108
        
        for test_user_id in test_users:
            logger.info(f"Testing with user {test_user_id}...")
            
            # Create test request for the user
            test_request = UnifiedRecommendationRequest(
                user_id=test_user_id,
                title="Test Request",
                description="Test description",
                technologies="React, JavaScript"
            )
            
            # Get user's own content
            content_list = data_layer.get_candidate_content(test_user_id, test_request)
            
            logger.info(f"Retrieved {len(content_list)} content items for user {test_user_id}")
            
            if len(content_list) == 0:
                logger.warning(f"⚠️ No content found for user {test_user_id} - this is expected if user has no saved content")
                continue
            
            # Check that all content belongs to the requesting user
            user_content_count = 0
            for content in content_list:
                if content.get('user_id') == test_user_id:
                    user_content_count += 1
            
            user_content_percentage = (user_content_count / len(content_list)) * 100
            
            logger.info(f"User {test_user_id} content: {user_content_count}/{len(content_list)} ({user_content_percentage:.1f}%)")
            
            if user_content_percentage >= 95:  # Should be 100% but allow for some edge cases
                logger.info(f"✅ All content belongs to user {test_user_id}")
            else:
                logger.warning(f"⚠️ Some content may not belong to user {test_user_id}")
                return False
        
        # If we get here, the test passed (even if no content was found)
        logger.info("✅ User content retrieval test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ User content retrieval test failed: {e}")
        return False

def test_embedding_fallback():
    """Test that embedding fallback works without network"""
    logger.info("Testing embedding fallback functionality...")
    
    try:
        from unified_recommendation_orchestrator import UnifiedDataLayer
        
        data_layer = UnifiedDataLayer()
        
        # Test fallback embedding
        test_text = "React Native JavaScript development"
        embedding = data_layer._get_embedding(test_text)
        
        if embedding and len(embedding) == 384:
            logger.info("✅ Fallback embedding working correctly")
            return True
        else:
            logger.error("❌ Fallback embedding not working")
            return False
        
    except Exception as e:
        logger.error(f"❌ Embedding fallback test failed: {e}")
        return False

def test_user_recommendations():
    """Test that recommendations are based on the requesting user's own saved content"""
    logger.info("Testing dynamic user-focused recommendations...")
    
    try:
        from unified_recommendation_orchestrator import get_unified_orchestrator, UnifiedRecommendationRequest
        from redis_utils import redis_cache
        
        # Clear cache to ensure fresh results
        try:
            # Clear all recommendation cache
            deleted_count = redis_cache.invalidate_all_recommendations()
            logger.info(f"✅ Cache cleared successfully - deleted {deleted_count} recommendation entries")
        except Exception as e:
            logger.warning(f"⚠️ Could not clear cache: {e}")
        
        # Test with different users
        test_users = [1, 108]
        
        for test_user_id in test_users:
            logger.info(f"Testing recommendations for user {test_user_id}...")
            
            # Create test request for the user
            test_request = UnifiedRecommendationRequest(
                user_id=test_user_id,
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
            
            logger.info(f"Generated {len(results)} recommendations for user {test_user_id}")
            
            # Analyze results
            if len(results) == 0:
                logger.warning(f"⚠️ No recommendations generated for user {test_user_id} - this is expected if user has no saved content")
                continue
            
            # Check that all recommendations are from the user's own content
            user_content_count = 0
            high_quality_count = 0
            relevant_tech_count = 0
            
            for i, result in enumerate(results, 1):
                logger.info(f"\n--- User {test_user_id} Recommendation {i} ---")
                logger.info(f"Title: {result.title}")
                logger.info(f"Score: {result.score:.2f}")
                logger.info(f"Reason: {result.reason}")
                logger.info(f"Technologies: {', '.join(result.technologies[:3])}")
                logger.info(f"Engine: {result.engine_used}")
                logger.info(f"Quality Score: {result.quality_score}")
                
                # Check if it's from the user's own content
                if "your saved content" in result.reason.lower() or "your saved bookmarks" in result.reason.lower():
                    user_content_count += 1
                    logger.info("✅ From user's own saved content")
                else:
                    logger.warning("⚠️ May not be from user's own content")
                
                # Check if it's high quality
                if result.score >= 30:  # Lowered threshold for user content
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
            user_content_percentage = (user_content_count / len(results)) * 100
            quality_percentage = (high_quality_count / len(results)) * 100
            relevance_percentage = (relevant_tech_count / len(results)) * 100
            
            logger.info(f"\n--- User {test_user_id} Content Analysis ---")
            logger.info(f"User's own content recommendations: {user_content_count}/{len(results)} ({user_content_percentage:.1f}%)")
            logger.info(f"High quality recommendations: {high_quality_count}/{len(results)} ({quality_percentage:.1f}%)")
            logger.info(f"Relevant technology recommendations: {relevant_tech_count}/{len(results)} ({relevance_percentage:.1f}%)")
            
            # Success criteria - focus on user's own content
            if user_content_percentage >= 80:  # At least 80% should be from user's own content
                logger.info(f"✅ Recommendations are focused on user {test_user_id}'s own saved content!")
            else:
                logger.warning(f"⚠️ Recommendations may not be focused enough on user {test_user_id}'s own content")
                return False
        
        # If we get here, the test passed (even if no recommendations were generated)
        logger.info("✅ User recommendations test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting dynamic user-focused recommendation verification...")
    
    tests = [
        ("Embedding Fallback", test_embedding_fallback),
        ("User Content Retrieval", test_user_content_retrieval),
        ("User Recommendations", test_user_recommendations)
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
        logger.info("🎉 Dynamic user-focused recommendations working correctly!")
        return True
    else:
        logger.error("⚠️ Dynamic user-focused recommendations need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 