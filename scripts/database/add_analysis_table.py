#!/usr/bin/env python3
"""
Script to add the ContentAnalysis table to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, ContentAnalysis

def add_analysis_table():
    """Add the ContentAnalysis table to the database"""
    with app.app_context():
        try:
            # Create the table
            db.create_all()
            print("✅ ContentAnalysis table created successfully!")
            
            # Verify the table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'content_analysis' in tables:
                print("✅ Table verification successful!")
                print(f"Available tables: {tables}")
            else:
                print("❌ Table verification failed!")
                
        except Exception as e:
            print(f"❌ Error creating table: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("Adding ContentAnalysis table to database...")
    success = add_analysis_table()
    if success:
        print("🎉 Database schema updated successfully!")
    else:
        print("💥 Failed to update database schema!") 