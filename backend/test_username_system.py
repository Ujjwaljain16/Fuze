#!/usr/bin/env python3
"""
Comprehensive test suite for the robust username detection system
Tests performance, race conditions, and scalability
"""

import os
import sys
import time
import threading
import concurrent.futures
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_username_system():
    """Comprehensive test of the username detection system"""
    try:
        from run_production import app, db
        from blueprints.auth import check_username_availability, generate_username_suggestions, bulk_check_usernames
        from models import User

        with app.app_context():
            print("🧪 TESTING ROBUST USERNAME DETECTION SYSTEM")
            print("=" * 60)

            # Test 1: Basic availability check
            print("\n1️⃣ Testing basic availability checks...")
            test_cases = [
                ('nonexistent_user_12345', True, "Should be available"),
                ('admin', False, "Should be taken"),
                ('', False, "Empty username should be invalid"),
                ('a' * 60, False, "Too long username should be invalid"),
            ]

            for username, expected_available, description in test_cases:
                is_available, _, _ = check_username_availability(username)
                status = "✅" if is_available == expected_available else "❌"
                print(f"   {status} {username}: {description}")

            # Test 2: Case insensitive checks
            print("\n2️⃣ Testing case-insensitive checks...")
            # Create a test user for case testing
            test_user = f"TestUser_{os.urandom(4).hex()}"
            try:
                test_user_obj = User(username=test_user, email=f"{test_user}@test.com", password_hash="test")
                db.session.add(test_user_obj)
                db.session.commit()

                # Test case variations
                variations = [test_user.lower(), test_user.upper(), test_user.capitalize()]
                for variation in variations:
                    is_available, _, conflict = check_username_availability(variation)
                    if not is_available and conflict == test_user:
                        print(f"   ✅ Case-insensitive check works: {variation} → conflicts with {test_user}")
                    else:
                        print(f"   ❌ Case-insensitive check failed: {variation}")

                # Clean up test user
                db.session.delete(test_user_obj)
                db.session.commit()

            except Exception as e:
                print(f"   ⚠️ Could not test case sensitivity: {e}")

            # Test 3: Suggestion generation
            print("\n3️⃣ Testing username suggestions...")
            taken_username = "admin"  # Assuming this exists
            suggestions = generate_username_suggestions(taken_username, 3)

            print(f"   📝 Suggestions for '{taken_username}': {suggestions}")
            if suggestions:
                # Verify suggestions are actually available
                available_suggestions = []
                for suggestion in suggestions:
                    is_available, _, _ = check_username_availability(suggestion)
                    if is_available:
                        available_suggestions.append(suggestion)

                print(f"   ✅ Available suggestions: {len(available_suggestions)}/{len(suggestions)}")
            else:
                print("   ⚠️ No suggestions generated")

            # Test 4: Bulk checking
            print("\n4️⃣ Testing bulk username checking...")
            bulk_test_usernames = [
                f"bulk_test_{i}_{os.urandom(2).hex()}" for i in range(10)
            ]
            bulk_results = bulk_check_usernames(bulk_test_usernames)

            available_count = sum(1 for available in bulk_results.values() if available)
            print(f"   📊 Bulk check: {available_count}/{len(bulk_test_usernames)} usernames available")

            # Test 5: Performance test
            print("\n5️⃣ Testing performance...")
            performance_tests = [
                f"perf_test_{i}_{os.urandom(4).hex()}" for i in range(100)
            ]

            start_time = time.time()
            results = bulk_check_usernames(performance_tests)
            end_time = time.time()

            total_time = end_time - start_time
            avg_time = total_time / len(performance_tests)

            print(".4f"            print(".6f"
            if avg_time < 0.01:  # Less than 10ms per check
                print("   ✅ Performance excellent!")
            elif avg_time < 0.05:  # Less than 50ms per check
                print("   ✅ Performance good!")
            else:
                print("   ⚠️ Performance could be better")

            # Test 6: Race condition simulation
            print("\n6️⃣ Testing race condition handling...")
            race_test_username = f"race_test_{os.urandom(8).hex()}"

            def simulate_concurrent_registration(username):
                """Simulate concurrent registration attempts"""
                try:
                    is_available, _, _ = check_username_availability(username)
                    if is_available:
                        # Try to create user
                        test_user = User(username=username, email=f"{username}@test.com", password_hash="test")
                        db.session.add(test_user)
                        db.session.commit()
                        return True
                    return False
                except Exception:
                    db.session.rollback()
                    return False

            # Run multiple concurrent attempts
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(simulate_concurrent_registration, race_test_username) for _ in range(5)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]

            successful_creations = sum(1 for result in results if result)
            print(f"   🎯 Race condition test: {successful_creations}/5 concurrent attempts succeeded")

            if successful_creations == 1:
                print("   ✅ Race conditions handled correctly!")
            else:
                print(f"   ⚠️ Race condition issue: {successful_creations} users created with same username")

            # Clean up race test user
            try:
                race_user = User.query.filter_by(username=race_test_username).first()
                if race_user:
                    db.session.delete(race_user)
                    db.session.commit()
            except:
                pass

            print("\n" + "=" * 60)
            print("🎉 USERNAME DETECTION SYSTEM TEST COMPLETE!")
            print("=" * 60)

            return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_username_system()
    sys.exit(0 if success else 1)
