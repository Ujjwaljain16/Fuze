#!/usr/bin/env python3
"""
Direct Database Query Tool
Allows you to run SQL queries directly on the database
"""

import sys
import os
from datetime import datetime

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db
from sqlalchemy import text

app = create_app()

def query_user_bookmarks(user_id):
    """Query bookmarks for a specific user"""
    with app.app_context():
        query = text("""
            SELECT 
                id, 
                user_id, 
                url, 
                title, 
                saved_at,
                quality_score
            FROM saved_content 
            WHERE user_id = :user_id
            ORDER BY saved_at DESC
            LIMIT 100
        """)
        
        result = db.session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        print(f"\n📚 Bookmarks for User {user_id}: {len(rows)} found")
        for row in rows[:10]:  # Show first 10
            print(f"   ID {row[0]}: {row[3][:50]}... (saved: {row[4]})")
        
        return rows

def query_recent_operations(user_id=None, hours=24):
    """Query recent database operations"""
    with app.app_context():
        if user_id:
            query = text("""
                SELECT 
                    id, 
                    user_id, 
                    url, 
                    title, 
                    saved_at
                FROM saved_content 
                WHERE user_id = :user_id 
                    AND saved_at >= NOW() - INTERVAL ':hours hours'
                ORDER BY saved_at DESC
            """)
            result = db.session.execute(query, {"user_id": user_id, "hours": hours})
        else:
            query = text("""
                SELECT 
                    id, 
                    user_id, 
                    url, 
                    title, 
                    saved_at
                FROM saved_content 
                WHERE saved_at >= NOW() - INTERVAL ':hours hours'
                ORDER BY saved_at DESC
                LIMIT 100
            """)
            result = db.session.execute(query, {"hours": hours})
        
        rows = result.fetchall()
        
        print(f"\n🕐 Recent operations (last {hours} hours): {len(rows)} found")
        for row in rows[:20]:
            print(f"   User {row[1]}: {row[3][:40]}... at {row[4]}")
        
        return rows

def query_content_analyses(user_id):
    """Query content analyses for a user"""
    with app.app_context():
        query = text("""
            SELECT 
                ca.id,
                ca.content_id,
                sc.user_id,
                sc.title,
                ca.created_at
            FROM content_analysis ca
            JOIN saved_content sc ON ca.content_id = sc.id
            WHERE sc.user_id = :user_id
            ORDER BY ca.created_at DESC
            LIMIT 100
        """)
        
        result = db.session.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        
        print(f"\n🔍 Content Analyses for User {user_id}: {len(rows)} found")
        for row in rows[:10]:
            print(f"   Analysis ID {row[0]} for bookmark '{row[3][:40]}...' (created: {row[4]})")
        
        return rows

def check_user_counts():
    """Check bookmark counts per user"""
    with app.app_context():
        query = text("""
            SELECT 
                user_id,
                COUNT(*) as bookmark_count,
                MAX(saved_at) as last_bookmark,
                MIN(saved_at) as first_bookmark
            FROM saved_content
            GROUP BY user_id
            ORDER BY bookmark_count DESC
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        print(f"\n📊 Bookmark counts by user:")
        for row in rows:
            print(f"   User {row[0]}: {row[1]} bookmarks (first: {row[3]}, last: {row[2]})")
        
        return rows

def run_custom_query(sql_query):
    """Run a custom SQL query"""
    with app.app_context():
        try:
            result = db.session.execute(text(sql_query))
            rows = result.fetchall()
            
            print(f"\n✅ Query executed successfully: {len(rows)} rows returned")
            for row in rows[:20]:
                print(f"   {row}")
            
            return rows
        except Exception as e:
            print(f"\n❌ Query failed: {e}")
            return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Query database directly')
    parser.add_argument('--user', type=int, help='User ID to query')
    parser.add_argument('--recent', type=int, default=24, help='Hours to look back (default: 24)')
    parser.add_argument('--query', type=str, help='Custom SQL query to run')
    parser.add_argument('--analyses', action='store_true', help='Show content analyses')
    parser.add_argument('--counts', action='store_true', help='Show bookmark counts per user')
    
    args = parser.parse_args()
    
    if args.query:
        run_custom_query(args.query)
    elif args.counts:
        check_user_counts()
    elif args.user:
        query_user_bookmarks(args.user)
        if args.analyses:
            query_content_analyses(args.user)
    else:
        query_recent_operations(hours=args.recent)

