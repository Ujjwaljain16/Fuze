#!/usr/bin/env python3
"""
Add embedding columns to projects table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Project
from run_production import app

def add_embedding_columns():
    """Add embedding columns to projects table"""
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('projects')]

            # Add the single embedding column we actually need
            if 'embedding' not in columns:
                print("Adding embedding column...")
                try:
                    # Use session-based approach for better compatibility
                    from sqlalchemy import text
                    db.session.execute(text('ALTER TABLE projects ADD COLUMN embedding VECTOR(384)'))
                    db.session.commit()
                    print("✅ Successfully added embedding column")
                except Exception as e:
                    print(f"❌ Failed to add embedding column: {e}")
                    # Try alternative approach with raw SQL
                    try:
                        db.engine.raw_connection().execute('ALTER TABLE projects ADD COLUMN embedding VECTOR(384)')
                        print("✅ Successfully added embedding column (using raw connection)")
                    except Exception as e2:
                        print(f"❌ Failed both approaches: {e2}")
                        return False

            # Check if we still have old columns (they might be there from previous attempts)
            old_columns_present = any(col in columns for col in ['tech_embedding', 'description_embedding', 'combined_embedding'])
            if old_columns_present:
                print("⚠️  Old embedding columns detected. These will be ignored by the new code.")
                print("   You can safely drop them later after confirming the migration works.")

            print("✅ Successfully added embedding columns to projects table")

        except Exception as e:
            print(f"❌ Error adding columns: {e}")
            return False

    return True

if __name__ == "__main__":
    add_embedding_columns()
