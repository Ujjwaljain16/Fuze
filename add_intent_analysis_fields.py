#!/usr/bin/env python3
"""
Database migration script to add intent analysis fields to projects table
"""

import os
import sys
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def add_intent_analysis_fields():
    """Add intent analysis fields to projects table"""
    with app.app_context():
        try:
            # Check if columns already exist
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects' 
                AND column_name IN ('intent_analysis', 'intent_analysis_updated')
            """))
            
            existing_columns = [row[0] for row in result]
            
            if 'intent_analysis' not in existing_columns:
                print("Adding intent_analysis column...")
                db.session.execute(text("""
                    ALTER TABLE projects 
                    ADD COLUMN intent_analysis JSON
                """))
            
            if 'intent_analysis_updated' not in existing_columns:
                print("Adding intent_analysis_updated column...")
                db.session.execute(text("""
                    ALTER TABLE projects 
                    ADD COLUMN intent_analysis_updated TIMESTAMP
                """))
            
            db.session.commit()
            print("✅ Intent analysis fields added successfully!")
            
        except Exception as e:
            print(f"❌ Error adding intent analysis fields: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_intent_analysis_fields() 