#!/usr/bin/env python3
"""
Comprehensive Recommendation Cache Clearing Script
Based on cache structure analysis from the codebase
"""

import os
import sys
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def clear_recommendation_cache_comprehensive():
    """Clear all recommendation caches comprehensively"""
    
    print("🔍 Analyzing cache structure...")
    
    try:
        # Import required modules
        from redis_utils import redis_cache
        from cache_invalidation_service import CacheInvalidationService
        
        if not redis_cache.connected:
            print("❌ Redis not connected. Cannot clear cache.")
            return False
        
        print("✅ Redis connected successfully")
        
        # Get current cache stats before clearing
        print("\n📊 Current cache status:")
        try:
            all_keys = redis_cache.redis_client.keys('*')
            recommendation_keys = [key for key in all_keys if b'recommendation' in key or b'unified_recommendations' in key]
            
            print(f"   Total Redis keys: {len(all_keys)}")
            print(f"   Recommendation-related keys: {len(recommendation_keys)}")
            
            if recommendation_keys:
                print("\n🔍 Found recommendation cache keys:")
                for key in recommendation_keys[:10]:  # Show first 10
                    print(f"   {key.decode()}")
                if len(recommendation_keys) > 10:
                    print(f"   ... and {len(recommendation_keys) - 10} more")
        except Exception as e:
            print(f"   ⚠️ Could not get current cache stats: {e}")
        
        print("\n🧹 Starting comprehensive cache clearing...")
        
        # Method 1: Use the built-in cache invalidation service
        print("\n1️⃣ Using CacheInvalidationService.invalidate_all_recommendations()...")
        try:
            result = CacheInvalidationService.invalidate_all_recommendations()
            if result:
                print("   ✅ Successfully invalidated all recommendations via service")
            else:
                print("   ❌ Failed to invalidate via service")
        except Exception as e:
            print(f"   ❌ Error using service: {e}")
        
        # Method 2: Use redis_utils directly
        print("\n2️⃣ Using redis_cache.invalidate_all_recommendations()...")
        try:
            result = redis_cache.invalidate_all_recommendations()
            if result:
                print("   ✅ Successfully invalidated all recommendations via redis_utils")
            else:
                print("   ❌ Failed to invalidate via redis_utils")
        except Exception as e:
            print(f"   ❌ Error using redis_utils: {e}")
        
        # Method 3: Manual pattern-based deletion for specific recommendation types
        print("\n3️⃣ Manual pattern-based deletion...")
        
        # Define all recommendation cache patterns found in the codebase
        recommendation_patterns = [
            "*recommendations:*",
            "*smart_recommendations:*", 
            "*enhanced_recommendations:*",
            "*unified_recommendations:*",
            "*gemini_enhanced_recommendations:*",
            "*project_recommendations:*",
            "*task_recommendations:*",
            "*learning_path_recommendations:*",
            "*unified_project_recommendations:*",
            "*context_extraction:*",
            "*ensemble_recommendations:*",
            "*quality_recommendations:*",
            "*fast_recommendations:*",
            "*context_aware_recommendations:*"
        ]
        
        total_deleted = 0
        for pattern in recommendation_patterns:
            try:
                deleted_count = redis_cache.delete_keys_pattern(pattern)
                if deleted_count > 0:
                    print(f"   ✅ Deleted {deleted_count} keys matching '{pattern}'")
                    total_deleted += deleted_count
                else:
                    print(f"   ℹ️  No keys found matching '{pattern}'")
            except Exception as e:
                print(f"   ❌ Error deleting pattern '{pattern}': {e}")
        
        # Method 4: Clear specific user recommendation caches (if user_id provided)
        print("\n4️⃣ Clearing specific user recommendation caches...")
        try:
            # Clear for user 1 (your test user)
            user_id = 1
            result = redis_cache.invalidate_user_recommendations(user_id)
            if result:
                print(f"   ✅ Successfully invalidated recommendations for user {user_id}")
            else:
                print(f"   ℹ️  No recommendations found for user {user_id}")
        except Exception as e:
            print(f"   ❌ Error clearing user recommendations: {e}")
        
        # Method 5: Clear intent analysis cache
        print("\n5️⃣ Clearing intent analysis cache...")
        try:
            intent_patterns = [
                "*intent_analysis:*",
                "*user_intent:*",
                "*context_analysis:*"
            ]
            
            for pattern in intent_patterns:
                deleted_count = redis_cache.delete_keys_pattern(pattern)
                if deleted_count > 0:
                    print(f"   ✅ Deleted {deleted_count} keys matching '{pattern}'")
                    total_deleted += deleted_count
        except Exception as e:
            print(f"   ❌ Error clearing intent cache: {e}")
        
        # Method 6: Clear embedding cache (which affects recommendations)
        print("\n6️⃣ Clearing embedding cache...")
        try:
            embedding_patterns = [
                "*embedding:*",
                "*content_embedding:*",
                "*project_embedding:*",
                "*user_embedding:*"
            ]
            
            for pattern in embedding_patterns:
                deleted_count = redis_cache.delete_keys_pattern(pattern)
                if deleted_count > 0:
                    print(f"   ✅ Deleted {deleted_count} keys matching '{pattern}'")
                    total_deleted += deleted_count
        except Exception as e:
            print(f"   ❌ Error clearing embedding cache: {e}")
        
        # Method 7: Clear analysis cache (which affects content scoring)
        print("\n7️⃣ Clearing analysis cache...")
        try:
            analysis_patterns = [
                "*content_analysis:*",
                "*analysis_data:*",
                "*user_analysis:*",
                "*project_analysis:*"
            ]
            
            for pattern in analysis_patterns:
                deleted_count = redis_cache.delete_keys_pattern(pattern)
                if deleted_count > 0:
                    print(f"   ✅ Deleted {deleted_count} keys matching '{pattern}'")
                    total_deleted += deleted_count
        except Exception as e:
            print(f"   ❌ Error clearing analysis cache: {e}")
        
        # Final verification
        print("\n🔍 Final cache verification...")
        try:
            remaining_keys = redis_cache.redis_client.keys('*')
            remaining_recommendation_keys = [key for key in remaining_keys if b'recommendation' in key or b'unified_recommendations' in key]
            
            print(f"   Remaining total keys: {len(remaining_keys)}")
            print(f"   Remaining recommendation keys: {len(remaining_recommendation_keys)}")
            
            if remaining_recommendation_keys:
                print("\n⚠️  Remaining recommendation cache keys:")
                for key in remaining_recommendation_keys:
                    print(f"   {key.decode()}")
            else:
                print("   ✅ All recommendation cache keys cleared successfully!")
                
        except Exception as e:
            print(f"   ❌ Could not verify final cache status: {e}")
        
        print(f"\n🎯 Cache clearing completed!")
        print(f"   Total keys deleted: {total_deleted}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_specific_user_cache(user_id: int):
    """Clear cache for a specific user"""
    try:
        from redis_utils import redis_cache
        
        if not redis_cache.connected:
            print("❌ Redis not connected")
            return False
        
        print(f"🧹 Clearing cache for user {user_id}...")
        
        # Clear user-specific recommendation cache
        result = redis_cache.invalidate_user_recommendations(user_id)
        
        # Clear specific patterns for this user
        user_patterns = [
            f"*unified_recommendations:*{user_id}*",
            f"*unified_project_recommendations:*{user_id}*",
            f"*context_extraction:*{user_id}*",
            f"*user_profile:{user_id}*",
            f"*user_context:{user_id}*",
            f"*user_bookmarks:{user_id}*"
        ]
        
        total_deleted = 0
        for pattern in user_patterns:
            deleted_count = redis_cache.delete_keys_pattern(pattern)
            if deleted_count > 0:
                print(f"   ✅ Deleted {deleted_count} keys matching '{pattern}'")
                total_deleted += deleted_count
        
        print(f"✅ User {user_id} cache cleared. Total keys deleted: {total_deleted}")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing user cache: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Comprehensive Recommendation Cache Clearing Tool")
    print("=" * 60)
    
    # Clear all recommendation caches
    success = clear_recommendation_cache_comprehensive()
    
    if success:
        print("\n✅ Cache clearing completed successfully!")
        
        # Optionally clear specific user cache
        user_input = input("\n🤔 Clear cache for specific user? (Enter user ID or 'n' to skip): ").strip()
        if user_input.lower() != 'n' and user_input.isdigit():
            user_id = int(user_input)
            clear_specific_user_cache(user_id)
    else:
        print("\n❌ Cache clearing failed!")
    
    print("\n🎯 All done! Your recommendation system will now generate fresh results.")
