#!/usr/bin/env python3
"""
Migration script to add user_metadata column to users table
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db
from sqlalchemy import text, inspect

app = create_app()

def add_user_metadata_column():
    """Add user_metadata column to users table if it doesn't exist"""
    with app.app_context():
        try:
            # Check if column already exists
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'user_metadata' in columns:
                print("✅ Column 'user_metadata' already exists in users table")
                return True
            
            # Add the column
            print("Adding 'user_metadata' column to users table...")
            try:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN user_metadata JSON;
                """))
                db.session.commit()
                print("✅ Column 'user_metadata' added successfully")
                return True
            except Exception as add_error:
                # If column already exists (race condition), that's fine
                error_str = str(add_error).lower()
                if 'already exists' in error_str or 'duplicate' in error_str:
                    print("✅ Column 'user_metadata' already exists")
                    db.session.rollback()
                    return True
                else:
                    raise
            
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    add_user_metadata_column()

