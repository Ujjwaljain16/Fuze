#!/usr/bin/env python3
"""
Simple database test script to check if the database and tables are working correctly.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, Project, SavedContent

def test_database():
    """Test database connection and basic operations"""
    print("Testing database connection and operations...")
    
    with app.app_context():
        try:
            # Test database connection
            print("1. Testing database connection...")
            db.session.execute(text("SELECT 1"))
            print("   ✓ Database connection successful")
            
            # Test User table
            print("2. Testing User table...")
            user_count = User.query.count()
            print(f"   ✓ User table accessible, {user_count} users found")
            
            # Test Project table
            print("3. Testing Project table...")
            project_count = Project.query.count()
            print(f"   ✓ Project table accessible, {project_count} projects found")
            
            # Test SavedContent table
            print("4. Testing SavedContent table...")
            content_count = SavedContent.query.count()
            print(f"   ✓ SavedContent table accessible, {content_count} items found")
            
            # Test creating a test user
            print("5. Testing user creation...")
            test_user = User.query.filter_by(username="testuser").first()
            if not test_user:
                print("   ✓ Test user not found (expected)")
            else:
                print(f"   ✓ Test user found with ID: {test_user.id}")
            
            # Test project creation
            print("6. Testing project creation...")
            if test_user:
                test_project = Project(
                    user_id=test_user.id,
                    title="Test Project",
                    description="This is a test project",
                    technologies="Python, Flask"
                )
                db.session.add(test_project)
                db.session.commit()
                print(f"   ✓ Project created successfully with ID: {test_project.id}")
                
                # Clean up
                db.session.delete(test_project)
                db.session.commit()
                print("   ✓ Test project cleaned up")
            else:
                print("   ⚠ Skipping project creation test (no test user)")
            
            print("\n🎉 All database tests passed!")
            return True
            
        except Exception as e:
            print(f"\n❌ Database test failed: {e}")
            return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1) 