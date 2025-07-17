#!/usr/bin/env python3
"""
Database migration script to add updated_at column to projects table
"""

import os
from sqlalchemy import text
from app import create_app
from models import db

def update_projects_table():
    """Add updated_at column to projects table if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if updated_at column exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects' AND column_name = 'updated_at'
            """))
            
            if not result.fetchone():
                print("Adding updated_at column to projects table...")
                
                # Add the updated_at column
                db.session.execute(text("""
                    ALTER TABLE projects 
                    ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """))
                
                # Update existing records to set updated_at = created_at
                db.session.execute(text("""
                    UPDATE projects 
                    SET updated_at = created_at 
                    WHERE updated_at IS NULL
                """))
                
                # Add trigger to automatically update updated_at on row updates
                db.session.execute(text("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                """))
                
                db.session.execute(text("""
                    DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
                    CREATE TRIGGER update_projects_updated_at
                        BEFORE UPDATE ON projects
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """))
                
                db.session.commit()
                print("✅ Successfully added updated_at column to projects table")
            else:
                print("✅ updated_at column already exists in projects table")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating projects table: {str(e)}")
            raise

if __name__ == "__main__":
    update_projects_table() 