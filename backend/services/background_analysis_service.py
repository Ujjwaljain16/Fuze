#!/usr/bin/env python3
"""
Background Analysis Service for Gemini Content Analysis
Implements fair round-robin multi-tenant scheduling, Redis TTL failure tracking,
NOT EXISTS query optimization, and cost-optimized single-pass summary generation.
"""

import time
import os
import sys
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import exists
from core.logging_config import get_logger

logger = get_logger(__name__)

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, SavedContent, ContentAnalysis
from utils.gemini_utils import GeminiAnalyzer
from utils.redis_utils import RedisCache
from core.distributed_lock import DistributedLock

_app_instance = None


def get_app():
    """Get Flask app instance, creating if necessary."""
    global _app_instance

    if _app_instance is not None:
        return _app_instance

    try:
        from flask import has_app_context, current_app
        if has_app_context():
            _app_instance = current_app._get_current_object()
            return _app_instance
    except Exception:
        pass

    try:
        from run_production import app
        _app_instance = app
        return app
    except (ImportError, AttributeError):
        try:
            from run_production import create_app
            _app_instance = create_app()
            return _app_instance
        except Exception as e:
            logger.error("bg_analysis_get_app_failed", extra={"error": str(e)})
            raise


class BackgroundAnalysisService:
    """Service to analyze content in the background with Redis failure tracking and fair scheduling."""

    def __init__(self):
        self.redis_cache = RedisCache()
        self.running = False
        self.analysis_thread = None
        self._local_failed_analyses = set()

    @property
    def failed_analyses(self):
        """Backward compatible property access to local failed analyses set."""
        return self._local_failed_analyses

    def start_background_analysis(self):
        """Start or restart the background analysis thread if dead."""
        if self.running and self.analysis_thread and self.analysis_thread.is_alive():
            logger.info("bg_analysis_service_already_running")
            return

        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.analysis_thread.start()
        logger.info("bg_analysis_service_started")

    def stop_background_analysis(self):
        """Stop the background analysis thread."""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        logger.info("bg_analysis_service_stopped")

    def _is_failed(self, content_id: int) -> bool:
        """Check if content ID failed recently using Redis 24h TTL."""
        if not self.redis_cache or not self.redis_cache.connected:
            return content_id in self._local_failed_analyses

        try:
            return bool(self.redis_cache.get_cache(f"fuze:bg_analysis:failed:{content_id}"))
        except Exception:
            return content_id in self._local_failed_analyses

    def _mark_failed(self, content_id: int):
        """Mark content ID as failed in Redis with 24h TTL."""
        if self.redis_cache and self.redis_cache.connected:
            try:
                self.redis_cache.set_cache(f"fuze:bg_analysis:failed:{content_id}", "1", ttl=86400)
            except Exception:
                self._local_failed_analyses.add(content_id)
        else:
            self._local_failed_analyses.add(content_id)

    def _analysis_worker(self):
        """Background worker that continuously checks for unanalyzed content."""
        while self.running:
            try:
                flask_app = get_app()
                with flask_app.app_context():
                    lock = DistributedLock("background_analysis", ttl_ms=300000)
                    if lock.acquire():
                        try:
                            self._process_unanalyzed_content()
                        finally:
                            lock.release()
                    else:
                        logger.debug("bg_analysis_worker_lock_skipped")
                time.sleep(30)
            except Exception as e:
                logger.error("bg_analysis_worker_exception", extra={"error": str(e)})
                time.sleep(60)

    def _process_unanalyzed_content(self):
        """Process content that hasn't been analyzed yet with round-robin multi-user fairness."""
        try:
            try:
                db.session.execute(db.text('SELECT 1'))
            except Exception as conn_error:
                logger.warning("bg_analysis_db_check_failed", extra={"error": str(conn_error)})
                return

            unanalyzed_content = self._get_unanalyzed_content()
            if not unanalyzed_content:
                return

            logger.info("bg_analysis_items_found", extra={"count": len(unanalyzed_content)})

            processed = 0
            for content in unanalyzed_content:
                try:
                    if hasattr(content, 'user_id'):
                        progress_key = f"analysis_progress:{content.user_id}"
                        self.redis_cache.set_cache(progress_key, {
                            'status': 'analyzing',
                            'current_item': content.title[:50] if hasattr(content, 'title') else 'Unknown',
                            'last_updated': datetime.now().isoformat()
                        }, ttl=3600)

                    self._analyze_single_content(content)
                    processed += 1
                    time.sleep(3.0)

                except Exception as e:
                    logger.error("bg_analysis_single_item_failed", extra={"content_id": content.id, "error": str(e)})
                    db.session.rollback()
                    self._mark_failed(content.id)

        except Exception as e:
            logger.error("bg_analysis_process_failed", extra={"error": str(e)})
            db.session.rollback()

    def _get_unanalyzed_content(self) -> List[SavedContent]:
        """
        Query unanalyzed content using an efficient SQL NOT EXISTS clause.
        Groups content using fair round-robin scheduling across users.
        """
        try:
            subq = exists().where(ContentAnalysis.content_id == SavedContent.id)
            query = db.session.query(SavedContent).filter(
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != '',
                ~subq
            ).order_by(SavedContent.saved_at.desc())

            raw_unanalyzed = query.limit(50).all()
            filtered = [c for c in raw_unanalyzed if not self._is_failed(c.id)]

            if not filtered:
                return []

            # Round-robin scheduling across users
            user_groups: Dict[int, List[SavedContent]] = {}
            for content in filtered:
                user_groups.setdefault(content.user_id, []).append(content)

            fair_batch = []
            max_per_user = 3
            user_ids = list(user_groups.keys())

            for i in range(max_per_user):
                for uid in user_ids:
                    if i < len(user_groups[uid]):
                        fair_batch.append(user_groups[uid][i])

            return fair_batch[:15]

        except Exception as e:
            logger.error("bg_analysis_get_unanalyzed_failed", extra={"error": str(e)})
            db.session.rollback()
            return []

    def _analyze_single_content(self, content: SavedContent, user_id: Optional[int] = None):
        """Analyze a single content item without mutating ORM fields or making duplicate LLM calls."""
        try:
            logger.info("bg_analysis_analyzing_content", extra={"content_id": content.id, "user_id": content.user_id})

            text_to_analyze = content.extracted_text or content.title or content.url or "Untitled content"
            target_user_id = user_id or content.user_id
            api_key = None

            if target_user_id:
                try:
                    from services.multi_user_api_manager import get_user_api_key, check_user_rate_limit, record_user_request
                    rate_status = check_user_rate_limit(target_user_id)
                    if not rate_status.get('can_make_request', True):
                        logger.warning("bg_analysis_rate_limited", extra={"user_id": target_user_id})
                        return

                    api_key = get_user_api_key(target_user_id)
                except Exception as e:
                    logger.warning("bg_analysis_api_key_failed", extra={"user_id": target_user_id, "error": str(e)})

            gemini_analyzer = GeminiAnalyzer(api_key=api_key)

            # Single primary Gemini analysis call
            analysis_result = gemini_analyzer.analyze_bookmark_content(
                title=content.title or "Untitled",
                description=content.notes or "",
                content=text_to_analyze,
                url=content.url
            )

            if target_user_id and api_key:
                try:
                    from services.multi_user_api_manager import record_user_request
                    record_user_request(target_user_id)
                except Exception:
                    pass

            if not analysis_result:
                logger.warning("bg_analysis_empty_result", extra={"content_id": content.id})
                self._mark_failed(content.id)
                return

            # Single-pass summary (avoids second LLM call cost doubling)
            basic_summary = analysis_result.get('summary') or analysis_result.get('brief_summary')
            if not basic_summary:
                techs = ', '.join(analysis_result.get('technologies', [])[:3]) or 'topics'
                basic_summary = f"Content focused on {techs} from {content.title or 'source'}."

            analysis_result['basic_summary'] = basic_summary

            # Check existing analysis to avoid race conditions
            existing_analysis = db.session.query(ContentAnalysis).filter_by(content_id=content.id).first()
            if existing_analysis:
                logger.debug("bg_analysis_duplicate_skipped", extra={"content_id": content.id})
                return

            key_concepts = analysis_result.get('key_concepts', [])
            content_type = analysis_result.get('content_type', 'article')
            difficulty_level = analysis_result.get('difficulty', 'intermediate')
            technology_tags = analysis_result.get('technologies', [])
            relevance_score = analysis_result.get('relevance_score', 50)

            analysis = ContentAnalysis(
                content_id=content.id,
                analysis_data=analysis_result,
                key_concepts=', '.join(key_concepts) if isinstance(key_concepts, list) else str(key_concepts),
                content_type=content_type,
                difficulty_level=difficulty_level,
                technology_tags=', '.join(technology_tags) if isinstance(technology_tags, list) else str(technology_tags),
                relevance_score=relevance_score
            )

            try:
                db.session.add(analysis)
                db.session.commit()
            except Exception as db_err:
                db.session.rollback()
                if 'unique' in str(db_err).lower() or 'duplicate' in str(db_err).lower():
                    logger.debug("bg_analysis_unique_constraint_race_handled", extra={"content_id": content.id})
                    return
                raise

            # Cache in Redis
            cache_key = f"content_analysis:{content.id}"
            self.redis_cache.set_cache(cache_key, analysis_result, ttl=86400)

            try:
                from services.cache_invalidation_service import cache_invalidator
                cache_invalidator.after_analysis_complete(content.id, content.user_id)
                self.redis_cache.invalidate_user_recommendations(content.user_id)
            except Exception as inv_err:
                logger.warning("bg_analysis_cache_invalidation_error", extra={"error": str(inv_err)})

            logger.info("bg_analysis_completed_successfully", extra={"content_id": content.id})

        except Exception as e:
            logger.error("bg_analysis_single_content_exception", extra={"content_id": content.id, "error": str(e)})
            db.session.rollback()
            self._mark_failed(content.id)

    def get_cached_analysis(self, content_id: int) -> Optional[Dict]:
        """Get cached analysis for a content item."""
        try:
            cache_key = f"content_analysis:{content_id}"
            cached_result = self.redis_cache.get_cache(cache_key)
            if cached_result:
                return cached_result

            flask_app = get_app()
            with flask_app.app_context():
                analysis = db.session.query(ContentAnalysis).filter_by(content_id=content_id).first()
                if analysis:
                    self.redis_cache.set_cache(cache_key, analysis.analysis_data, ttl=86400)
                    return analysis.analysis_data
            return None
        except Exception as e:
            logger.error("bg_analysis_get_cached_failed", extra={"content_id": content_id, "error": str(e)})
            return None

    def analyze_content_immediately(self, content_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """Analyze content immediately (user-triggered)."""
        try:
            flask_app = get_app()
            with flask_app.app_context():
                content = db.session.query(SavedContent).filter_by(id=content_id).first()
                if not content:
                    logger.error("bg_analysis_content_not_found", extra={"content_id": content_id})
                    return None

                target_user_id = user_id or content.user_id
                self._analyze_single_content(content, user_id=target_user_id)
                return self.get_cached_analysis(content_id)
        except Exception as e:
            logger.error("bg_analysis_immediate_failed", extra={"content_id": content_id, "error": str(e)})
            return None


# Global singleton instance
background_service = BackgroundAnalysisService()


def start_background_service():
    background_service.start_background_analysis()


def stop_background_service():
    background_service.stop_background_analysis()


def analyze_content(content_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
    return background_service.analyze_content_immediately(content_id, user_id)