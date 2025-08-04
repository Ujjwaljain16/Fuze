#!/usr/bin/env python3
"""
Add database indexes for better performance
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db

def add_performance_indexes():
    """Add database indexes for better performance"""
    print("🔧 Adding database indexes for performance...")
    
    try:
        with app.app_context():
            # Create indexes for better query performance
            indexes = [
                # SavedContent indexes
                "CREATE INDEX IF NOT EXISTS idx_savedcontent_quality_score ON saved_content(quality_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_savedcontent_title ON saved_content(title)",
                "CREATE INDEX IF NOT EXISTS idx_savedcontent_tags ON saved_content(tags)",
                "CREATE INDEX IF NOT EXISTS idx_savedcontent_saved_at ON saved_content(saved_at DESC)",
                
                # ContentAnalysis indexes
                "CREATE INDEX IF NOT EXISTS idx_contentanalysis_technology_tags ON content_analysis(technology_tags)",
                "CREATE INDEX IF NOT EXISTS idx_contentanalysis_key_concepts ON content_analysis(key_concepts)",
                "CREATE INDEX IF NOT EXISTS idx_contentanalysis_content_type ON content_analysis(content_type)",
                "CREATE INDEX IF NOT EXISTS idx_contentanalysis_difficulty_level ON content_analysis(difficulty_level)",
                
                # Composite indexes for common queries
                "CREATE INDEX IF NOT EXISTS idx_content_quality_tech ON saved_content(quality_score DESC, title)",
                "CREATE INDEX IF NOT EXISTS idx_analysis_tech_concepts ON content_analysis(technology_tags, key_concepts)",
            ]
            
            for index_sql in indexes:
                try:
                    db.session.execute(index_sql)
                    print(f"✅ Added index: {index_sql[:50]}...")
                except Exception as e:
                    print(f"⚠️  Index already exists or error: {e}")
            
            db.session.commit()
            print("🎉 Database indexes added successfully!")
            
    except Exception as e:
        print(f"❌ Error adding indexes: {e}")

if __name__ == "__main__":
    add_performance_indexes() 