#!/usr/bin/env python3
"""
Clear Recommendation Cache Script
Clears all recommendation-related caches using multiple methods
"""

import requests
import json
import time

def clear_recommendation_cache_via_api():
    """Clear recommendation cache via Flask API endpoint"""
    print("🧹 Clearing recommendation cache via API...")
    
    try:
        # Try to clear via the recommendations cache clear endpoint
        response = requests.post(
            "http://localhost:5000/api/recommendations/cache/clear",
            timeout=10
        )
        
        if response.status_code == 200:
            print("   ✅ Recommendation cache cleared via API")
            return True
        else:
            print(f"   ⚠️ API returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Flask server not running (ConnectionError)")
        return False
    except Exception as e:
        print(f"   ❌ API call failed: {e}")
        return False

def clear_unified_recommendation_cache():
    """Clear unified recommendation cache via API"""
    print("🧹 Clearing unified recommendation cache...")
    
    try:
        # Try to clear unified recommendations cache
        response = requests.post(
            "http://localhost:5000/api/recommendations/unified-orchestrator",
            json={"action": "clear_cache"},
            timeout=10
        )
        
        if response.status_code == 200:
            print("   ✅ Unified recommendation cache cleared")
            return True
        else:
            print(f"   ⚠️ Unified cache clear returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Flask server not running (ConnectionError)")
        return False
    except Exception as e:
        print(f"   ❌ Unified cache clear failed: {e}")
        return False

def clear_redis_recommendation_cache():
    """Clear Redis recommendation cache directly"""
    print("🧹 Clearing Redis recommendation cache...")
    
    try:
        from redis_utils import redis_cache
        
        # Access the actual Redis client
        if hasattr(redis_cache, 'redis_client') and redis_cache.redis_client:
            redis_client = redis_cache.redis_client
            
            # Get all recommendation-related keys
            recommendation_keys = redis_client.keys('*recommendation*')
            unified_keys = redis_client.keys('*unified*')
            cache_keys = redis_client.keys('*cache*')
            
            all_keys = recommendation_keys + unified_keys + cache_keys
            
            if all_keys:
                # Delete all recommendation-related keys
                deleted_count = redis_client.delete(*all_keys)
                print(f"   ✅ Deleted {deleted_count} recommendation cache keys")
                return True
            else:
                print("   ✅ No recommendation cache keys found")
                return True
        else:
            print("   ⚠️ Redis client not available")
            return False
            
    except ImportError:
        print("   ⚠️ Redis utils not available")
        return False
    except Exception as e:
        print(f"   ❌ Redis cache clear failed: {e}")
        return False

def clear_fast_gemini_cache():
    """Clear Fast Gemini recommendation cache"""
    print("🧹 Clearing Fast Gemini cache...")
    
    try:
        response = requests.post(
            "http://localhost:5000/api/recommendations/fast-gemini-clear-cache",
            timeout=10
        )
        
        if response.status_code == 200:
            print("   ✅ Fast Gemini cache cleared")
            return True
        else:
            print(f"   ⚠️ Fast Gemini cache clear returned status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Flask server not running (ConnectionError)")
        return False
    except Exception as e:
        print(f"   ❌ Fast Gemini cache clear failed: {e}")
        return False

def check_cache_status():
    """Check current cache status"""
    print("\n📊 Checking cache status...")
    
    try:
        # Check Fast Gemini cache stats
        response = requests.get(
            "http://localhost:5000/api/recommendations/fast-gemini-cache-stats",
            timeout=10
        )
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   📈 Fast Gemini cache: {stats}")
        else:
            print(f"   ⚠️ Could not get Fast Gemini cache stats: {response.status_code}")
            
    except Exception as e:
        print(f"   ⚠️ Cache status check failed: {e}")

def main():
    """Main function to clear all recommendation caches"""
    print("🚀 Recommendation Cache Clearing Tool")
    print("=" * 50)
    
    # Check if Flask server is running
    print("🔍 Checking if Flask server is running...")
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        print("   ✅ Flask server is running")
        server_running = True
    except:
        print("   ❌ Flask server is not running")
        server_running = False
    
    # Clear caches using different methods
    methods = [
        ("Redis Direct", clear_redis_recommendation_cache),
    ]
    
    # Add API methods only if server is running
    if server_running:
        methods.extend([
            ("API Endpoint", clear_recommendation_cache_via_api),
            ("Unified Cache", clear_unified_recommendation_cache),
            ("Fast Gemini", clear_fast_gemini_cache)
        ])
    
    # Execute all methods
    results = []
    for method_name, method_func in methods:
        try:
            result = method_func()
            results.append((method_name, result))
        except Exception as e:
            print(f"   ❌ {method_name} failed: {e}")
            results.append((method_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Cache Clearing Results")
    print("=" * 50)
    
    successful = 0
    total = len(results)
    
    for method_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"{status} {method_name}")
        if result:
            successful += 1
    
    print(f"\n🏁 Overall: {successful}/{total} methods successful")
    
    if server_running and successful > 0:
        print("\n💡 Next steps:")
        print("   1. All recommendation caches have been cleared")
        print("   2. Next recommendation requests will be fresh")
        print("   3. Your Universal Semantic Matcher will work with fresh data")
        
        # Check cache status after clearing
        time.sleep(1)
        check_cache_status()
    else:
        print("\n⚠️ Some cache clearing methods failed")
        print("   - Make sure Redis is running")
        print("   - Check if Flask server is accessible")

if __name__ == "__main__":
    main()
