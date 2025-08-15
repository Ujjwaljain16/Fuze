#!/usr/bin/env python3
"""
Check what's actually in the database and test recommendations system
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_database_content():
    """Check what content exists in the database"""
    print("🔍 Checking database content...")
    
    try:
        from models import db, SavedContent, User, Project
        
        with db.engine.connect() as connection:
            # Check users
            result = connection.execute(db.text('SELECT COUNT(*) FROM users'))
            user_count = result.fetchone()[0]
            print(f"   Users: {user_count}")
            
            # Check saved content
            result = connection.execute(db.text('SELECT COUNT(*) FROM saved_content'))
            content_count = result.fetchone()[0]
            print(f"   Saved content: {content_count}")
            
            # Check content quality
            result = connection.execute(db.text('''
                SELECT COUNT(*) as count, 
                       AVG(quality_score) as avg_score,
                       MIN(quality_score) as min_score,
                       MAX(quality_score) as max_score
                FROM saved_content
            '''))
            
            row = result.fetchone()
            if row[0] > 0:
                print(f"   Content quality: {row[1]:.1f} avg, {row[2]}-{row[3]} range")
                
                # Check high-quality content
                result = connection.execute(db.text('''
                    SELECT COUNT(*) FROM saved_content WHERE quality_score >= 7
                '''))
                high_quality_count = result.fetchone()[0]
                print(f"   High-quality content (score >= 7): {high_quality_count}")
                
                if high_quality_count == 0:
                    print("   ⚠️  No high-quality content found!")
                    print("   💡 This is why recommendations aren't working!")
                    return False
                else:
                    print("   ✅ Sufficient content for recommendations")
                    return True
            else:
                print("   ❌ No content in database!")
                return False
                
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")
        return False

def test_recommendations_engine():
    """Test the recommendations engine directly"""
    print("\n🧪 Testing recommendations engine...")
    
    try:
        # Test if the engine can be imported
        from unified_recommendation_orchestrator import UnifiedRecommendationOrchestrator
        print("   ✅ Engine imported successfully")
        
        # Test if it can be instantiated
        try:
            engine = UnifiedRecommendationOrchestrator()
            print("   ✅ Engine instantiated successfully")
            
            # Check what engines are available
            available_engines = list(engine.engines.keys()) if hasattr(engine, 'engines') else []
            print(f"   Available engines: {available_engines}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Engine instantiation failed: {e}")
            return False
            
    except ImportError as e:
        print(f"   ❌ Engine import failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Engine test failed: {e}")
        return False

def test_with_existing_user():
    """Test with an existing user to see if recommendations work"""
    print("\n👤 Testing with existing user...")
    
    try:
        from models import db, User
        
        with db.engine.connect() as connection:
            # Get first user
            result = connection.execute(db.text('SELECT id, username FROM users LIMIT 1'))
            user_row = result.fetchone()
            
            if user_row:
                user_id, username = user_row
                print(f"   Using user: {username} (ID: {user_id})")
                
                # Check if this user has any content
                result = connection.execute(db.text('''
                    SELECT COUNT(*) FROM saved_content WHERE user_id = %s
                '''), (user_id,))
                user_content_count = result.fetchone()[0]
                print(f"   User content: {user_content_count} items")
                
                return user_id, username
            else:
                print("   ❌ No users found in database")
                return None, None
                
    except Exception as e:
        print(f"   ❌ User check failed: {e}")
        return None, None

def create_simple_test():
    """Create a simple test to add content and test recommendations"""
    print("\n🧪 Creating simple test...")
    
    test_content = '''#!/usr/bin/env python3
"""
Simple test to add content and test recommendations
"""

import requests
import time

def add_test_content():
    """Add some test content to the database"""
    print("📝 Adding test content...")
    
    # First login
    login_data = {
        "username": "testuser",  # Use existing user
        "password": "testpass123"
    }
    
    try:
        login_response = requests.post("http://localhost:5000/api/auth/login", 
                                     json=login_data, timeout=15)
        
        if login_response.status_code == 200:
            token = login_response.json().get('access_token')
            print("   ✅ Login successful")
            
            # Add test bookmark
            headers = {"Authorization": f"Bearer {token}"}
            bookmark_data = {
                "url": "https://example.com/test",
                "title": "Test Content for Recommendations",
                "source": "test",
                "extracted_text": "This is test content about Python programming and web development. It covers topics like Flask, React, and database design.",
                "tags": "python, flask, react, database",
                "category": "programming",
                "notes": "Test content for recommendations system",
                "quality_score": 8
            }
            
            response = requests.post("http://localhost:5000/api/bookmarks", 
                                   json=bookmark_data, headers=headers, timeout=15)
            
            if response.status_code in [200, 201]:
                print("   ✅ Test content added")
                return token
            else:
                print(f"   ❌ Failed to add content: {response.status_code}")
                return None
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def test_recommendations(token):
    """Test if recommendations work now"""
    print("\\n🎯 Testing recommendations...")
    
    headers = {"Authorization": f"Bearer {token}"}
    test_data = {
        "title": "Python Web Development",
        "description": "Learning Flask and React",
        "technologies": "Python, Flask, React",
        "max_recommendations": 3
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/api/recommendations/unified-orchestrator",
            json=test_data,
            headers=headers,
            timeout=20
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get('recommendations', [])
            print(f"   ✅ SUCCESS! Got {len(recommendations)} recommendations")
            
            if recommendations:
                print("   First recommendation:")
                rec = recommendations[0]
                print(f"     Title: {rec.get('title', 'N/A')}")
                print(f"     Score: {rec.get('score', 'N/A')}")
            return True
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Simple Recommendations Test")
    print("=" * 50)
    
    # Add test content
    token = add_test_content()
    if not token:
        print("❌ Cannot proceed without content")
        return
    
    # Test recommendations
    success = test_recommendations(token)
    
    print("\\n" + "=" * 50)
    if success:
        print("🎉 Recommendations are working!")
        print("💡 The issue was lack of content in the database")
    else:
        print("❌ Recommendations still not working")
        print("💡 Check the server logs for errors")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('simple_recommendations_test.py', 'w') as f:
            f.write(test_content)
        print("✅ Created simple test script")
    except Exception as e:
        print(f"❌ Failed to create test: {e}")

def main():
    """Main diagnostic function"""
    print("🚀 Recommendations System Diagnostic")
    print("=" * 60)
    
    # Check database content
    has_content = check_database_content()
    
    # Test recommendations engine
    engine_works = test_recommendations_engine()
    
    # Test with existing user
    user_id, username = test_with_existing_user()
    
    # Create simple test
    create_simple_test()
    
    print("\n" + "=" * 60)
    print("🏁 Diagnostic completed!")
    
    if not has_content:
        print("\\n❌ PROBLEM IDENTIFIED: No content in database!")
        print("💡 Solution: Add some bookmarks/content to your system")
        print("💡 Run: python simple_recommendations_test.py")
        
    elif not engine_works:
        print("\\n❌ PROBLEM IDENTIFIED: Recommendations engine broken!")
        print("💡 Check the engine code for errors")
        
    else:
        print("\\n✅ System appears healthy")
        print("💡 Try running: python simple_recommendations_test.py")
        print("💡 Check server logs for any errors")

if __name__ == "__main__":
    main()
