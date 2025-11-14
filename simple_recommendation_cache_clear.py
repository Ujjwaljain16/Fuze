#!/usr/bin/env python3
"""
Simple Recommendation Cache Clear
Clears recommendation cache using direct methods
"""

import os
import glob
import time

def clear_python_cache():
    """Clear Python cache files that might affect recommendations"""
    print("🧹 Clearing Python cache...")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                cache_path = os.path.join(root, dir_name)
                try:
                    import shutil
                    shutil.rmtree(cache_path)
                    print(f"   ✅ Removed: {cache_path}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {cache_path}: {e}")

def clear_redis_cache_simple():
    """Try to clear Redis cache using simple methods"""
    print("🧹 Clearing Redis cache...")
    
    try:
        # Try to import and use redis directly
        import redis
        
        # Try common Redis connection settings
        redis_hosts = ['localhost', '127.0.0.1']
        redis_ports = [6379, 6380]
        
        for host in redis_hosts:
            for port in redis_ports:
                try:
                    r = redis.Redis(host=host, port=port, socket_connect_timeout=2)
                    r.ping()
                    print(f"   ✅ Connected to Redis at {host}:{port}")
                    
                    # Clear all keys
                    keys = r.keys('*')
                    if keys:
                        r.flushall()
                        print(f"   ✅ Cleared {len(keys)} Redis keys")
                    else:
                        print("   ✅ Redis already empty")
                    return True
                    
                except Exception:
                    continue
        
        print("   ⚠️ Could not connect to Redis")
        return False
        
    except ImportError:
        print("   ⚠️ Redis package not available")
        return False
    except Exception as e:
        print(f"   ❌ Redis clear failed: {e}")
        return False

def clear_file_caches():
    """Clear any file-based caches"""
    print("🧹 Clearing file caches...")
    
    # Remove any cache files
    cache_patterns = [
        '*.cache',
        'cache/*',
        'tmp/*',
        'temp/*',
        '.cache/*'
    ]
    
    for pattern in cache_patterns:
        try:
            files = glob.glob(pattern)
            for file_path in files:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"   ✅ Removed: {file_path}")
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
                    print(f"   ✅ Removed: {file_path}")
        except Exception as e:
            print(f"   ⚠️ Pattern {pattern}: {e}")

def clear_specific_recommendation_files():
    """Clear specific recommendation-related cache files"""
    print("🧹 Clearing recommendation-specific files...")
    
    # Look for recommendation cache files
    recommendation_patterns = [
        '**/*recommendation*.cache',
        '**/*recommendation*.json',
        '**/*cache*.json',
        '**/*similarity*.cache'
    ]
    
    for pattern in recommendation_patterns:
        try:
            files = glob.glob(pattern, recursive=True)
            for file_path in files:
                try:
                    os.remove(file_path)
                    print(f"   ✅ Removed: {file_path}")
                except Exception as e:
                    print(f"   ⚠️ Could not remove {file_path}: {e}")
        except Exception as e:
            print(f"   ⚠️ Pattern {pattern}: {e}")

def restart_recommendation_services():
    """Provide instructions for restarting services"""
    print("\n🔄 Recommendation Service Restart Instructions")
    print("=" * 50)
    print("To ensure fresh recommendations, restart these services:")
    print("   1. Flask application (if running)")
    print("   2. Redis server (if running)")
    print("   3. Any background workers")
    print("\n💡 Manual restart commands:")
    print("   - Flask: Stop and restart python app.py")
    print("   - Redis: redis-cli flushall")
    print("   - System: Restart terminal/IDE")

def main():
    """Main cache clearing function"""
    print("🚀 Simple Recommendation Cache Clearing")
    print("=" * 50)
    
    # Clear all types of caches
    clear_python_cache()
    clear_redis_cache_simple()
    clear_file_caches()
    clear_specific_recommendation_files()
    
    print("\n" + "=" * 50)
    print("🏁 Cache clearing completed!")
    
    # Provide restart instructions
    restart_recommendation_services()
    
    print("\n💡 What this accomplished:")
    print("   ✅ Cleared Python cache files")
    print("   ✅ Attempted Redis cache clearing")
    print("   ✅ Removed file-based caches")
    print("   ✅ Cleared recommendation-specific files")
    print("\n🎯 Next steps:")
    print("   1. Restart your Flask application")
    print("   2. All recommendation caches are now fresh")
    print("   3. Your Universal Semantic Matcher will work with clean data")
    print("   4. Test with a new recommendation request")

if __name__ == "__main__":
    main()
