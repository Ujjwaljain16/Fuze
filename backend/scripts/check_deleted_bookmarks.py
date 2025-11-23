#!/usr/bin/env python3
"""
Check if bookmarks were deleted or moved to another user
"""

import sys
import os
from datetime import datetime, timedelta

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db, SavedContent, ContentAnalysis
from sqlalchemy import text

app = create_app()

def check_all_bookmarks():
    """Check all bookmarks in database and their user_ids"""
    with app.app_context():
        print("\n" + "="*60)
        print("ALL BOOKMARKS IN DATABASE")
        print("="*60)
        
        # Get all bookmarks grouped by user
        query = text("""
            SELECT 
                user_id,
                COUNT(*) as count,
                MIN(saved_at) as first_bookmark,
                MAX(saved_at) as last_bookmark
            FROM saved_content
            GROUP BY user_id
            ORDER BY user_id
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        print(f"\nTotal users with bookmarks: {len(rows)}")
        for row in rows:
            print(f"  User {row[0]}: {row[1]} bookmarks (first: {row[2]}, last: {row[3]})")

def check_bookmark_history():
    """Check if there are any bookmarks that might have been user 156's"""
    with app.app_context():
        print("\n" + "="*60)
        print("CHECKING FOR POTENTIALLY MOVED BOOKMARKS")
        print("="*60)
        
        # Check if any bookmarks were created around the time user 370 was created
        # that might have been user 156's
        query = text("""
            SELECT 
                id,
                user_id,
                url,
                title,
                saved_at
            FROM saved_content
            WHERE saved_at >= '2025-11-23 17:46:00'  -- Around when user 370 was created
                AND saved_at <= '2025-11-23 18:00:00'
            ORDER BY saved_at
            LIMIT 200
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        print(f"\nBookmarks created around user 370 creation time: {len(rows)}")
        print("\nFirst 20 bookmarks:")
        for row in rows[:20]:
            print(f"  ID {row[0]}, User {row[1]}: {row[3][:50]}... (saved: {row[4]})")

def check_for_deleted_records():
    """Check database for any signs of deleted records"""
    with app.app_context():
        print("\n" + "="*60)
        print("CHECKING FOR DELETED RECORDS")
        print("="*60)
        
        # Check if there are any content_analysis records without matching bookmarks
        query = text("""
            SELECT 
                ca.id,
                ca.content_id,
                ca.created_at
            FROM content_analysis ca
            LEFT JOIN saved_content sc ON ca.content_id = sc.id
            WHERE sc.id IS NULL
            LIMIT 50
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        if rows:
            print(f"\n⚠️  Found {len(rows)} orphaned ContentAnalysis records (bookmarks deleted)")
            for row in rows[:10]:
                print(f"  Analysis ID {row[0]} for deleted bookmark {row[1]} (created: {row[2]})")
        else:
            print("\n✅ No orphaned ContentAnalysis records found")

def check_user_156_timeline():
    """Check timeline of user 156's data"""
    with app.app_context():
        print("\n" + "="*60)
        print("USER 156 DATA TIMELINE")
        print("="*60)
        
        # Check when user 156 was created
        query = text("SELECT created_at FROM users WHERE id = 156")
        result = db.session.execute(query)
        user_created = result.fetchone()
        
        if user_created:
            print(f"\nUser 156 created: {user_created[0]}")
        
        # Check if there are any bookmarks with user_id 156 in the database at all
        query = text("SELECT COUNT(*) FROM saved_content WHERE user_id = 156")
        result = db.session.execute(query)
        count = result.fetchone()[0]
        
        print(f"Current bookmarks for user 156: {count}")
        
        # Check if there are any content_analysis records that might have been user 156's
        # by checking creation dates
        query = text("""
            SELECT 
                ca.id,
                ca.content_id,
                ca.created_at,
                sc.user_id,
                sc.title
            FROM content_analysis ca
            JOIN saved_content sc ON ca.content_id = sc.id
            WHERE ca.created_at < '2025-11-23 17:46:00'  -- Before user 370 was created
            ORDER BY ca.created_at DESC
            LIMIT 20
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        print(f"\nContent analyses created before user 370 (Nov 23, 17:46): {len(rows)}")
        for row in rows[:10]:
            print(f"  Analysis {row[0]} for User {row[3]}: {row[4][:40]}... (created: {row[2]})")

if __name__ == "__main__":
    check_all_bookmarks()
    check_bookmark_history()
    check_for_deleted_records()
    check_user_156_timeline()
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)

