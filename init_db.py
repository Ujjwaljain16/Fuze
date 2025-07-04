from app import app, db
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