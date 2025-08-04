#!/usr/bin/env python3
"""
Optimized Saved Bookmarks Analysis Script
Analyzes all saved bookmarks efficiently while respecting free tier rate limits
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bookmark_analysis.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis
from gemini_utils import GeminiAnalyzer
from background_analysis_service import BackgroundAnalysisService
from rate_limit_handler import GeminiRateLimiter
from redis_utils import RedisCache

class OptimizedBookmarkAnalyzer:
    """
    Optimized analyzer for processing saved bookmarks efficiently
    """
    
    def __init__(self):
        self.gemini_analyzer = GeminiAnalyzer()
        self.rate_limiter = GeminiRateLimiter()
        self.background_service = BackgroundAnalysisService()
        self.redis_cache = RedisCache()
        
        # Rate limit settings (free tier)
        self.REQUESTS_PER_MINUTE = 15
        self.REQUESTS_PER_DAY = 1500
        self.DELAY_BETWEEN_REQUESTS = 4  # seconds (to stay well under limit)
        
        # Batch processing settings
        self.BATCH_SIZE = 5  # Process 5 items per batch
        self.BATCH_DELAY = 30  # Wait 30 seconds between batches
        
        # Progress tracking
        self.processed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.start_time = None
        
    def get_analysis_stats(self) -> Dict:
        """Get current analysis statistics"""
        try:
            with app.app_context():
                total_bookmarks = db.session.query(SavedContent).count()
                analyzed_bookmarks = db.session.query(ContentAnalysis).count()
                
                return {
                    'total_bookmarks': total_bookmarks,
                    'analyzed_bookmarks': analyzed_bookmarks,
                    'pending_analysis': total_bookmarks - analyzed_bookmarks,
                    'coverage_percentage': (analyzed_bookmarks / total_bookmarks * 100) if total_bookmarks > 0 else 0
                }
        except Exception as e:
            logger.error(f"Error getting analysis stats: {e}")
            return {}
    
    def get_unanalyzed_bookmarks(self, limit: int = None, reanalyze_all: bool = False) -> List[SavedContent]:
        """Get bookmarks that haven't been analyzed yet or need reanalysis"""
        try:
            with app.app_context():
                if reanalyze_all:
                    # Get ALL bookmarks for reanalysis
                    query = db.session.query(SavedContent).filter(
                        SavedContent.extracted_text.isnot(None),
                        SavedContent.extracted_text != ''
                    ).order_by(SavedContent.saved_at.desc())  # Process newest first
                else:
                    # Find bookmarks without corresponding analysis
                    analyzed_ids = db.session.query(ContentAnalysis.content_id).subquery()
                    
                    query = db.session.query(SavedContent).filter(
                        ~SavedContent.id.in_(analyzed_ids),
                        SavedContent.extracted_text.isnot(None),
                        SavedContent.extracted_text != ''
                    ).order_by(SavedContent.saved_at.desc())  # Process newest first
                
                if limit:
                    query = query.limit(limit)
                
                return query.all()
        except Exception as e:
            logger.error(f"Error getting unanalyzed bookmarks: {e}")
            return []
    
    def check_rate_limit_status(self) -> Dict:
        """Check current rate limit status"""
        try:
            status = self.rate_limiter.get_status()
            logger.info(f"Rate limit status: {status}")
            return status
        except Exception as e:
            logger.error(f"Error checking rate limit status: {e}")
            return {}
    
    def wait_for_rate_limit(self, required_requests: int = 1):
        """Wait if necessary to respect rate limits"""
        try:
            status = self.rate_limiter.get_status()
            
            # Check if we can make the required number of requests
            if status.get('requests_last_minute', 0) + required_requests > self.REQUESTS_PER_MINUTE:
                wait_time = 60 - (datetime.now().minute % 1) * 60  # Wait until next minute
                logger.info(f"Rate limit approaching. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            
            # Check daily limit
            if status.get('requests_today', 0) + required_requests > self.REQUESTS_PER_DAY:
                logger.warning("Daily rate limit would be exceeded. Stopping analysis.")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            return True  # Continue if we can't check
    
    def analyze_single_bookmark(self, bookmark: SavedContent, reanalyze: bool = False) -> bool:
        """Analyze a single bookmark with rate limiting"""
        try:
            # Check if we can make a request
            if not self.wait_for_rate_limit(1):
                return False
            
            logger.info(f"Analyzing bookmark: {bookmark.title}")
            
            # Analyze with Gemini
            analysis_result = self.gemini_analyzer.analyze_bookmark_content(
                title=bookmark.title,
                description=bookmark.notes or bookmark.tags or "",
                content=bookmark.extracted_text,
                url=bookmark.url
            )
            
            if not analysis_result:
                logger.warning(f"No analysis result for bookmark {bookmark.id}")
                self.failed_count += 1
                return False
            
            # Extract key information
            key_concepts = analysis_result.get('key_concepts', [])
            content_type = analysis_result.get('content_type', 'unknown')
            difficulty_level = analysis_result.get('difficulty', 'unknown')
            technology_tags = analysis_result.get('technologies', [])
            
            # Create or update analysis record
            with app.app_context():
                existing_analysis = db.session.query(ContentAnalysis).filter_by(content_id=bookmark.id).first()
                
                if existing_analysis and reanalyze:
                    # Update existing analysis with new enhanced data
                    existing_analysis.analysis_data = analysis_result
                    existing_analysis.key_concepts = ', '.join(key_concepts) if isinstance(key_concepts, list) else str(key_concepts)
                    existing_analysis.content_type = content_type
                    existing_analysis.difficulty_level = difficulty_level
                    existing_analysis.technology_tags = ', '.join(technology_tags) if isinstance(technology_tags, list) else str(technology_tags)
                    existing_analysis.relevance_score = analysis_result.get('relevance_score', 0)
                    db.session.commit()
                    logger.info(f"Updated existing analysis for bookmark {bookmark.id}")
                else:
                    # Create new analysis record
                    analysis = ContentAnalysis(
                        content_id=bookmark.id,
                        analysis_data=analysis_result,
                        key_concepts=', '.join(key_concepts) if isinstance(key_concepts, list) else str(key_concepts),
                        content_type=content_type,
                        difficulty_level=difficulty_level,
                        technology_tags=', '.join(technology_tags) if isinstance(technology_tags, list) else str(technology_tags),
                        relevance_score=analysis_result.get('relevance_score', 0)
                    )
                    db.session.add(analysis)
                    db.session.commit()
                    logger.info(f"Created new analysis for bookmark {bookmark.id}")
            
            # Cache in Redis
            cache_key = f"content_analysis:{bookmark.id}"
            self.redis_cache.set_cache(cache_key, analysis_result, ttl=86400)
            
            self.processed_count += 1
            
            # Rate limiting delay
            time.sleep(self.DELAY_BETWEEN_REQUESTS)
            
            return True
            
        except Exception as e:
            logger.error(f"Error analyzing bookmark {bookmark.id}: {e}")
            self.failed_count += 1
            return False
    
    def analyze_bookmarks_batch(self, bookmarks: List[SavedContent], reanalyze: bool = False) -> Dict:
        """Analyze a batch of bookmarks efficiently"""
        batch_start = time.time()
        batch_success = 0
        batch_failed = 0
        
        logger.info(f"Processing batch of {len(bookmarks)} bookmarks")
        
        for bookmark in bookmarks:
            success = self.analyze_single_bookmark(bookmark, reanalyze=reanalyze)
            if success:
                batch_success += 1
            else:
                batch_failed += 1
        
        batch_time = time.time() - batch_start
        
        return {
            'batch_size': len(bookmarks),
            'success': batch_success,
            'failed': batch_failed,
            'time_taken': batch_time,
            'avg_time_per_item': batch_time / len(bookmarks) if bookmarks else 0
        }
    
    def run_optimized_analysis(self, max_bookmarks: int = None, dry_run: bool = False, reanalyze_all: bool = False):
        """Run the optimized analysis process"""
        self.start_time = time.time()
        
        if reanalyze_all:
            logger.info("Starting REANALYSIS of ALL Bookmarks with Enhanced Fields")
        else:
            logger.info("Starting Optimized Bookmark Analysis")
        logger.info("=" * 60)
        
        # Get initial stats
        initial_stats = self.get_analysis_stats()
        logger.info(f"Initial stats: {initial_stats}")
        
        if dry_run:
            logger.info("DRY RUN MODE - No actual analysis will be performed")
        
        # Check rate limit status
        rate_status = self.check_rate_limit_status()
        logger.info(f"Current rate limit status: {rate_status}")
        
        # Get bookmarks to analyze
        bookmarks_to_analyze = self.get_unanalyzed_bookmarks(limit=max_bookmarks, reanalyze_all=reanalyze_all)
        
        if reanalyze_all:
            logger.info(f"Found {len(bookmarks_to_analyze)} bookmarks to reanalyze with enhanced fields")
        else:
            logger.info(f"Found {len(bookmarks_to_analyze)} unanalyzed bookmarks")
        
        if not bookmarks_to_analyze:
            if reanalyze_all:
                logger.info("All bookmarks already have enhanced analysis!")
            else:
                logger.info("All bookmarks are already analyzed!")
            return
        
        # Process in batches
        total_batches = (len(bookmarks_to_analyze) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.BATCH_SIZE
            end_idx = min(start_idx + self.BATCH_SIZE, len(bookmarks_to_analyze))
            batch_bookmarks = bookmarks_to_analyze[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_bookmarks)} items)")
            
            if not dry_run:
                batch_result = self.analyze_bookmarks_batch(batch_bookmarks, reanalyze=reanalyze_all)
                logger.info(f"Batch result: {batch_result}")
                
                # Wait between batches
                if batch_num < total_batches - 1:  # Don't wait after last batch
                    logger.info(f"Waiting {self.BATCH_DELAY} seconds before next batch...")
                    time.sleep(self.BATCH_DELAY)
            else:
                logger.info(f"Would process {len(batch_bookmarks)} bookmarks in this batch")
                time.sleep(1)  # Small delay for dry run
        
        # Final stats
        total_time = time.time() - self.start_time
        final_stats = self.get_analysis_stats()
        
        logger.info("=" * 60)
        logger.info("ANALYSIS COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Processed: {self.processed_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Skipped: {self.skipped_count}")
        logger.info(f"Final stats: {final_stats}")
        
        # Calculate efficiency metrics
        if self.processed_count > 0:
            avg_time_per_item = total_time / self.processed_count
            items_per_minute = (self.processed_count / total_time) * 60
            logger.info(f"Average time per item: {avg_time_per_item:.2f} seconds")
            logger.info(f"Processing rate: {items_per_minute:.2f} items/minute")
    
    def start_background_analysis(self):
        """Start the background analysis service"""
        logger.info("Starting background analysis service...")
        self.background_service.start_background_analysis()
        logger.info("Background analysis service started")
    
    def stop_background_analysis(self):
        """Stop the background analysis service"""
        logger.info("Stopping background analysis service...")
        self.background_service.stop_background_analysis()
        logger.info("Background analysis service stopped")

def main():
    """Main function to run the optimized analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimized Bookmark Analysis')
    parser.add_argument('--max-bookmarks', type=int, help='Maximum number of bookmarks to analyze')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be analyzed without actually doing it')
    parser.add_argument('--background', action='store_true', help='Start background analysis service instead')
    parser.add_argument('--stats', action='store_true', help='Show current analysis statistics only')
    parser.add_argument('--reanalyze-all', action='store_true', help='Reanalyze ALL bookmarks with enhanced fields (including already analyzed ones)')
    
    args = parser.parse_args()
    
    # Check if API key is set
    if not os.environ.get('GEMINI_API_KEY'):
        logger.error("❌ GEMINI_API_KEY environment variable is not set")
        logger.error("Please set your Gemini API key and try again.")
        sys.exit(1)
    
    analyzer = OptimizedBookmarkAnalyzer()
    
    if args.stats:
        # Show stats only
        stats = analyzer.get_analysis_stats()
        rate_status = analyzer.check_rate_limit_status()
        
        print("\nANALYSIS STATISTICS")
        print("=" * 40)
        print(f"Total bookmarks: {stats.get('total_bookmarks', 0)}")
        print(f"Analyzed bookmarks: {stats.get('analyzed_bookmarks', 0)}")
        print(f"Pending analysis: {stats.get('pending_analysis', 0)}")
        print(f"Coverage: {stats.get('coverage_percentage', 0):.1f}%")
        
        print("\nRATE LIMIT STATUS")
        print("=" * 40)
        print(f"Requests this minute: {rate_status.get('requests_last_minute', 0)}")
        print(f"Requests today: {rate_status.get('requests_today', 0)}")
        print(f"Can make request: {rate_status.get('can_make_request', False)}")
        print(f"Daily limit: {rate_status.get('daily_limit', 0)}")
        print(f"Minute limit: {rate_status.get('minute_limit', 0)}")
        
        return
    
    if args.background:
        # Start background service
        try:
            analyzer.start_background_analysis()
            print("Background analysis service is running...")
            print("Press Ctrl+C to stop")
            
            try:
                while True:
                    time.sleep(10)
                    # Show progress every 10 seconds
                    stats = analyzer.get_analysis_stats()
                    print(f"\rProgress: {stats.get('analyzed_bookmarks', 0)}/{stats.get('total_bookmarks', 0)} analyzed ({stats.get('coverage_percentage', 0):.1f}%)", end='')
            except KeyboardInterrupt:
                print("\nStopping background service...")
                analyzer.stop_background_analysis()
                
        except Exception as e:
            logger.error(f"Error in background service: {e}")
            analyzer.stop_background_analysis()
    else:
        # Run optimized analysis
        try:
            analyzer.run_optimized_analysis(
                max_bookmarks=args.max_bookmarks,
                dry_run=args.dry_run,
                reanalyze_all=args.reanalyze_all
            )
        except KeyboardInterrupt:
            logger.info("\nAnalysis interrupted by user")
        except Exception as e:
            logger.error(f"Error during analysis: {e}")

if __name__ == "__main__":
    main() 