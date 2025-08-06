#!/usr/bin/env python3
"""
Test Database Connection
Simple test to check if database is accessible
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection and configuration"""
    print("🗄️ Testing Database Connection")
    print("=" * 40)
    
    try:
        # Check environment variables
        print("🔍 Checking Environment Variables...")
        
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            print(f"✅ DATABASE_URL found: {database_url[:50]}...")
        else:
            print("❌ DATABASE_URL not found in environment")
            print("   Please create a .env file with your database configuration")
            print("   See env_template.txt for reference")
        
        # Check if .env file exists
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            print("✅ .env file found")
        else:
            print("❌ .env file not found")
            print("   Please copy env_template.txt to .env and configure it")
        
        # Try to import and test database connection
        print("\n🔧 Testing Database Import...")
        
        try:
            from app import app, db
            print("✅ Flask app and database imported successfully")
            
            # Test database connection
            with app.app_context():
                try:
                    # Simple query to test connection
                    result = db.session.execute('SELECT 1')
                    print("✅ Database connection successful")
                    
                    # Check if tables exist
                    from models import SavedContent, ContentAnalysis
                    
                    try:
                        content_count = SavedContent.query.count()
                        print(f"✅ SavedContent table accessible: {content_count} records")
                    except Exception as e:
                        print(f"❌ SavedContent table error: {e}")
                    
                    try:
                        analysis_count = ContentAnalysis.query.count()
                        print(f"✅ ContentAnalysis table accessible: {analysis_count} records")
                    except Exception as e:
                        print(f"❌ ContentAnalysis table error: {e}")
                        
                except Exception as e:
                    print(f"❌ Database connection failed: {e}")
                    print("   This might be due to:")
                    print("   - Database not running")
                    print("   - Wrong credentials in DATABASE_URL")
                    print("   - Database doesn't exist")
                    
        except ImportError as e:
            print(f"❌ Import error: {e}")
            
    except Exception as e:
        print(f"❌ Error in database test: {e}")

if __name__ == "__main__":
    test_database_connection() 