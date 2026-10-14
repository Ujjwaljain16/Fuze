#!/usr/bin/env python3
"""
Content analysis for one bookmark: one LLM call produces the content profile that is stored and embedded.
Run by the RQ job `analyze_bookmark_task` (see services/bookmark_processing_service.py); the pipeline
reconciler decides which bookmarks are due, so nothing here loops or schedules.
"""

import time
import os
import sys
from datetime import datetime
from typing import Dict, Optional
from core.logging_config import get_logger

logger = get_logger(__name__)

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from models import db, SavedContent, ContentAnalysis
from core.job_timeout import JobTimeoutException
from utils.gemini_utils import GeminiAnalyzer
from utils.redis_utils import RedisCache

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
    """Analyzes a single bookmark with the configured LLM and stores the result."""

    def __init__(self):
        self.redis_cache = RedisCache()

    def _analyze_single_content(self, content: SavedContent, user_id: Optional[int] = None, pipeline_run_id: Optional[str] = None):
        """Analyze a single content item without mutating ORM fields or making duplicate LLM calls."""
        from utils.event_bus import publish_pipeline_event, generate_pipeline_run_id
        run_id = pipeline_run_id or generate_pipeline_run_id()
        target_user_id = user_id or content.user_id
        analysis_announced = False

        try:
            logger.info("bg_analysis_analyzing_content", extra={"content_id": content.id, "user_id": target_user_id, "run_id": run_id})

            start_time = time.time()
            text_to_analyze = content.extracted_text or content.title or content.url or "Untitled content"
            api_key = None

            if target_user_id:
                try:
                    from services.multi_user_api_manager import get_user_api_key, check_user_rate_limit
                    rate_status = check_user_rate_limit(target_user_id)
                    if not rate_status.get('can_make_request', True):
                        logger.warning("bg_analysis_rate_limited", extra={"user_id": target_user_id})
                        publish_pipeline_event(
                            event_type="bookmark.pipeline.analysis.failed",
                            bookmark_id=content.id,
                            user_id=target_user_id,
                            pipeline_run_id=run_id,
                            sequence=6,
                            error={"error_code": "RATE_LIMIT_EXCEEDED", "retryable": True}
                        )
                        return

                    api_key = get_user_api_key(target_user_id)
                    if api_key == '':
                        # Their daily share of the shared key is used up: leave it PENDING.
                        logger.info("bg_analysis_deferred_no_key_allowance", extra={"user_id": target_user_id})
                        return
                    from core import gemini_quota
                    wait = gemini_quota.cooldown_seconds(api_key or os.environ.get('GEMINI_API_KEY'))
                    if wait > 0:
                        # Google said this key is out of quota until later: leave it PENDING (not
                        # FAILED, not a try) and let the reconciler come back after the reset.
                        logger.info("bg_analysis_deferred_quota_cooldown", extra={"user_id": target_user_id, "wait_seconds": wait})
                        return
                except Exception as e:
                    logger.warning("bg_analysis_api_key_failed", extra={"user_id": target_user_id, "error": str(e)})

            # Stage 3 started: announced only once the analysis will really run (a deferred one
            # would otherwise leave the live "analyzing" counter up with no event to bring it down).
            publish_pipeline_event(
                event_type="bookmark.pipeline.analysis.started",
                bookmark_id=content.id,
                user_id=target_user_id,
                pipeline_run_id=run_id,
                sequence=5
            )
            analysis_announced = True

            gemini_analyzer = GeminiAnalyzer(api_key=api_key)

            # Single Gemini call: structured content profile (no heuristic fallback)
            from services.content_profile import generate_profile
            analysis_result = generate_profile(
                gemini_analyzer,
                title=content.title or "",
                url=content.url or "",
                notes=content.notes or "",
                text=text_to_analyze,
            )
            analysis_duration_ms = round((time.time() - start_time) * 1000)

            if target_user_id and api_key:
                try:
                    from services.multi_user_api_manager import record_user_request
                    record_user_request(target_user_id)
                except Exception:
                    pass

            if not analysis_result:
                from core import gemini_quota
                stopped_by = getattr(gemini_analyzer, 'last_failure', None)
                if gemini_quota.cooldown_seconds(api_key or os.environ.get('GEMINI_API_KEY')) > 0:
                    stopped_by = 'quota'
                if stopped_by in ('quota', 'unavailable'):
                    # The model was out of quota or unreachable (a DNS blip, a provider outage):
                    # nothing is wrong with this bookmark. Stays PENDING so a later pass retries it,
                    # instead of a FAILED that then waits an hour or more.
                    logger.info("bg_analysis_stopped_by_provider", extra={"content_id": content.id, "reason": stopped_by})
                    publish_pipeline_event(
                        event_type="bookmark.pipeline.analysis.failed",
                        bookmark_id=content.id,
                        user_id=target_user_id,
                        pipeline_run_id=run_id,
                        sequence=6,
                        error={"error_code": "QUOTA_EXHAUSTED" if stopped_by == 'quota' else "PROVIDER_UNAVAILABLE",
                               "retryable": True}
                    )
                    return
                logger.warning("bg_analysis_empty_result", extra={"content_id": content.id})
                content.analysis_status = 'FAILED'
                db.session.commit()
                publish_pipeline_event(
                    event_type="bookmark.pipeline.analysis.failed",
                    bookmark_id=content.id,
                    user_id=target_user_id,
                    pipeline_run_id=run_id,
                    sequence=6,
                    error={"error_code": "ANALYSIS_FAILED", "retryable": True}
                )
                return

            from services.content_profile import analysis_payload, index_profile_chunk, store_profile
            store_profile(db.session, content, analysis_result, getattr(gemini_analyzer, 'active_model_name', None))
            content.analysis_status = 'SUCCESS'
            content.analyzed_at = datetime.utcnow()
            try:
                db.session.commit()
            except Exception as db_err:
                db.session.rollback()
                if 'unique' in str(db_err).lower() or 'duplicate' in str(db_err).lower():
                    logger.debug("bg_analysis_unique_constraint_race_handled", extra={"content_id": content.id})
                    return
                raise

            try:
                index_profile_chunk(db.session, content.id, content.user_id, content.title or "", analysis_result)
                db.session.commit()
            except Exception as chunk_err:
                db.session.rollback()
                logger.warning("bg_profile_chunk_index_failed", extra={"content_id": content.id, "error": str(chunk_err)})

            analysis_result = analysis_payload(analysis_result, getattr(gemini_analyzer, 'active_model_name', None))

            # Cache in Redis
            cache_key = f"content_analysis:{content.id}"
            self.redis_cache.set_cache(cache_key, analysis_result, ttl=86400)

            try:
                from services.cache_invalidation_service import cache_invalidator
                cache_invalidator.after_analysis_complete(content.id, content.user_id)
                self.redis_cache.invalidate_user_recommendations(content.user_id)
            except Exception as inv_err:
                logger.warning("bg_analysis_cache_invalidation_error", extra={"error": str(inv_err)})

            publish_pipeline_event(
                event_type="bookmark.pipeline.analysis.completed",
                bookmark_id=content.id,
                user_id=target_user_id,
                pipeline_run_id=run_id,
                sequence=6,
                data={"duration_ms": analysis_duration_ms}
            )
            logger.info("bg_analysis_completed_successfully", extra={"content_id": content.id, "duration_ms": analysis_duration_ms})

        except JobTimeoutException:
            db.session.rollback()
            if analysis_announced:
                publish_pipeline_event(
                    event_type="bookmark.pipeline.analysis.failed",
                    bookmark_id=content.id,
                    user_id=target_user_id,
                    pipeline_run_id=run_id,
                    sequence=6,
                    error={"error_code": "ANALYSIS_TIMEOUT", "retryable": True}
                )
            raise
        except Exception as e:
            logger.error("bg_analysis_single_content_exception", extra={"content_id": content.id, "error": str(e)})
            db.session.rollback()
            if analysis_announced:
                publish_pipeline_event(
                    event_type="bookmark.pipeline.analysis.failed",
                    bookmark_id=content.id,
                    user_id=target_user_id,
                    pipeline_run_id=run_id,
                    sequence=6,
                    error={"error_code": "ANALYSIS_FAILED", "retryable": True}
                )

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
        except JobTimeoutException:
            raise
        except Exception as e:
            logger.error("bg_analysis_immediate_failed", extra={"content_id": content_id, "error": str(e)})
            return None


# Global singleton instance
background_service = BackgroundAnalysisService()


def analyze_content(content_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
    return background_service.analyze_content_immediately(content_id, user_id)