#!/usr/bin/env python3
"""
User Content Processing Pipeline
Robust pipeline for new users with content extraction and AI analysis
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
from dataclasses import dataclass
from enum import Enum

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis, User
from enhanced_web_scraper import scrape_url_enhanced
from gemini_utils import GeminiAnalyzer
from rate_limit_handler import GeminiRateLimiter

class ProcessingStatus(Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"

@dataclass
class ProcessingJob:
    user_id: int
    bookmark_id: int
    status: ProcessingStatus
    priority: int = 1  # Higher number = higher priority
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class UserContentProcessor:
    """
    Robust content processing pipeline for new users
    """
    
    def __init__(self, user_id: int, user_api_key: str = None):
        self.user_id = user_id
        self.user_api_key = user_api_key or os.environ.get('GEMINI_API_KEY')
        self.gemini_analyzer = GeminiAnalyzer(api_key=self.user_api_key)
        self.rate_limiter = GeminiRateLimiter()
        
        # Processing settings
        self.MAX_RETRIES = 3
        self.RETRY_DELAY = 30  # seconds
        self.BATCH_SIZE = 5
        self.BATCH_DELAY = 60  # seconds
        
        # Rate limiting settings
        self.REQUESTS_PER_MINUTE = 15
        self.REQUESTS_PER_DAY = 1500
        
        self.logger = logging.getLogger(f"UserProcessor_{user_id}")
    
    def get_user_bookmarks(self, limit: int = None) -> List[SavedContent]:
        """Get bookmarks for the specific user"""
        try:
            with app.app_context():
                query = db.session.query(SavedContent).filter_by(user_id=self.user_id)
                if limit:
                    query = query.limit(limit)
                return query.order_by(SavedContent.saved_at.desc()).all()
        except Exception as e:
            self.logger.error(f"Error getting user bookmarks: {e}")
            return []
    
    def check_rate_limits(self) -> Dict:
        """Check current rate limit status"""
        try:
            status = self.rate_limiter.get_status()
            return {
                'can_make_request': status.get('can_make_request', False),
                'requests_last_minute': status.get('requests_last_minute', 0),
                'requests_today': status.get('requests_today', 0),
                'wait_time_seconds': status.get('wait_time_seconds', 0)
            }
        except Exception as e:
            self.logger.error(f"Error checking rate limits: {e}")
            return {'can_make_request': False}
    
    def extract_content_with_retry(self, bookmark: SavedContent) -> Optional[str]:
        """Extract content with retry mechanism"""
        for attempt in range(self.MAX_RETRIES):
            try:
                self.logger.info(f"Extracting content for bookmark {bookmark.id} (attempt {attempt + 1})")
                
                # Use enhanced scraper
                scraped_result = scrape_url_enhanced(bookmark.url)
                
                if not scraped_result:
                    raise Exception("No scraping result")
                
                content = scraped_result.get('content', '')
                
                if not content or len(content.strip()) < 50:
                    raise Exception(f"Insufficient content: {len(content)} chars")
                
                self.logger.info(f"Successfully extracted {len(content)} chars for bookmark {bookmark.id}")
                return content
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for bookmark {bookmark.id}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    self.logger.error(f"All attempts failed for bookmark {bookmark.id}")
                    return None
        
        return None
    
    def analyze_content_with_rate_limiting(self, bookmark: SavedContent, content: str) -> Optional[Dict]:
        """Analyze content with rate limiting"""
        try:
            # Check rate limits
            rate_status = self.check_rate_limits()
            if not rate_status['can_make_request']:
                wait_time = rate_status['wait_time_seconds']
                self.logger.info(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            
            # Record request
            self.rate_limiter.record_request()
            
            # Analyze with Gemini
            analysis_result = self.gemini_analyzer.analyze_bookmark_content(
                title=bookmark.title,
                description=bookmark.notes or bookmark.tags or "",
                content=content,
                url=bookmark.url
            )
            
            if not analysis_result:
                raise Exception("No analysis result from Gemini")
            
            self.logger.info(f"Successfully analyzed bookmark {bookmark.id}")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing bookmark {bookmark.id}: {e}")
            return None
    
    def save_content_to_database(self, bookmark: SavedContent, content: str) -> bool:
        """Save extracted content to database"""
        try:
            with app.app_context():
                bookmark.extracted_text = content
                db.session.commit()
                self.logger.info(f"Saved content to database for bookmark {bookmark.id}")
                return True
        except Exception as e:
            self.logger.error(f"Error saving content to database: {e}")
            db.session.rollback()
            return False
    
    def save_analysis_to_database(self, bookmark: SavedContent, analysis_result: Dict) -> bool:
        """Save AI analysis to database"""
        try:
            with app.app_context():
                # Extract key information
                key_concepts = analysis_result.get('key_concepts', [])
                content_type = analysis_result.get('content_type', 'unknown')
                difficulty_level = analysis_result.get('difficulty', 'unknown')
                technology_tags = analysis_result.get('technologies', [])
                
                # Create or update analysis record
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
                
                self.logger.info(f"Saved analysis to database for bookmark {bookmark.id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving analysis to database: {e}")
            db.session.rollback()
            return False
    
    def process_single_bookmark(self, bookmark: SavedContent) -> bool:
        """Process a single bookmark (extract + analyze)"""
        try:
            self.logger.info(f"Processing bookmark: {bookmark.title}")
            
            # Step 1: Extract content
            content = self.extract_content_with_retry(bookmark)
            if not content:
                return False
            
            # Step 2: Save content to database
            if not self.save_content_to_database(bookmark, content):
                return False
            
            # Step 3: Analyze content
            analysis_result = self.analyze_content_with_rate_limiting(bookmark, content)
            if not analysis_result:
                return False
            
            # Step 4: Save analysis to database
            if not self.save_analysis_to_database(bookmark, analysis_result):
                return False
            
            self.logger.info(f"Successfully processed bookmark {bookmark.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing bookmark {bookmark.id}: {e}")
            return False
    
    def process_user_bookmarks(self, limit: int = None, background: bool = False):
        """Process all bookmarks for the user"""
        try:
            self.logger.info(f"Starting content processing for user {self.user_id}")
            
            # Get user's bookmarks
            bookmarks = self.get_user_bookmarks(limit=limit)
            if not bookmarks:
                self.logger.info(f"No bookmarks found for user {self.user_id}")
                return
            
            self.logger.info(f"Found {len(bookmarks)} bookmarks to process")
            
            # Process in batches
            total_batches = (len(bookmarks) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            successful_count = 0
            failed_count = 0
            
            for batch_num in range(total_batches):
                start_idx = batch_num * self.BATCH_SIZE
                end_idx = min(start_idx + self.BATCH_SIZE, len(bookmarks))
                batch_bookmarks = bookmarks[start_idx:end_idx]
                
                self.logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch_bookmarks)} items)")
                
                for bookmark in batch_bookmarks:
                    success = self.process_single_bookmark(bookmark)
                    if success:
                        successful_count += 1
                    else:
                        failed_count += 1
                    
                    # Small delay between items
                    time.sleep(2)
                
                # Wait between batches
                if batch_num < total_batches - 1:
                    self.logger.info(f"Waiting {self.BATCH_DELAY} seconds before next batch...")
                    time.sleep(self.BATCH_DELAY)
            
            self.logger.info(f"Processing complete for user {self.user_id}")
            self.logger.info(f"Successful: {successful_count}, Failed: {failed_count}")
            
        except Exception as e:
            self.logger.error(f"Error processing user bookmarks: {e}")

def process_new_user_content(user_id: int, user_api_key: str = None, limit: int = None):
    """Process content for a new user"""
    processor = UserContentProcessor(user_id, user_api_key)
    processor.process_user_bookmarks(limit=limit)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process User Content')
    parser.add_argument('--user-id', type=int, required=True, help='User ID to process')
    parser.add_argument('--api-key', type=str, help='User-specific API key')
    parser.add_argument('--limit', type=int, help='Maximum number of bookmarks to process')
    
    args = parser.parse_args()
    
    process_new_user_content(args.user_id, args.api_key, args.limit) 