#!/usr/bin/env python3
"""
Reset Database Sequences
Resets all auto-increment sequences to start from 1 after clearing database
"""

import sys
import os
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from run_production import create_app
from models import db
from sqlalchemy import text

app = create_app()

def reset_sequences():
    """Reset all sequences to start from 1"""
    with app.app_context():
        print("="*60)
        print("Resetting Database Sequences")
        print("="*60)
        
        # List of tables with auto-increment IDs
        sequences = [
            ('users', 'users_id_seq'),
            ('projects', 'projects_id_seq'),
            ('saved_content', 'saved_content_id_seq'),
            ('content_analysis', 'content_analysis_id_seq'),
            ('tasks', 'tasks_id_seq'),
            ('subtasks', 'subtasks_id_seq'),
            ('feedback', 'feedback_id_seq'),
            ('user_feedback', 'user_feedback_id_seq'),
        ]
        
        print("\nResetting sequences...")
        
        for table_name, sequence_name in sequences:
            try:
                # Check if sequence exists
                result = db.session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_sequences WHERE sequencename = '{sequence_name}'
                    );
                """))
                exists = result.scalar()
                
                if exists:
                    # Reset sequence to start from 1
                    db.session.execute(text(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1;"))
                    print(f"  ✅ Reset {sequence_name} → starts at 1")
                else:
                    # Try alternative sequence name format
                    alt_sequence = f"{table_name}_id_seq"
                    result = db.session.execute(text(f"""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_sequences WHERE sequencename = '{alt_sequence}'
                        );
                    """))
                    if result.scalar():
                        db.session.execute(text(f"ALTER SEQUENCE {alt_sequence} RESTART WITH 1;"))
                        print(f"  ✅ Reset {alt_sequence} → starts at 1")
                    else:
                        print(f"  ⚠️  Sequence for {table_name} not found (may use different naming)")
            except Exception as e:
                print(f"  ❌ Error resetting {sequence_name}: {e}")
        
        # Commit all changes
        db.session.commit()
        
        print("\n✅ All sequences reset successfully!")
        print("   Next IDs will start from 1")
        
        # Verify by checking next value
        print("\nVerifying sequences...")
        for table_name, sequence_name in sequences:
            try:
                result = db.session.execute(text(f"SELECT nextval('{sequence_name}');"))
                next_val = result.scalar()
                # Reset it back since we just incremented it
                db.session.execute(text(f"SELECT setval('{sequence_name}', 1, false);"))
                print(f"  {table_name}: next ID will be {next_val}")
            except Exception as e:
                # Sequence might not exist or have different name
                pass
        
        db.session.commit()

if __name__ == "__main__":
    print("\n⚠️  This will reset all ID sequences to start from 1")
    print("   Make sure you've cleared the database first!")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
        reset_sequences()
    else:
        print("Cancelled.")

