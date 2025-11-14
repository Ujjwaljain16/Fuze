#!/usr/bin/env python3
"""
Fix Content Database Issue
Fix the issue where content was extracted but not properly saved to database
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_content_database.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent
from enhanced_web_scraper import scrape_url_enhanced

class ContentDatabaseFixer:
    """
    Fix the database issue where content was extracted but not saved
    """
    
    def __init__(self):
        self.processed_count = 0
        self.successful_count = 0
        self.failed_count = 0
        self.start_time = None
        
        # Rate limiting for scraping
        self.DELAY_BETWEEN_REQUESTS = 2  # seconds
    
    def get_bookmarks_with_empty_content(self) -> List[SavedContent]:
        """Get bookmarks that have empty extracted text but should have content"""
        try:
            with app.app_context():
                bookmarks = db.session.query(SavedContent).filter(
                    (SavedContent.extracted_text.is_(None)) |
                    (SavedContent.extracted_text == '') |
                    (SavedContent.extracted_text == 'null')
                ).order_by(SavedContent.saved_at.desc()).all()
                return bookmarks
        except Exception as e:
            logger.error(f"Error getting bookmarks with empty content: {e}")
            return []
    
    def fix_bookmark_content(self, bookmark: SavedContent) -> bool:
        """Fix content for a single bookmark with proper database handling"""
        try:
            logger.info(f"Fixing content for: {bookmark.title}")
            logger.info(f"URL: {bookmark.url}")
            
            # Use enhanced scraper
            scraped_result = scrape_url_enhanced(bookmark.url)
            
            if not scraped_result:
                logger.warning(f"No scraping result for {bookmark.id}")
                self.failed_count += 1
                return False
            
            content = scraped_result.get('content', '')
            title = scraped_result.get('title', '')
            quality_score = scraped_result.get('quality_score', 0)
            
            # Check if we got meaningful content
            if not content or len(content.strip()) < 50:
                logger.warning(f"Insufficient content for {bookmark.id}: {len(content)} chars")
                self.failed_count += 1
                return False
            
            # Update the bookmark with extracted content - FIXED VERSION
            try:
                with app.app_context():
                    # Get fresh bookmark from database
                    fresh_bookmark = db.session.query(SavedContent).filter_by(id=bookmark.id).first()
                    if not fresh_bookmark:
                        logger.error(f"Bookmark {bookmark.id} not found in database")
                        self.failed_count += 1
                        return False
                    
                    # Update the content
                    fresh_bookmark.extracted_text = content
                    if title and not fresh_bookmark.title:
                        fresh_bookmark.title = title
                    
                    # Commit the transaction
                    db.session.commit()
                    
                    # Verify the update
                    db.session.refresh(fresh_bookmark)
                    if fresh_bookmark.extracted_text == content:
                        logger.info(f"✅ Successfully updated {len(content)} chars for bookmark {bookmark.id}")
                        logger.info(f"Quality score: {quality_score}")
                        self.successful_count += 1
                        return True
                    else:
                        logger.error(f"❌ Database update verification failed for bookmark {bookmark.id}")
                        self.failed_count += 1
                        return False
                        
            except Exception as db_error:
                logger.error(f"Database error for bookmark {bookmark.id}: {db_error}")
                db.session.rollback()
                self.failed_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Error fixing content for bookmark {bookmark.id}: {e}")
            self.failed_count += 1
            return False
    
    def run_database_fix(self, max_bookmarks: int = None, dry_run: bool = False):
        """Run the database fixing process"""
        self.start_time = time.time()
        
        logger.info("Starting Content Database Fix Process")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual database updates will be performed")
        
        # Get bookmarks with empty content
        bookmarks_to_fix = self.get_bookmarks_with_empty_content()
        
        if not bookmarks_to_fix:
            logger.info("✅ All bookmarks already have extracted content!")
            return
        
        if max_bookmarks:
            bookmarks_to_fix = bookmarks_to_fix[:max_bookmarks]
        
        logger.info(f"Found {len(bookmarks_to_fix)} bookmarks with empty content to fix")
        
        if dry_run:
            logger.info("Would process the following bookmarks:")
            for i, bookmark in enumerate(bookmarks_to_fix[:5], 1):
                logger.info(f"  {i}. {bookmark.title} - {bookmark.url}")
            if len(bookmarks_to_fix) > 5:
                logger.info(f"  ... and {len(bookmarks_to_fix) - 5} more")
            return
        
        # Process bookmarks
        for i, bookmark in enumerate(bookmarks_to_fix, 1):
            logger.info(f"Processing {i}/{len(bookmarks_to_fix)}: {bookmark.title}")
            
            success = self.fix_bookmark_content(bookmark)
            self.processed_count += 1
            
            if success:
                logger.info(f"✅ Successfully fixed bookmark {bookmark.id}")
            else:
                logger.warning(f"❌ Failed to fix bookmark {bookmark.id}")
            
            # Rate limiting delay
            if i < len(bookmarks_to_fix):  # Don't delay after last item
                time.sleep(self.DELAY_BETWEEN_REQUESTS)
        
        # Final stats
        total_time = time.time() - self.start_time
        
        logger.info("=" * 60)
        logger.info("CONTENT DATABASE FIX COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Processed: {self.processed_count}")
        logger.info(f"Successful: {self.successful_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Success rate: {(self.successful_count/self.processed_count)*100:.1f}%" if self.processed_count > 0 else "N/A")

def main():
    """Main function to run the database fix process"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Content Database Issue')
    parser.add_argument('--max-bookmarks', type=int, help='Maximum number of bookmarks to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without actually doing it')
    
    args = parser.parse_args()
    
    fixer = ContentDatabaseFixer()
    
    # Run database fix
    try:
        fixer.run_database_fix(
            max_bookmarks=args.max_bookmarks,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        logger.info("\nDatabase fix process interrupted by user")
    except Exception as e:
        logger.error(f"Error during database fix process: {e}")

if __name__ == "__main__":
    main() 