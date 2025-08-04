#!/usr/bin/env python3
"""
Check Content Status in Database
Verify what's actually stored in the database for extracted text
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent

def check_content_status():
    """Check the actual content status in the database"""
    
    print("🔍 CHECKING CONTENT STATUS IN DATABASE")
    print("=" * 60)
    
    try:
        with app.app_context():
            # Get all bookmarks
            all_bookmarks = db.session.query(SavedContent).all()
            
            # Count bookmarks with and without content
            with_content = 0
            without_content = 0
            empty_content = 0
            null_content = 0
            
            print(f"Total bookmarks in database: {len(all_bookmarks)}")
            print()
            
            for bookmark in all_bookmarks:
                extracted_text = bookmark.extracted_text
                
                if extracted_text is None:
                    null_content += 1
                    print(f"❌ NULL: {bookmark.title[:50]}... (ID: {bookmark.id})")
                elif extracted_text == '':
                    empty_content += 1
                    print(f"❌ EMPTY: {bookmark.title[:50]}... (ID: {bookmark.id})")
                elif extracted_text == 'null':
                    empty_content += 1
                    print(f"❌ 'null' STRING: {bookmark.title[:50]}... (ID: {bookmark.id})")
                elif len(extracted_text.strip()) < 50:
                    without_content += 1
                    print(f"⚠️  SHORT ({len(extracted_text)} chars): {bookmark.title[:50]}... (ID: {bookmark.id})")
                else:
                    with_content += 1
                    print(f"✅ GOOD ({len(extracted_text)} chars): {bookmark.title[:50]}... (ID: {bookmark.id})")
            
            print()
            print("📊 SUMMARY:")
            print(f"✅ With good content: {with_content}")
            print(f"⚠️  With short content: {without_content}")
            print(f"❌ Empty content: {empty_content}")
            print(f"❌ NULL content: {null_content}")
            print(f"📈 Total with any content: {with_content + without_content}")
            print(f"📉 Total without content: {empty_content + null_content}")
            print(f"🎯 Coverage: {((with_content + without_content) / len(all_bookmarks)) * 100:.1f}%")
            
            # Show some examples of content
            print()
            print("📝 CONTENT EXAMPLES:")
            print("-" * 40)
            
            good_examples = [b for b in all_bookmarks if b.extracted_text and len(b.extracted_text.strip()) > 100]
            if good_examples:
                example = good_examples[0]
                print(f"Title: {example.title}")
                print(f"Content preview: {example.extracted_text[:200]}...")
                print(f"Content length: {len(example.extracted_text)} chars")
            
    except Exception as e:
        print(f"Error checking content status: {e}")

if __name__ == "__main__":
    check_content_status() 