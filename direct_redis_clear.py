#!/usr/bin/env python3
"""
Direct Redis Clear - Connect directly to Redis and clear it
"""

def clear_redis_direct():
    """Clear Redis by connecting directly"""
    print("🧹 Connecting directly to Redis on localhost:6379...")
    
    try:
        import redis
        
        # Connect directly to Redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=5)
        
        # Test connection
        r.ping()
        print("   ✅ Connected to Redis successfully")
        
        # Get all keys
        all_keys = r.keys('*')
        print(f"   📊 Found {len(all_keys)} keys to clear")
        
        if all_keys:
            # Show some sample keys
            sample_keys = all_keys[:10]
            print(f"   📋 Sample keys: {[key.decode('utf-8') if isinstance(key, bytes) else key for key in sample_keys]}")
            
            # Clear all keys
            r.flushall()
            print(f"   ✅ Cleared all {len(all_keys)} Redis keys")
            
            # Verify
            remaining_keys = r.keys('*')
            if not remaining_keys:
                print("   ✅ VERIFIED: Redis is completely empty")
                return True
            else:
                print(f"   ❌ FAILED: Redis still has {len(remaining_keys)} keys")
                return False
        else:
            print("   ✅ Redis already empty")
            return True
            
    except ImportError:
        print("   ❌ Redis package not available")
        print("   💡 Install with: pip install redis")
        return False
    except Exception as e:
        print(f"   ❌ Redis clear failed: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Direct Redis Clear")
    print("=" * 30)
    
    if clear_redis_direct():
        print("\n🎉 SUCCESS! Redis is completely cleared!")
        print("\n💡 Next steps:")
        print("   1. Restart your Flask application")
        print("   2. All recommendation caches are now fresh")
        print("   3. Test with a new recommendation request")
    else:
        print("\n❌ Failed to clear Redis")
        print("\n💡 Manual options:")
        print("   1. Install redis package: pip install redis")
        print("   2. Check Redis connection")
        print("   3. Use redis-cli flushall if available")

if __name__ == "__main__":
    main()
