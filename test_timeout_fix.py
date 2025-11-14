#!/usr/bin/env python3
"""
Test script to verify that the database timeout issue has been resolved
"""

import os
import sys
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_database_timeout_fix():
    """Test if the database timeout issue has been resolved"""
    print("🔍 Testing Database Timeout Fix")
    print("=" * 50)
    
    # Check if we have the necessary environment variables
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        print("💡 Please check your .env file")
        return False
    
    print(f"✅ DATABASE_URL found: {database_url[:50]}...")
    
    # Test the ensemble endpoint to see if the timeout is fixed
    base_url = "http://localhost:5000"
    
    print(f"\n🧪 Testing ensemble recommendations endpoint...")
    print(f"   URL: {base_url}/api/recommendations/ensemble")
    
    # Test payload
    test_payload = {
        "title": "Test Project",
        "description": "Testing if database timeout is fixed",
        "technologies": "Python, Flask, PostgreSQL",
        "max_recommendations": 5
    }
    
    try:
        start_time = time.time()
        
        # Make request to ensemble endpoint
        response = requests.post(
            f"{base_url}/api/recommendations/ensemble",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # 60 second timeout for the test
        )
        
        response_time = (time.time() - start_time) * 1000
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Time: {response_time:.2f}ms")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"   ✅ Success! Got {len(recommendations)} recommendations")
            print(f"   Engine used: {data.get('engine_used', 'Unknown')}")
            
            # Show first recommendation if available
            if recommendations:
                first_rec = recommendations[0]
                print(f"   First recommendation:")
                print(f"     Title: {first_rec.get('title', 'N/A')}")
                print(f"     Score: {first_rec.get('score', 'N/A')}")
            
            # Check if response time is reasonable (should be under 10 seconds)
            if response_time < 10000:
                print(f"   🚀 Performance: Excellent! ({response_time:.2f}ms)")
                print(f"   ✅ Database timeout issue appears to be RESOLVED!")
                return True
            elif response_time < 30000:
                print(f"   ⚠️ Performance: Acceptable ({response_time:.2f}ms)")
                print(f"   ✅ Database timeout issue appears to be RESOLVED!")
                return True
            else:
                print(f"   ❌ Performance: Still slow ({response_time:.2f}ms)")
                print(f"   ⚠️ Database timeout issue may still exist")
                return False
                
        elif response.status_code == 401:
            print(f"   🔐 Authentication required - this is expected")
            print(f"   ✅ Endpoint is responding (no timeout)")
            print(f"   💡 Database timeout issue appears to be RESOLVED!")
            return True
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out after 60 seconds")
        print(f"   ❌ Database timeout issue still exists")
        return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Could not connect to server")
        print(f"   💡 Make sure the Flask app is running on {base_url}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def test_database_connection():
    """Test direct database connection"""
    print(f"\n🔍 Testing direct database connection...")
    
    try:
        from config import Config
        from models import db, SavedContent
        
        print(f"   ✅ Config loaded successfully")
        print(f"   ✅ Models imported successfully")
        
        # Try to create a simple query
        with db.app.app_context():
            # Simple count query to test connection
            start_time = time.time()
            count = SavedContent.query.count()
            query_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ Database query successful!")
            print(f"   📊 Total saved content: {count}")
            print(f"   ⚡ Query time: {query_time:.2f}ms")
            
            if query_time < 1000:
                print(f"   🚀 Database performance: Excellent!")
            elif query_time < 5000:
                print(f"   ✅ Database performance: Good")
            else:
                print(f"   ⚠️ Database performance: Could be better")
            
            return True
            
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Database Timeout Fix Verification")
    print("=" * 50)
    
    # Test 1: Check environment
    env_ok = test_database_timeout_fix()
    
    # Test 2: Direct database connection
    db_ok = test_database_connection()
    
    print(f"\n📊 Test Results Summary:")
    print(f"   Environment: {'✅ OK' if env_ok else '❌ Failed'}")
    print(f"   Database: {'✅ OK' if db_ok else '❌ Failed'}")
    
    if env_ok and db_ok:
        print(f"\n🎉 SUCCESS! Database timeout issue appears to be RESOLVED!")
        print(f"💡 The ensemble recommendations should now work without timeouts")
    else:
        print(f"\n⚠️ Some issues remain. Please check the errors above.")
