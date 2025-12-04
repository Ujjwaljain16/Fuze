#!/usr/bin/env python3
"""
Test script for API Key Revocation Manager
Run this to verify the revocation system is working correctly
"""

import sys
import os

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.api_key_revocation_manager import APIKeyRevocationManager
from utils.redis_utils import RedisCache

def test_revocation_manager():
    """Test the revocation manager functionality"""
    
    print("=" * 60)
    print("API Key Revocation Manager Test")
    print("=" * 60)
    
    # Initialize
    print("\n1. Initializing RevocationManager...")
    redis_cache = RedisCache()
    manager = APIKeyRevocationManager(redis_cache)
    
    if not redis_cache.connected:
        print("❌ Redis not connected - tests will fail")
        print("   Please check your REDIS_URL configuration")
        return False
    
    print("✅ Redis connected successfully")
    
    # Test API key
    test_key = "AIzaSyDummyKeyForTesting123456789012345"
    test_user_id = 999
    
    # Test 1: Revoke a key
    print(f"\n2. Revoking test API key...")
    success = manager.revoke_api_key(test_key, user_id=test_user_id)
    if success:
        print(f"✅ Key revoked successfully")
    else:
        print(f"❌ Failed to revoke key")
        return False
    
    # Test 2: Check if key is revoked
    print(f"\n3. Checking if key is revoked...")
    is_revoked = manager.is_api_key_revoked(test_key)
    if is_revoked:
        print(f"✅ Key correctly detected as revoked")
    else:
        print(f"❌ Key not detected as revoked")
        return False
    
    # Test 3: Check different key (should not be revoked)
    different_key = "AIzaSyDifferentKeyForTesting123456789012"
    print(f"\n4. Checking different key (should NOT be revoked)...")
    is_revoked = manager.is_api_key_revoked(different_key)
    if not is_revoked:
        print(f"✅ Different key correctly NOT revoked")
    else:
        print(f"❌ Different key incorrectly marked as revoked")
        return False
    
    # Test 4: Get revoked count
    print(f"\n5. Getting revoked keys count...")
    count = manager.get_revoked_count()
    print(f"✅ Total revoked keys: {count}")
    
    # Test 5: Remove from revocation list
    print(f"\n6. Removing test key from revocation list...")
    success = manager.remove_from_revocation_list(test_key)
    if success:
        print(f"✅ Key removed from revocation list")
    else:
        print(f"❌ Failed to remove key")
        return False
    
    # Test 6: Verify key is no longer revoked
    print(f"\n7. Verifying key is no longer revoked...")
    is_revoked = manager.is_api_key_revoked(test_key)
    if not is_revoked:
        print(f"✅ Key correctly NOT revoked after removal")
    else:
        print(f"❌ Key still showing as revoked")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True

def test_performance():
    """Test performance of revocation checks"""
    import time
    
    print("\n" + "=" * 60)
    print("Performance Test")
    print("=" * 60)
    
    redis_cache = RedisCache()
    manager = APIKeyRevocationManager(redis_cache)
    
    if not redis_cache.connected:
        print("❌ Redis not connected - skipping performance test")
        return
    
    test_key = "AIzaSyPerformanceTestKey123456789012345"
    
    # Add to revocation list
    manager.revoke_api_key(test_key)
    
    # Test lookup performance
    iterations = 1000
    print(f"\nRunning {iterations} revocation checks...")
    
    start_time = time.time()
    for _ in range(iterations):
        manager.is_api_key_revoked(test_key)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000  # Convert to ms
    
    print(f"✅ Average check time: {avg_time:.3f}ms")
    print(f"   Total time: {total_time:.3f}s")
    print(f"   Throughput: {iterations/total_time:.0f} checks/second")
    
    # Cleanup
    manager.remove_from_revocation_list(test_key)
    
    if avg_time < 1.0:
        print("\n✅ Performance excellent (< 1ms per check)")
    elif avg_time < 5.0:
        print("\n✅ Performance good (< 5ms per check)")
    else:
        print(f"\n⚠️  Performance slower than expected ({avg_time:.3f}ms)")

if __name__ == "__main__":
    print("Testing API Key Revocation Manager\n")
    
    # Run functional tests
    success = test_revocation_manager()
    
    if success:
        # Run performance tests
        test_performance()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("=" * 60)
    else:
        print("\n❌ Tests failed - please check the errors above")
        sys.exit(1)
