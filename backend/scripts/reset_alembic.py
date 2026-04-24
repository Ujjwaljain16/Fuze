import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add current directory to path to load .env
load_dotenv()

def reset_alembic():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not found in .env")
        return

    # Use 'pooler' URLs carefully, but for a single DDL it's fine
    engine = create_engine(db_url)
    
    try:
        with engine.connect() as conn:
            print("Checking for alembic_version table...")
            # Using text() for raw SQL
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
            conn.commit()
            print("Successfully dropped alembic_version table.")
    except Exception as e:
        print(f"Error resetting alembic: {e}")

if __name__ == "__main__":
    reset_alembic()
