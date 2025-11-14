#!/usr/bin/env python3
"""
Fix Missing Content for All Bookmarks
Uses enhanced scraping to extract content for bookmarks that don't have it
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
        logging.FileHandler('fix_missing_content.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent
from enhanced_web_scraper import scrape_url_enhanced

class MissingContentFixer:
    """
    Fix missing content for bookmarks using enhanced scraping
    """
    
    def __init__(self):
        self.processed_count = 0
        self.successful_count = 0
        self.failed_count = 0
        self.start_time = None
        
        # Rate limiting for scraping
        self.DELAY_BETWEEN_REQUESTS = 2  # seconds
        self.BATCH_SIZE = 10
        self.BATCH_DELAY = 10  # seconds
    
    def get_bookmarks_without_content(self) -> List[SavedContent]:
        """Get bookmarks that don't have extracted text"""
        try:
            with app.app_context():
                bookmarks = db.session.query(SavedContent).filter(
                    (SavedContent.extracted_text.is_(None)) |
                    (SavedContent.extracted_text == '') |
                    (SavedContent.extracted_text == 'null')
                ).order_by(SavedContent.saved_at.desc()).all()
                return bookmarks
        except Exception as e:
            logger.error(f"Error getting bookmarks without content: {e}")
            return []
    
    def get_content_stats(self) -> Dict:
        """Get current content statistics"""
        try:
            with app.app_context():
                total_bookmarks = db.session.query(SavedContent).count()
                bookmarks_with_content = db.session.query(SavedContent).filter(
                    SavedContent.extracted_text.isnot(None),
                    SavedContent.extracted_text != '',
                    SavedContent.extracted_text != 'null'
                ).count()
                bookmarks_without_content = total_bookmarks - bookmarks_with_content
                
                return {
                    'total': total_bookmarks,
                    'with_content': bookmarks_with_content,
                    'without_content': bookmarks_without_content,
                    'coverage': (bookmarks_with_content/total_bookmarks)*100 if total_bookmarks > 0 else 0
                }
        except Exception as e:
            logger.error(f"Error getting content stats: {e}")
            return {}
    
    def extract_content_for_bookmark(self, bookmark: SavedContent) -> bool:
        """Extract content for a single bookmark"""
        try:
            logger.info(f"Extracting content for: {bookmark.title}")
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
            
            # Update the bookmark with extracted content
            with app.app_context():
                bookmark.extracted_text = content
                if title and not bookmark.title:
                    bookmark.title = title
                db.session.commit()
                
                logger.info(f"Successfully extracted {len(content)} chars for bookmark {bookmark.id}")
                logger.info(f"Quality score: {quality_score}")
                
                self.successful_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Error extracting content for bookmark {bookmark.id}: {e}")
            self.failed_count += 1
            return False
    
    def process_bookmarks_batch(self, bookmarks: List[SavedContent]) -> Dict:
        """Process a batch of bookmarks"""
        batch_start = time.time()
        batch_success = 0
        batch_failed = 0
        
        logger.info(f"Processing batch of {len(bookmarks)} bookmarks")
        
        for bookmark in bookmarks:
            success = self.extract_content_for_bookmark(bookmark)
            if success:
                batch_success += 1
            else:
                batch_failed += 1
            
            self.processed_count += 1
            
            # Rate limiting delay
            time.sleep(self.DELAY_BETWEEN_REQUESTS)
        
        batch_time = time.time() - batch_start
        
        return {
            'batch_size': len(bookmarks),
            'success': batch_success,
            'failed': batch_failed,
            'time_taken': batch_time,
            'avg_time_per_item': batch_time / len(bookmarks) if bookmarks else 0
        }
    
    def run_content_fix(self, max_bookmarks: int = None, dry_run: bool = False):
        """Run the content fixing process"""
        self.start_time = time.time()
        
        logger.info("Starting Missing Content Fix Process")
        logger.info("=" * 60)
        
        # Get initial stats
        initial_stats = self.get_content_stats()
        logger.info(f"Initial stats: {initial_stats}")
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual content extraction will be performed")
        
        # Get bookmarks without content
        bookmarks_to_fix = self.get_bookmarks_without_content()
        
        if not bookmarks_to_fix:
            logger.info("✅ All bookmarks already have extracted content!")
            return
        
        if max_bookmarks:
            bookmarks_to_fix = bookmarks_to_fix[:max_bookmarks]
        
        logger.info(f"Found {len(bookmarks_to_fix)} bookmarks without content")
        
        if dry_run:
            logger.info("Would process the following bookmarks:")
            for i, bookmark in enumerate(bookmarks_to_fix[:5], 1):  # Show first 5
                logger.info(f"  {i}. {bookmark.title} - {bookmark.url}")
            if len(bookmarks_to_fix) > 5:
                logger.info(f"  ... and {len(bookmarks_to_fix) - 5} more")
            return
        
        # Process in batches
        total_batches = (len(bookmarks_to_fix) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.BATCH_SIZE
            end_idx = min(start_idx + self.BATCH_SIZE, len(bookmarks_to_fix))
            batch_bookmarks = bookmarks_to_fix[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_bookmarks)} items)")
            
            batch_result = self.process_bookmarks_batch(batch_bookmarks)
            logger.info(f"Batch result: {batch_result}")
            
            # Wait between batches
            if batch_num < total_batches - 1:  # Don't wait after last batch
                logger.info(f"Waiting {self.BATCH_DELAY} seconds before next batch...")
                time.sleep(self.BATCH_DELAY)
        
        # Final stats
        total_time = time.time() - self.start_time
        final_stats = self.get_content_stats()
        
        logger.info("=" * 60)
        logger.info("CONTENT FIX PROCESS COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Processed: {self.processed_count}")
        logger.info(f"Successful: {self.successful_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Success rate: {(self.successful_count/self.processed_count)*100:.1f}%" if self.processed_count > 0 else "N/A")
        logger.info(f"Final stats: {final_stats}")
        
        # Calculate efficiency metrics
        if self.successful_count > 0:
            avg_time_per_item = total_time / self.successful_count
            items_per_minute = (self.successful_count / total_time) * 60
            logger.info(f"Average time per successful item: {avg_time_per_item:.2f} seconds")
            logger.info(f"Processing rate: {items_per_minute:.2f} items/minute")

def main():
    """Main function to run the content fixing process"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Missing Content for Bookmarks')
    parser.add_argument('--max-bookmarks', type=int, help='Maximum number of bookmarks to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without actually doing it')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of bookmarks to process per batch')
    parser.add_argument('--delay', type=int, default=2, help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    fixer = MissingContentFixer()
    
    # Update settings if provided
    if args.batch_size:
        fixer.BATCH_SIZE = args.batch_size
    if args.delay:
        fixer.DELAY_BETWEEN_REQUESTS = args.delay
    
    # Run content fix
    try:
        fixer.run_content_fix(
            max_bookmarks=args.max_bookmarks,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        logger.info("\nContent fix process interrupted by user")
    except Exception as e:
        logger.error(f"Error during content fix process: {e}")

if __name__ == "__main__":
    main() 