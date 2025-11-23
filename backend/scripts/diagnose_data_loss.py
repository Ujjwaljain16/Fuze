#!/usr/bin/env python3
"""
Diagnostic Script for Data Loss Investigation
Checks database state and logs to investigate user data loss issues
"""

import sys
import os
from datetime import datetime, timedelta

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db, User, SavedContent, ContentAnalysis, Project

app = create_app()

def check_user_data(user_id):
    """Check if user's data exists in database"""
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"Checking data for User ID: {user_id}")
        print(f"{'='*60}")
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            print(f"❌ User {user_id} does NOT exist in database!")
            return False
        
        print(f"✅ User {user_id} exists: {user.username} ({user.email})")
        print(f"   Created at: {user.created_at}")
        
        # Check bookmarks
        bookmarks = SavedContent.query.filter_by(user_id=user_id).all()
        print(f"\n📚 Bookmarks: {len(bookmarks)} found")
        if bookmarks:
            print(f"   First bookmark: {bookmarks[0].title[:50]}...")
            print(f"   Last bookmark: {bookmarks[-1].title[:50]}...")
            print(f"   Date range: {bookmarks[-1].saved_at} to {bookmarks[0].saved_at}")
        else:
            print("   ⚠️  No bookmarks found!")
        
        # Check content analysis
        content_ids = [bm.id for bm in bookmarks]
        analyses = []
        if content_ids:
            analyses = ContentAnalysis.query.filter(ContentAnalysis.content_id.in_(content_ids)).all()
        print(f"\n🔍 Content Analyses: {len(analyses)} found")
        if analyses:
            print(f"   First analysis: Content ID {analyses[0].content_id}")
            print(f"   Last analysis: Content ID {analyses[-1].content_id}")
        else:
            print("   ⚠️  No content analyses found!")
        
        # Check projects
        projects = Project.query.filter_by(user_id=user_id).all()
        print(f"\n📁 Projects: {len(projects)} found")
        if projects:
            for proj in projects[:3]:
                print(f"   - {proj.title[:50]}")
        
        return True

def check_recent_imports():
    """Check recent bookmark imports"""
    with app.app_context():
        print(f"\n{'='*60}")
        print("Recent Bookmark Activity (Last 24 hours)")
        print(f"{'='*60}")
        
        # Get bookmarks created in last 24 hours
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        recent_bookmarks = SavedContent.query.filter(
            SavedContent.saved_at >= yesterday
        ).order_by(SavedContent.saved_at.desc()).limit(50).all()
        
        print(f"\n📊 Total bookmarks created in last 24h: {len(recent_bookmarks)}")
        
        # Group by user
        by_user = {}
        for bm in recent_bookmarks:
            if bm.user_id not in by_user:
                by_user[bm.user_id] = []
            by_user[bm.user_id].append(bm)
        
        print(f"\n👥 Users with recent activity:")
        for user_id, bookmarks in sorted(by_user.items(), key=lambda x: len(x[1]), reverse=True):
            user = User.query.get(user_id)
            username = user.username if user else f"User {user_id} (deleted?)"
            print(f"   User {user_id} ({username}): {len(bookmarks)} bookmarks")
            if bookmarks:
                print(f"      First: {bookmarks[-1].saved_at} - {bookmarks[-1].title[:40]}")
                print(f"      Last:  {bookmarks[0].saved_at} - {bookmarks[0].title[:40]}")

def check_database_constraints():
    """Check for database constraint violations"""
    with app.app_context():
        print(f"\n{'='*60}")
        print("Database Integrity Checks")
        print(f"{'='*60}")
        
        # Check for orphaned content analyses
        all_analyses = ContentAnalysis.query.all()
        orphaned = []
        for analysis in all_analyses:
            bookmark = SavedContent.query.get(analysis.content_id)
            if not bookmark:
                orphaned.append(analysis.id)
        
        if orphaned:
            print(f"⚠️  Found {len(orphaned)} orphaned ContentAnalysis records (content_id doesn't exist)")
        else:
            print("✅ No orphaned ContentAnalysis records")
        
        # Check for bookmarks without user
        all_bookmarks = SavedContent.query.all()
        orphaned_bookmarks = []
        for bm in all_bookmarks:
            user = User.query.get(bm.user_id)
            if not user:
                orphaned_bookmarks.append(bm.id)
        
        if orphaned_bookmarks:
            print(f"⚠️  Found {len(orphaned_bookmarks)} bookmarks with invalid user_id")
        else:
            print("✅ All bookmarks have valid user_id")

def check_logs_for_imports():
    """Check application logs for import activity"""
    log_file = os.path.join(backend_dir, 'production.log')
    
    if not os.path.exists(log_file):
        print(f"\n⚠️  Log file not found: {log_file}")
        return
    
    print(f"\n{'='*60}")
    print(f"Recent Import Activity in Logs")
    print(f"{'='*60}")
    
    # Read last 1000 lines of log file
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
            
            import_lines = [line for line in recent_lines if 'IMPORT' in line or 'import' in line.lower()]
            
            if import_lines:
                print(f"\nFound {len(import_lines)} import-related log entries:")
                for line in import_lines[-20:]:  # Show last 20
                    print(f"   {line.strip()[:100]}")
            else:
                print("\n⚠️  No import-related log entries found in recent logs")
                
    except Exception as e:
        print(f"\n❌ Error reading log file: {e}")

def compare_users(user_id_1, user_id_2):
    """Compare data between two users"""
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"Comparing User {user_id_1} vs User {user_id_2}")
        print(f"{'='*60}")
        
        for user_id in [user_id_1, user_id_2]:
            user = User.query.get(user_id)
            if not user:
                print(f"\n❌ User {user_id} does not exist")
                continue
            
            bookmarks = SavedContent.query.filter_by(user_id=user_id).count()
            analyses = db.session.query(ContentAnalysis).join(
                SavedContent, ContentAnalysis.content_id == SavedContent.id
            ).filter(SavedContent.user_id == user_id).count()
            projects = Project.query.filter_by(user_id=user_id).count()
            
            print(f"\nUser {user_id} ({user.username}):")
            print(f"   Bookmarks: {bookmarks}")
            print(f"   Analyses: {analyses}")
            print(f"   Projects: {projects}")

def main():
    """Main diagnostic function"""
    print("="*60)
    print("DATA LOSS DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check user 156
    print("\n1. Checking User 156 data...")
    check_user_data(156)
    
    # Check user 370
    print("\n2. Checking User 370 data...")
    check_user_data(370)
    
    # Compare users
    print("\n3. Comparing users...")
    compare_users(156, 370)
    
    # Check recent imports
    print("\n4. Checking recent import activity...")
    check_recent_imports()
    
    # Check database integrity
    print("\n5. Checking database integrity...")
    check_database_constraints()
    
    # Check logs
    print("\n6. Checking application logs...")
    check_logs_for_imports()
    
    print(f"\n{'='*60}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. If user 156's data is missing, check if it was deleted or moved")
    print("2. Review the log entries above for any errors")
    print("3. Check if there were any database migrations or schema changes")
    print("4. Verify the extension was using the correct auth token")

if __name__ == "__main__":
    main()

