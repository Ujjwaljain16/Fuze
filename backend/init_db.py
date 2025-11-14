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
            
            # Create all tables
            db.create_all()
            print("✅ All database tables created successfully")
            
            print("\n🎉 Database setup complete!")
            print("Your Fuze backend is ready to use!")
            
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            db.session.rollback()

if __name__ == "__main__":
    init_database() 