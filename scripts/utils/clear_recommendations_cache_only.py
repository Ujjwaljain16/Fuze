#!/usr/bin/env python3
"""
Clear ONLY Recommendations and Intent Caches
===========================================
Clears recommendation and intent analysis caches while preserving everything else.
Perfect for testing fresh recommendations!
"""

import sys

def clear_recommendation_caches():
    """Clear only recommendation-related caches"""
    print("🧹 Clearing Recommendation & Intent Caches Only")
    print("=" * 60)
    
    try:
        import redis
        
        # Connect to Redis directly
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=5)
            redis_client.ping()
            print("   ✅ Connected to Redis")
        except Exception as e:
            print(f"   ⚠️  Trying alternative connection...")
            redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True, socket_connect_timeout=5)
            redis_client.ping()
            print("   ✅ Connected to Redis (127.0.0.1)")
        
        if redis_client:
            
            # Patterns to clear
            patterns = [
                'unified_recommendations:*',        # Unified orchestrator cache
                'unified_recommendations_intent:*', # Unified orchestrator WITH intent cache (THE MAIN ONE!)
                'intent_analysis:*',                # Intent analysis cache
                'recommendation:*',                 # Generic recommendation cache
                'intent:*',                         # Generic intent cache
                'project_intent:*',                 # Project intent cache
                'user_recommendations:*',           # User-specific recommendation cache
            ]
            
            total_deleted = 0
            
            for pattern in patterns:
                try:
                    # Find matching keys
                    keys = redis_client.keys(pattern)
                    
                    if keys:
                        # Delete them
                        deleted = redis_client.delete(*keys)
                        total_deleted += deleted
                        print(f"   ✅ Cleared {deleted} keys matching '{pattern}'")
                    else:
                        print(f"   ℹ️  No keys found for '{pattern}'")
                        
                except Exception as e:
                    print(f"   ⚠️  Error with pattern '{pattern}': {e}")
            
            print("\n" + "=" * 60)
            print(f"🎉 Total keys cleared: {total_deleted}")
            print("=" * 60)
            
            if total_deleted > 0:
                print("\n✅ Recommendation & Intent caches cleared successfully!")
                print("📊 All other caches (embeddings, user data, etc.) preserved")
                print("\n🚀 Ready for fresh testing!")
            else:
                print("\nℹ️  No recommendation caches found (already clear)")
            
            return True
            
    except ImportError:
        print("❌ Redis package not installed")
        print("💡 Install: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Error clearing caches: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_cache_status():
    """Check what's left in Redis"""
    print("\n" + "=" * 60)
    print("📊 Verifying Cache Status")
    print("=" * 60)
    
    try:
        import redis
        
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        if redis_client:
            
            # Check recommendation caches
            rec_keys = redis_client.keys('unified_recommendations:*')
            intent_keys = redis_client.keys('intent*')
            all_keys = redis_client.keys('*')
            
            print(f"   Recommendation caches: {len(rec_keys)} keys")
            print(f"   Intent caches: {len(intent_keys)} keys")
            print(f"   Total Redis keys: {len(all_keys)} keys")
            
            if len(rec_keys) == 0 and len(intent_keys) == 0:
                print("\n   ✅ Recommendation & Intent caches are CLEAR!")
            
            if len(all_keys) > 0:
                print(f"\n   ℹ️  Other caches preserved: {len(all_keys)} keys")
            
        else:
            print("   ⚠️  Cannot verify - Redis not available")
            
    except Exception as e:
        print(f"   ⚠️  Verification error: {e}")


def main():
    """Main function"""
    print("\n" + "🎯" * 30)
    print("TARGETED CACHE CLEARING - RECOMMENDATIONS & INTENTS ONLY")
    print("🎯" * 30 + "\n")
    
    # Clear the caches
    success = clear_recommendation_caches()
    
    if success:
        # Verify what's left
        verify_cache_status()
        
        print("\n" + "=" * 60)
        print("✅ DONE! Ready to test fresh recommendations")
        print("=" * 60)
        print("\n📝 What was cleared:")
        print("   ✅ All recommendation caches")
        print("   ✅ All intent analysis caches")
        print("\n📝 What was preserved:")
        print("   ✅ User session data")
        print("   ✅ Embedding caches")
        print("   ✅ Authentication tokens")
        print("   ✅ All other application data")
        
        print("\n🚀 Next steps:")
        print("   1. Your Flask server is still running")
        print("   2. Refresh your frontend")
        print("   3. Request recommendations - they'll be freshly generated!")
        print("   4. Performance: First request ~5s, then cached <100ms")
        
        return 0
    else:
        print("\n❌ Cache clearing failed")
        print("💡 Try: python clear_all_caches.py (clears everything)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

