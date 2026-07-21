import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from run_production import create_app
from models import db

app = create_app()
from sqlalchemy import text

def init_database():
    with app.app_context():
        try:
            # Enable pgvector extension (for Supabase)
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            db.session.commit()
            print("✅ pgvector extension enabled")
            
            # Run idempotent schema migrations (columns, token families table, etc.)
            from models import configure_database
            print("\n🔄 Running idempotent schema migrations...")
            if configure_database():
                print("✅ Schema migrations completed successfully")
            else:
                print("⚠️  Some schema migrations may have failed")
            
            # Create all tables
            db.create_all()
            print("✅ All database tables created successfully")
            
            # Run security migration (enable RLS, create policies) - OPTIONAL
            # Only run if RUN_SECURITY_MIGRATION env var is set to 'true'
            # This is a one-time setup, so it's optional after initial setup
            if os.environ.get('RUN_SECURITY_MIGRATION', 'false').lower() == 'true':
                try:
                    from utils.database_security_migration import run_security_migration
                    print("\n🔒 Running database security migration...")
                    results = run_security_migration(db)
                    print(f"✅ Security migration complete: {results.get('rls_enabled', 0)} tables with RLS enabled")
                except Exception as sec_error:
                    print(f"⚠️  Security migration skipped: {sec_error}")
                    print("   You can run it manually: python utils/database_security_migration.py")
            else:
                print("\nℹ️  Security migration skipped (set RUN_SECURITY_MIGRATION=true to enable)")
                print("   Run manually if needed: python utils/database_security_migration.py")
            
            print("\n✅ Database setup complete!")
            print("Your Fuze backend is ready to use!")
            
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            db.session.rollback()

if __name__ == "__main__":
    init_database() 