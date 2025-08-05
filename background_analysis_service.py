#!/usr/bin/env python3
"""
Background Analysis Service for Gemini Content Analysis
"""

import sys
import os
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, SavedContent, ContentAnalysis
from gemini_utils import GeminiAnalyzer
from redis_utils import RedisCache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundAnalysisService:
    """Service to analyze content in the background and cache results"""
    
    def __init__(self):
        self.gemini_analyzer = GeminiAnalyzer()
        self.redis_cache = RedisCache()
        self.running = False
        self.analysis_thread = None
        self.failed_analyses = set()  # Track failed content IDs to avoid infinite retries
        
    def start_background_analysis(self):
        """Start the background analysis thread"""
        if self.running:
            logger.info("Background analysis service is already running")
            return
            
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()
        logger.info("Background analysis service started")
    
    def stop_background_analysis(self):
        """Stop the background analysis thread"""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join()
        logger.info("Background analysis service stopped")
    
    def _analysis_worker(self):
        """Background worker that continuously checks for unanalyzed content"""
        while self.running:
            try:
                with app.app_context():
                    self._process_unanalyzed_content()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in background analysis worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _process_unanalyzed_content(self):
        """Process content that hasn't been analyzed yet"""
        try:
            # Find content without analysis
            unanalyzed_content = self._get_unanalyzed_content()
            
            if not unanalyzed_content:
                return
                
            logger.info(f"Found {len(unanalyzed_content)} items to analyze")
            
            for content in unanalyzed_content:
                try:
                    self._analyze_single_content(content)
                    time.sleep(2)  # Rate limiting between analyses
                except Exception as e:
                    logger.error(f"Error analyzing content {content.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing unanalyzed content: {e}")
    
    def _get_unanalyzed_content(self) -> List[SavedContent]:
        """Get content that hasn't been analyzed yet"""
        try:
            # Find content without corresponding analysis
            analyzed_content_ids = db.session.query(ContentAnalysis.content_id).subquery()
            
            # Also exclude content that has no extracted_text to avoid repeated failures
            unanalyzed = db.session.query(SavedContent).filter(
                ~SavedContent.id.in_(analyzed_content_ids),
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).limit(10).all()  # Process 10 at a time
            
            # Filter out previously failed analyses
            unanalyzed = [content for content in unanalyzed if content.id not in self.failed_analyses]
            
            return unanalyzed
        except Exception as e:
            logger.error(f"Error getting unanalyzed content: {e}")
            return []
    
    def _analyze_single_content(self, content: SavedContent):
        """Analyze a single content item and store the result"""
        try:
            logger.info(f"Analyzing content: {content.title}")
            
            # Check if we have the required fields
            if not content.extracted_text:
                logger.warning(f"Content {content.id} has no extracted_text, skipping")
                return
            
            # Analyze with Gemini
            analysis_result = self.gemini_analyzer.analyze_bookmark_content(
                title=content.title,
                description=content.notes or content.tags or "",
                content=content.extracted_text,
                url=content.url
            )
            
            if not analysis_result:
                logger.warning(f"No analysis result for content {content.id}")
                return
            
            # Extract key information from analysis
            key_concepts = analysis_result.get('key_concepts', [])
            content_type = analysis_result.get('content_type', 'unknown')
            difficulty_level = analysis_result.get('difficulty', 'unknown')  # Note: field name is 'difficulty' not 'difficulty_level'
            technology_tags = analysis_result.get('technologies', [])
            
            # Create analysis record
            analysis = ContentAnalysis(
                content_id=content.id,
                analysis_data=analysis_result,
                key_concepts=', '.join(key_concepts) if isinstance(key_concepts, list) else str(key_concepts),
                content_type=content_type,
                difficulty_level=difficulty_level,
                technology_tags=', '.join(technology_tags) if isinstance(technology_tags, list) else str(technology_tags),
                relevance_score=analysis_result.get('relevance_score', 0)
            )
            
            # Save to database
            db.session.add(analysis)
            db.session.commit()
            
            # Cache in Redis
            cache_key = f"content_analysis:{content.id}"
            self.redis_cache.set_cache(cache_key, analysis_result, ttl=86400)  # 24 hours
            
            # Invalidate caches using comprehensive cache invalidation service
            from cache_invalidation_service import cache_invalidator
            cache_invalidator.after_analysis_complete(content.id, content.user_id)
            
            logger.info(f"✅ Analysis completed and stored for content {content.id}")
            
        except Exception as e:
            logger.error(f"Error analyzing content {content.id}: {e}")
            db.session.rollback()
            # Add to failed analyses to prevent infinite retries
            self.failed_analyses.add(content.id)
    
    def get_cached_analysis(self, content_id: int) -> Optional[Dict]:
        """Get cached analysis for a content item"""
        try:
            # Try Redis first
            cache_key = f"content_analysis:{content_id}"
            cached_result = self.redis_cache.get_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Try database
            with app.app_context():
                analysis = db.session.query(ContentAnalysis).filter_by(content_id=content_id).first()
                if analysis:
                    # Cache in Redis for future use
                    self.redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                    return analysis.analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for content {content_id}: {e}")
            return None
    
    def analyze_content_immediately(self, content_id: int) -> Optional[Dict]:
        """Analyze content immediately (for user-triggered analysis)"""
        try:
            with app.app_context():
                content = db.session.query(SavedContent).filter_by(id=content_id).first()
                if not content:
                    logger.error(f"Content {content_id} not found")
                    return None
                
                self._analyze_single_content(content)
                
                # Return the analysis result
                return self.get_cached_analysis(content_id)
                
        except Exception as e:
            logger.error(f"Error in immediate analysis for content {content_id}: {e}")
            return None
    
    def get_analysis_stats(self) -> Dict:
        """Get statistics about analysis coverage"""
        try:
            with app.app_context():
                total_content = db.session.query(SavedContent).count()
                analyzed_content = db.session.query(ContentAnalysis).count()
                
                return {
                    'total_content': total_content,
                    'analyzed_content': analyzed_content,
                    'coverage_percentage': (analyzed_content / total_content * 100) if total_content > 0 else 0,
                    'pending_analysis': total_content - analyzed_content
                }
        except Exception as e:
            logger.error(f"Error getting analysis stats: {e}")
            return {}

# Global instance
background_service = BackgroundAnalysisService()

def start_background_service():
    """Start the background analysis service"""
    background_service.start_background_analysis()

def stop_background_service():
    """Stop the background analysis service"""
    background_service.stop_background_analysis()

if __name__ == "__main__":
    print("Starting Background Analysis Service...")
    start_background_service()
    
    try:
        # Keep the service running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Background Analysis Service...")
        stop_background_service()
        print("Service stopped.") 