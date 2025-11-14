#!/usr/bin/env python3
"""
Check database health and connection status
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_vars():
    """Check if database environment variables are set"""
    print("🔍 Checking environment variables...")
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print(f"✅ DATABASE_URL is set")
        # Mask the password for security
        if '://' in db_url:
            parts = db_url.split('://')
            if len(parts) == 2:
                protocol = parts[0]
                rest = parts[1]
                if '@' in rest:
                    user_pass, host_port_db = rest.split('@', 1)
                    if ':' in user_pass:
                        user, _ = user_pass.split(':', 1)
                        masked_url = f"{protocol}://{user}:***@{host_port_db}"
                        print(f"   URL: {masked_url}")
                    else:
                        print(f"   URL: {protocol}://***@{host_port_db}")
                else:
                    print(f"   URL: {db_url}")
    else:
        print("❌ DATABASE_URL not set")
        return False
    
    return True

def test_database_connection():
    """Test database connection directly"""
    print("\n🗄️ Testing database connection...")
    
    try:
        from models import db
        from sqlalchemy import text
        
        # Try to connect
        with db.engine.connect() as connection:
            print("✅ Database connection successful")
            
            # Test a simple query
            result = connection.execute(text('SELECT 1 as test'))
            row = result.fetchone()
            print(f"✅ Test query successful: {row[0]}")
            
            # Check database info
            result = connection.execute(text('SELECT version()'))
            version = result.fetchone()
            print(f"✅ Database version: {version[0][:50]}...")
            
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_database_tables():
    """Check if required tables exist"""
    print("\n📋 Checking database tables...")
    
    try:
        from models import db, User, SavedContent, Project
        
        # Check if tables exist by trying to query them
        with db.engine.connect() as connection:
            # Check users table
            try:
                result = connection.execute(text('SELECT COUNT(*) FROM users'))
                count = result.fetchone()[0]
                print(f"✅ Users table exists with {count} users")
            except Exception as e:
                print(f"❌ Users table issue: {e}")
                return False
            
            # Check saved_content table
            try:
                result = connection.execute(text('SELECT COUNT(*) FROM saved_content'))
                count = result.fetchone()[0]
                print(f"✅ Saved content table exists with {count} items")
            except Exception as e:
                print(f"❌ Saved content table issue: {e}")
                return False
            
            # Check projects table
            try:
                result = connection.execute(text('SELECT COUNT(*) FROM projects'))
                count = result.fetchone()[0]
                print(f"✅ Projects table exists with {count} projects")
            except Exception as e:
                print(f"❌ Projects table issue: {e}")
                return False
                
        return True
        
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False

def check_content_quality():
    """Check if there's content with good quality scores"""
    print("\n⭐ Checking content quality...")
    
    try:
        from models import db
        
        with db.engine.connect() as connection:
            # Check for high-quality content
            result = connection.execute(text('''
                SELECT COUNT(*) as count, 
                       AVG(quality_score) as avg_score,
                       MIN(quality_score) as min_score,
                       MAX(quality_score) as max_score
                FROM saved_content 
                WHERE quality_score >= 7
            '''))
            
            row = result.fetchone()
            count = row[0]
            avg_score = row[1] if row[1] else 0
            min_score = row[2] if row[2] else 0
            max_score = row[3] if row[3] else 0
            
            print(f"✅ High-quality content (score >= 7): {count} items")
            print(f"   Score range: {min_score} - {max_score}")
            print(f"   Average score: {avg_score:.2f}")
            
            if count == 0:
                print("⚠️  No high-quality content found! This is why recommendations aren't working.")
                print("   The system needs content with quality_score >= 7 to generate recommendations.")
                return False
            else:
                print("✅ Sufficient content for recommendations")
                return True
                
    except Exception as e:
        print(f"❌ Content quality check failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🚀 Database Health Check")
    print("=" * 50)
    
    # Check environment
    if not check_env_vars():
        print("\n❌ Environment not properly configured")
        return
    
    # Test connection
    if not test_database_connection():
        print("\n❌ Cannot connect to database")
        return
    
    # Check tables
    if not check_database_tables():
        print("\n❌ Database tables missing or corrupted")
        return
    
    # Check content
    if not check_content_quality():
        print("\n❌ No content available for recommendations")
        print("\n💡 To fix this:")
        print("   1. Add some bookmarks/content to your system")
        print("   2. Ensure content has quality_score >= 7")
        print("   3. Or lower the quality threshold in the code")
        return
    
    print("\n" + "=" * 50)
    print("✅ Database is healthy and has content!")
    print("💡 The issue might be in the application logic, not the database.")

if __name__ == "__main__":
    main()
