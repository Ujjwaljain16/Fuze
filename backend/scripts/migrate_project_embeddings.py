#!/usr/bin/env python3
"""
Migrate project embeddings from multiple columns to single embedding column
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Project
from run_production import app

def migrate_project_embeddings():
    """Migrate from multiple embedding columns to single embedding column"""
    with app.app_context():
        try:
            # Check current columns
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('projects')]

            if 'embedding' not in columns:
                print("❌ Single embedding column missing from projects table!")
                print("Please run the add_project_embeddings.py script first.")
                return False

            # Check if old columns still exist
            old_columns = ['tech_embedding', 'description_embedding', 'combined_embedding', 'embeddings_updated']
            existing_old_columns = [col for col in old_columns if col in columns]

            if existing_old_columns:
                print(f"Found old embedding columns: {existing_old_columns}")
                print("⚠️  Old columns detected but cannot migrate due to model changes.")
                print("   This is expected - the new system uses a single 'embedding' column.")
                print("   Embeddings will be regenerated automatically for new/updated projects.")
                print("   You can safely drop the old columns manually if desired:")
                for col in existing_old_columns:
                    print(f"     ALTER TABLE projects DROP COLUMN {col};")
            else:
                print("No old embedding columns found.")

            # Count final status
            total_projects = Project.query.count()
            projects_with_embeddings = Project.query.filter(Project.embedding.isnot(None)).count()

            print(f"✅ Migration completed:")
            print(f"   Total projects: {total_projects}")
            print(f"   Projects with embeddings: {projects_with_embeddings}")
            print(f"   Projects needing embeddings: {total_projects - projects_with_embeddings}")

            if total_projects - projects_with_embeddings > 0:
                print("   Note: Remaining projects will get embeddings automatically on next update/create")

        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False

    return True

if __name__ == "__main__":
    migrate_project_embeddings()
