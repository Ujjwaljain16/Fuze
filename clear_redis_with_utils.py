#!/usr/bin/env python3
"""
Clear Redis using existing redis_utils
"""

def clear_redis_with_utils():
    """Clear Redis using the existing redis_utils"""
    print("🧹 Clearing Redis using redis_utils...")
    
    try:
        from redis_utils import redis_cache
        
        if redis_cache.connected and redis_cache.redis_client:
            print("   ✅ Connected to Redis via redis_utils")
            
            # Get all keys
            all_keys = redis_cache.redis_client.keys('*')
            print(f"   📊 Found {len(all_keys)} keys to clear")
            
            if all_keys:
                # Clear all keys
                redis_cache.redis_client.flushall()
                print(f"   ✅ Cleared all {len(all_keys)} Redis keys")
                
                # Verify
                remaining_keys = redis_cache.redis_client.keys('*')
                if not remaining_keys:
                    print("   ✅ VERIFIED: Redis is completely empty")
                    return True
                else:
                    print(f"   ❌ FAILED: Redis still has {len(remaining_keys)} keys")
                    return False
            else:
                print("   ✅ Redis already empty")
                return True
        else:
            print("   ❌ Redis not connected via redis_utils")
            return False
            
    except ImportError:
        print("   ❌ redis_utils not available")
        return False
    except Exception as e:
        print(f"   ❌ Redis clear failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Redis Clear using redis_utils")
    print("=" * 40)
    
    if clear_redis_with_utils():
        print("\n🎉 SUCCESS! Redis is completely cleared!")
        print("\n💡 Next steps:")
        print("   1. Restart your Flask application")
        print("   2. All recommendation caches are now fresh")
        print("   3. Test with a new recommendation request")
    else:
        print("\n❌ Failed to clear Redis")
        print("\n💡 Manual options:")
        print("   1. Check if Redis is running")
        print("   2. Restart Redis service")
        print("   3. Use redis-cli flushall if available")

if __name__ == "__main__":
    main()
