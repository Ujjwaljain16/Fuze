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

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, SavedContent, ContentAnalysis
from utils.gemini_utils import GeminiAnalyzer
from utils.redis_utils import RedisCache

# Import app for app_context - use lazy import to avoid circular dependencies
_app_instance = None

def get_app():
    """Get Flask app instance, creating if necessary"""
    global _app_instance
    
    # Try to use cached instance first
    if _app_instance is not None:
        return _app_instance
    
    # Try to get from current_app (if in request context)
    try:
        from flask import has_app_context, current_app
        if has_app_context():
            _app_instance = current_app._get_current_object()
            return _app_instance
    except Exception:
        pass
    
    # Not in app context, try to import app directly
    try:
        from run_production import app
        _app_instance = app
        return app
    except (ImportError, AttributeError):
        # Last resort: create app context
        try:
            from run_production import create_app
            _app_instance = create_app()
            return _app_instance
        except Exception as e:
            logger.error(f"Failed to get Flask app: {e}")
            raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundAnalysisService:
    """Service to analyze content in the background and cache results"""
    
    def __init__(self):
        # Don't create analyzer here - create per-content with user's API key
        self.redis_cache = RedisCache()
        self.running = False
        self.analysis_thread = None
        self.failed_analyses = set()  # Track failed content IDs to avoid infinite retries
        self.current_user = None  # Track which user we're analyzing for
        
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
                flask_app = get_app()
                with flask_app.app_context():
                    self._process_unanalyzed_content()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in background analysis worker: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _process_unanalyzed_content(self):
        """Process content that hasn't been analyzed yet"""
        try:
            # Refresh database connection before processing
            try:
                db.session.execute(db.text('SELECT 1'))
            except Exception as conn_error:
                logger.warning(f"Database connection check failed, refreshing: {conn_error}")
                try:
                    db.session.close()
                    db.session.remove()
                except Exception:
                    pass
                return  # Skip this cycle if connection is bad
            
            # Find content without analysis
            unanalyzed_content = self._get_unanalyzed_content()

            if not unanalyzed_content:
                return

            logger.info(f"Found {len(unanalyzed_content)} items to analyze")

            # Update progress tracking
            total_items = len(unanalyzed_content)
            processed = 0

            for content in unanalyzed_content:
                try:
                    # Verify connection is still alive before each analysis
                    try:
                        db.session.execute(db.text('SELECT 1'))
                    except Exception as conn_error:
                        logger.warning(f"Connection lost during processing, refreshing: {conn_error}")
                        try:
                            db.session.close()
                            db.session.remove()
                        except Exception:
                            pass
                        break  # Exit loop and retry next cycle
                    
                    # Update progress for this user's content
                    if hasattr(content, 'user_id'):
                        progress_key = f"analysis_progress:{content.user_id}"
                        self.redis_cache.set_cache(progress_key, {
                            'status': 'analyzing',
                            'total': total_items,
                            'processed': processed,
                            'current_item': content.title[:50] if hasattr(content, 'title') else 'Unknown',
                            'last_updated': datetime.now().isoformat()
                        }, ttl=3600)

                    # Analyze the content (SQLAlchemy handles transactions automatically)
                    self._analyze_single_content(content)

                    processed += 1
                    
                    # Rate limiting between analyses (same as content_analysis_script.py default delay)
                    # Use 3 seconds default delay like the script, with adaptive delays for errors
                    delay = 3.0  # Base delay (same as script default)
                    if hasattr(self, '_last_api_error') and self._last_api_error:
                        delay = 5.0  # Longer delay after errors
                        self._last_api_error = False
                    time.sleep(delay)  # Rate limiting between analyses

                except Exception as e:
                    logger.error(f"Error analyzing content {content.id}: {e}")
                    # Check if it's a connection error
                    error_str = str(e).lower()
                    is_connection_error = any(keyword in error_str for keyword in [
                        'connection', 'closed', 'terminated', 'operationalerror',
                        'server closed', 'connection unexpectedly'
                    ])
                    
                    if is_connection_error:
                        logger.warning("Connection error detected, will retry next cycle")
                        try:
                            db.session.close()
                            db.session.remove()
                        except Exception:
                            pass
                        break  # Exit loop to retry next cycle
                    else:
                        db.session.rollback()  # Rollback on error
                        # Add to failed analyses to prevent infinite retries
                        self.failed_analyses.add(content.id)

            # Mark analysis as completed for this batch
            if unanalyzed_content and processed > 0 and hasattr(unanalyzed_content[0], 'user_id'):
                progress_key = f"analysis_progress:{unanalyzed_content[0].user_id}"
                self.redis_cache.set_cache(progress_key, {
                    'status': 'completed',
                    'total': total_items,
                    'processed': processed,
                    'completed_at': datetime.now().isoformat()
                }, ttl=3600)

        except Exception as e:
            logger.error(f"Error processing unanalyzed content: {e}")
            # Check if it's a connection error
            error_str = str(e).lower()
            is_connection_error = any(keyword in error_str for keyword in [
                'connection', 'closed', 'terminated', 'operationalerror',
                'server closed', 'connection unexpectedly'
            ])
            
            if is_connection_error:
                logger.warning("Connection error in _process_unanalyzed_content, will retry next cycle")
            else:
                db.session.rollback()  # Rollback on error
            
            # Always try to close/remove session on error
            try:
                db.session.close()
                db.session.remove()
            except Exception:
                pass
    
    def _get_unanalyzed_content(self) -> List[SavedContent]:
        """Get content that hasn't been analyzed yet"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Refresh database connection before query
                try:
                    db.session.close()  # Close any stale connections
                except Exception:
                    pass
                
                # Verify connection is alive
                try:
                    db.session.execute(db.text('SELECT 1'))
                except Exception as conn_error:
                    logger.warning(f"Database connection check failed (attempt {attempt + 1}): {conn_error}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise
                
                # Find content without corresponding analysis
                # Use a simpler query that works with both PostgreSQL and SQLite
                from sqlalchemy import select, text
                from sqlalchemy.exc import OperationalError
                
                # Get all analyzed content IDs (handle case where table doesn't exist)
                analyzed_ids_set = set()
                try:
                    analyzed_ids = db.session.query(ContentAnalysis.content_id).distinct().all()
                    analyzed_ids_set = {row[0] for row in analyzed_ids} if analyzed_ids else set()
                except (OperationalError, Exception) as e:
                    # Table doesn't exist or other error - assume no analyzed content
                    logger.debug(f"Could not query ContentAnalysis table: {e}")
                    analyzed_ids_set = set()
                
                # Query unanalyzed content
                query = db.session.query(SavedContent).filter(
                    SavedContent.extracted_text.isnot(None),
                    SavedContent.extracted_text != ''
                )
                
                # Filter out analyzed content
                if analyzed_ids_set:
                    query = query.filter(~SavedContent.id.in_(analyzed_ids_set))
                
                unanalyzed = query.limit(10).all()  # Process 10 at a time
                
                # Filter out previously failed analyses
                unanalyzed = [content for content in unanalyzed if content.id not in self.failed_analyses]
                
                # OPTIMIZATION: Group by user_id for batch processing
                # This allows us to use user-specific API keys more efficiently
                user_groups = {}
                for content in unanalyzed:
                    user_id = content.user_id
                    if user_id not in user_groups:
                        user_groups[user_id] = []
                    user_groups[user_id].append(content)
                
                # Return content grouped by user (process all of one user's content together)
                # This improves API key caching and reduces context switching
                if user_groups:
                    # Return first user's content batch
                    first_user_id = list(user_groups.keys())[0]
                    return user_groups[first_user_id]
                
                return unanalyzed
                
            except Exception as e:
                error_str = str(e).lower()
                is_connection_error = any(keyword in error_str for keyword in [
                    'connection', 'closed', 'terminated', 'operationalerror', 
                    'server closed', 'connection unexpectedly'
                ])
                
                if is_connection_error and attempt < max_retries - 1:
                    logger.warning(f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    
                    # Close session and wait before retry
                    try:
                        db.session.close()
                        db.session.remove()
                    except Exception:
                        pass
                    
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"Error getting unanalyzed content: {e}")
                    # Close session on final failure
                    try:
                        db.session.rollback()
                        db.session.close()
                    except Exception:
                        pass
                    return []
        
        return []
    
    def _analyze_single_content(self, content: SavedContent, user_id: int = None):
        """Analyze a single content item and store the result"""
        try:
            logger.info(f"Analyzing content: {content.title} for user {content.user_id}")
            
            # Check if we have the required fields - analyze even if empty
            # (We want to analyze all content regardless of quality or emptiness)
            if not content.extracted_text:
                # Use minimal fallback content for analysis
                content.extracted_text = content.title or content.url or "Untitled content"
            
            # Get user's API key and create analyzer (same as content_analysis_script.py)
            user_id = user_id or content.user_id
            api_key = None
            if user_id:
                try:
                    from services.multi_user_api_manager import get_user_api_key, check_user_rate_limit, record_user_request
                    
                    # Check rate limit before processing (same as content_analysis_script.py)
                    rate_limit_status = check_user_rate_limit(user_id)
                    if not rate_limit_status.get('can_make_request', True):
                        wait_time = rate_limit_status.get('wait_time_seconds', 60)
                        logger.warning(f"Rate limit exceeded for user {user_id}. Waiting {wait_time} seconds...")
                        import time
                        time.sleep(min(wait_time, 60))  # Wait up to 60 seconds
                        return  # Skip this item and try again later
                    
                    api_key = get_user_api_key(user_id)
                except Exception as e:
                    logger.warning(f"Could not get user API key for user {user_id}: {e}")
            
            # Create analyzer with user's key
            gemini_analyzer = GeminiAnalyzer(api_key=api_key)
            
            # Analyze with Gemini (same as content_analysis_script.py)
            analysis_result = gemini_analyzer.analyze_bookmark_content(
                title=content.title or "Untitled",
                description=content.notes or "",
                content=content.extracted_text,
                url=content.url
            )
            
            # Record API usage for rate limiting (same as content_analysis_script.py)
            if user_id and api_key:
                try:
                    from services.multi_user_api_manager import record_user_request
                    record_user_request(user_id)
                except Exception as record_error:
                    logger.warning(f"Could not record API usage: {record_error}")

            # Generate basic summary for instant display
            if analysis_result:
                basic_summary = self._generate_basic_summary(gemini_analyzer, content, analysis_result)
                analysis_result['basic_summary'] = basic_summary
            
            if not analysis_result:
                logger.warning(f"No analysis result for content {content.id}")
                return
            
            # Extract key information from analysis (same as content_analysis_script.py)
            key_concepts = analysis_result.get('key_concepts', [])
            content_type = analysis_result.get('content_type', 'article')  # Default to 'article' like script
            difficulty_level = analysis_result.get('difficulty', 'intermediate')  # Default to 'intermediate' like script
            technology_tags = analysis_result.get('technologies', [])
            relevance_score = analysis_result.get('relevance_score', 50)  # Default to 50 like script
            
            # Check if analysis already exists (prevent duplicates from race conditions)
            existing_analysis = db.session.query(ContentAnalysis).filter_by(content_id=content.id).first()
            if existing_analysis:
                logger.debug(f"Analysis already exists for content {content.id}, skipping duplicate")
                return
            
            # Create analysis record (same format as content_analysis_script.py)
            analysis = ContentAnalysis(
                content_id=content.id,
                analysis_data=analysis_result,
                key_concepts=', '.join(key_concepts) if isinstance(key_concepts, list) else str(key_concepts),
                content_type=content_type,
                difficulty_level=difficulty_level,
                technology_tags=', '.join(technology_tags) if isinstance(technology_tags, list) else str(technology_tags),
                relevance_score=relevance_score
            )
            
            # Save to database
            try:
                db.session.add(analysis)
                db.session.commit()
            except Exception as db_error:
                # Handle race condition - if another thread already created analysis
                error_str = str(db_error).lower()
                if 'unique' in error_str or 'duplicate' in error_str:
                    logger.debug(f"Analysis already exists for content {content.id} (race condition), skipping")
                    db.session.rollback()
                    return
                else:
                    # Re-raise if it's a different error
                    raise
            
            # Cache in Redis
            cache_key = f"content_analysis:{content.id}"
            self.redis_cache.set_cache(cache_key, analysis_result, ttl=86400)  # 24 hours
            
            # Invalidate caches using comprehensive cache invalidation service
            from services.cache_invalidation_service import cache_invalidator
            cache_invalidator.after_analysis_complete(content.id, content.user_id)
            
            # Also invalidate recommendation caches for this user
            try:
                from utils.redis_utils import redis_cache
                # Use the dedicated method for invalidating user recommendations
                redis_cache.invalidate_user_recommendations(content.user_id)
                logger.debug(f"Invalidated recommendation caches for user {content.user_id}")
            except Exception as e:
                logger.warning(f"Error invalidating recommendation caches: {e}")
            
            logger.info(f"✅ Analysis completed and stored for content {content.id}")

        except Exception as e:
            logger.error(f"Error analyzing content {content.id}: {e}")
            db.session.rollback()
            # Add to failed analyses to prevent infinite retries
            self.failed_analyses.add(content.id)

    def _generate_basic_summary(self, gemini_analyzer: GeminiAnalyzer, content: SavedContent, analysis_result: Dict) -> str:
        """Generate a basic summary for instant display during recommendations"""
        try:
            # Create a concise summary prompt
            summary_prompt = f"""
            Create a brief 2-3 sentence summary of this content for quick reference:

            Title: {content.title}
            Content: {content.extracted_text[:1000]}...  # First 1000 chars for context

            Key topics: {', '.join(analysis_result.get('technologies', []))}
            Content type: {analysis_result.get('content_type', 'article')}

            Summary should be:
            - 2-3 sentences maximum
            - Highlight the main value/proposition
            - Include key technologies mentioned
            - Suitable for quick scanning in recommendation lists
            """

            summary = gemini_analyzer._make_gemini_request(summary_prompt)
            if summary and len(summary.strip()) > 10:
                return summary.strip()
            else:
                # Fallback summary
                return f"Content about {', '.join(analysis_result.get('technologies', ['various topics'])[:3])}"

        except Exception as e:
            logger.error(f"Error generating basic summary for content {content.id}: {e}")
            # Return a simple fallback
            return f"Content about {content.title[:50]}..."
    
    def get_cached_analysis(self, content_id: int) -> Optional[Dict]:
        """Get cached analysis for a content item"""
        try:
            # Try Redis first
            cache_key = f"content_analysis:{content_id}"
            cached_result = self.redis_cache.get_cache(cache_key)
            
            if cached_result:
                return cached_result
            
            # Try database
            flask_app = get_app()
            with flask_app.app_context():
                analysis = db.session.query(ContentAnalysis).filter_by(content_id=content_id).first()
                if analysis:
                    # Cache in Redis for future use
                    self.redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                    return analysis.analysis_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached analysis for content {content_id}: {e}")
            return None
    
    def analyze_content_immediately(self, content_id: int, user_id: int = None) -> Optional[Dict]:
        """Analyze content immediately (for user-triggered analysis)"""
        try:
            flask_app = get_app()
            with flask_app.app_context():
                content = db.session.query(SavedContent).filter_by(id=content_id).first()
                if not content:
                    logger.error(f"Content {content_id} not found")
                    return None
                
                # Use provided user_id or content's user_id
                user_id = user_id or content.user_id
                self._analyze_single_content(content, user_id=user_id)
                
                # Return the analysis result
                return self.get_cached_analysis(content_id)
                
        except Exception as e:
            logger.error(f"Error in immediate analysis for content {content_id}: {e}")
            return None
    
    def get_analysis_stats(self) -> Dict:
        """Get statistics about analysis coverage"""
        try:
            flask_app = get_app()
            with flask_app.app_context():
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

def start_background_analysis_for_user(user_id: int) -> Dict:
    """Start background analysis for a specific user"""
    try:
        # Check if service is already running
        if background_service.running:
            return {
                'status': 'already_running',
                'message': 'Background analysis service is already running'
            }

        # Start the service
        background_service.start_background_analysis()

        return {
            'status': 'started',
            'message': 'Background analysis service started successfully'
        }
    except Exception as e:
        logger.error(f"Error starting background analysis for user {user_id}: {e}")
        return {
            'status': 'error',
            'message': f'Failed to start background analysis: {str(e)}'
        }

def analyze_content(content_id: int, user_id: int = None) -> Optional[Dict]:
    """Helper function to analyze content immediately"""
    return background_service.analyze_content_immediately(content_id, user_id)

def batch_analyze_content(content_ids: List[int], user_id: int = None) -> Dict:
    """Helper function to batch analyze content"""
    results = []
    for content_id in content_ids:
        try:
            result = background_service.analyze_content_immediately(content_id, user_id)
            if result:
                results.append({'content_id': content_id, 'success': True, 'result': result})
            else:
                results.append({'content_id': content_id, 'success': False, 'error': 'No result'})
        except Exception as e:
            logger.error(f"Error analyzing content {content_id}: {e}")
            results.append({'content_id': content_id, 'success': False, 'error': str(e)})
    
    return {
        'total': len(content_ids),
        'successful': len([r for r in results if r.get('success')]),
        'failed': len([r for r in results if not r.get('success')]),
        'results': results
    }

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