"""
LinkedIn API Blueprint
Handles LinkedIn post content extraction, AI analysis, history, and bookmark integration.
"""

import json
from datetime import datetime
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

from models import db, SavedContent, ContentAnalysis
from scrapers.easy_linkedin_scraper import EasyLinkedInScraper
from utils.gemini_utils import GeminiAnalyzer
from middleware.rate_limiting import limiter
from core.logging_config import get_logger
from concurrent.futures import ThreadPoolExecutor
from utils.timefmt import iso_utc

logger = get_logger(__name__)

BATCH_FETCH_CONCURRENCY = 5

linkedin_bp = Blueprint('linkedin', __name__)

ALLOWED_LINKEDIN_DOMAINS = {'linkedin.com', 'www.linkedin.com', 'm.linkedin.com'}

def validate_linkedin_url(url: str) -> bool:
    """Validate that the URL belongs to LinkedIn and uses HTTP/HTTPS."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        netloc = parsed.netloc.lower()
        return netloc in ALLOWED_LINKEDIN_DOMAINS
    except Exception:
        return False

def _store_linkedin_post(user_id: int, url: str, title: str, text: str, quality_score: int = 0) -> int:
    """Upsert a LinkedIn post as a bookmark whose content is already fetched, and request its
    embedding. These rows used to skip the pipeline entirely, so they were never embedded and
    never showed up in search or recommendations."""
    from scrapers.models import compute_content_hash
    from services.pipeline_orchestrator import PipelineOrchestrator

    text = (text or '').replace('\x00', '')
    content_rec = SavedContent.query.filter_by(user_id=user_id, url=url).first()
    if not content_rec:
        content_rec = SavedContent(user_id=user_id, url=url, title=title or 'LinkedIn Post',
                                   source='linkedin', category='linkedin')
        db.session.add(content_rec)
    elif title:
        content_rec.title = title
    if text:
        content_rec.extracted_text = text
        content_rec.content_hash = compute_content_hash(text)
    content_rec.quality_score = quality_score or content_rec.quality_score or 0
    content_rec.scrape_status = 'SUCCESS'
    content_rec.scraped_at = datetime.utcnow()
    content_rec.strategy_used = 'LINKEDIN'
    db.session.commit()
    PipelineOrchestrator().request_embedding(content_rec.id, user_id)
    return content_rec.id


@linkedin_bp.route('/api/linkedin/extract', methods=['POST'])
@jwt_required()
def extract_linkedin_content():
    """Extract content from LinkedIn post URL."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        linkedin_url = data.get('url', '').strip()
        if not linkedin_url:
            return jsonify({'success': False, 'error': 'LinkedIn URL is required'}), 400

        if not validate_linkedin_url(linkedin_url):
            return jsonify({'success': False, 'error': 'Please provide a valid LinkedIn URL'}), 400

        logger.info("linkedin_extract_started", user_id=user_id)

        # Per-request thread-safe scraper instance
        scraper = EasyLinkedInScraper()
        extracted_data = scraper.scrape_post(linkedin_url)

        if not extracted_data or not extracted_data.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to extract content from LinkedIn post'
            }), 400

        try:
            content_id = _store_linkedin_post(user_id, linkedin_url, extracted_data.get('title'),
                                              extracted_data.get('content', ''), extracted_data.get('quality_score', 0))
            logger.info("linkedin_extract_saved", user_id=user_id, content_id=content_id)
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("linkedin_extract_db_failed", user_id=user_id)

        return jsonify({
            'success': True,
            'message': 'LinkedIn content extracted successfully',
            'data': {
                'title': extracted_data.get('title'),
                'content': extracted_data.get('content'),
                'meta_description': extracted_data.get('meta_description', ''),
                'quality_score': extracted_data.get('quality_score', 0),
                'method_used': extracted_data.get('method_used', ''),
                'technologies': extracted_data.get('technologies', []),
                'extracted_at': iso_utc(datetime.utcnow())
            }
        }), 200

    except Exception:
        logger.exception("linkedin_extract_endpoint_failed")
        return jsonify({'success': False, 'error': 'Internal server error during LinkedIn extraction'}), 500


@linkedin_bp.route('/api/linkedin/analyze', methods=['POST'])
@jwt_required()
def analyze_linkedin_content():
    """Analyze extracted LinkedIn content using AI."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        content = data.get('content', '').strip()
        if not content:
            return jsonify({'success': False, 'error': 'Content is required for analysis'}), 400

        title = data.get('title', '')
        meta_description = data.get('meta_description', '')
        url = data.get('url', '')

        # Validate Gemini API Key immediately
        from services.multi_user_api_manager import get_user_api_key
        api_key = get_user_api_key(user_id)
        if not api_key:
            return jsonify({'success': False, 'error': 'Gemini API key required for analysis'}), 400

        # The same structured content profile every other bookmark gets. There used to be a call to
        # a method that doesn't exist, caught, followed by a canned "analysis" stored as if Gemini
        # had written it.
        from services.content_profile import analysis_payload, generate_profile, store_profile
        gemini_analyzer = GeminiAnalyzer(api_key=api_key)
        profile = generate_profile(gemini_analyzer, title=title, url=url, notes=meta_description, text=content)
        if profile is None:
            return jsonify({'success': False, 'error': 'Analysis is unavailable right now. Please try again.'}), 502

        try:
            content_id = _store_linkedin_post(user_id, url, title, content)
            content_rec = db.session.get(SavedContent, content_id)
            store_profile(db.session, content_rec, profile, gemini_analyzer.active_model_name)
            content_rec.analysis_status = 'SUCCESS'
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("linkedin_analysis_db_failed", user_id=user_id)

        return jsonify({
            'success': True,
            'message': 'LinkedIn content analyzed successfully',
            'data': {**analysis_payload(profile, gemini_analyzer.active_model_name),
                     'analyzed_at': iso_utc(datetime.utcnow())},
        }), 200

    except Exception:
        logger.exception("linkedin_analysis_endpoint_failed")
        return jsonify({'success': False, 'error': 'Internal server error during LinkedIn analysis'}), 500


@linkedin_bp.route('/api/linkedin/batch-extract', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def batch_extract_linkedin():
    """Extract content from multiple LinkedIn URLs."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        urls = data.get('urls', [])
        if not isinstance(urls, list) or len(urls) == 0:
            return jsonify({'success': False, 'error': 'List of LinkedIn URLs is required'}), 400

        if len(urls) > 10:
            return jsonify({'success': False, 'error': 'Maximum 10 URLs allowed per batch'}), 400

        logger.info("linkedin_batch_extract_started", user_id=user_id, count=len(urls))

        def extract_one(url_str):
            if not validate_linkedin_url(url_str):
                return {'url': url_str, 'success': False, 'error': 'Invalid LinkedIn URL'}
            try:
                extracted = EasyLinkedInScraper().scrape_post(url_str)
            except Exception:
                logger.exception("linkedin_batch_url_failed", user_id=user_id)
                return {'url': url_str, 'success': False, 'error': 'Extraction failed'}
            if not (extracted and extracted.get('success')):
                return {'url': url_str, 'success': False, 'error': 'Extraction failed'}
            return {
                'url': url_str,
                'success': True,
                'data': {
                    'title': extracted.get('title'),
                    'content': extracted.get('content'),
                    'quality_score': extracted.get('quality_score', 0),
                    'method_used': extracted.get('method_used', '')
                }
            }

        # Fetch concurrently: sequential fetching made the worst case (10 URLs x timeout) block one request for minutes.
        with ThreadPoolExecutor(max_workers=BATCH_FETCH_CONCURRENCY) as pool:
            results = list(pool.map(extract_one, [(u or '').strip() for u in urls]))
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        return jsonify({
            'success': True,
            'message': f'Batch extraction completed: {successful} successful, {failed} failed',
            'data': {
                'total_urls': len(urls),
                'successful': successful,
                'failed': failed,
                'results': results
            }
        }), 200

    except Exception:
        logger.exception("linkedin_batch_extract_failed")
        return jsonify({'success': False, 'error': 'Internal server error during batch LinkedIn extraction'}), 500


@linkedin_bp.route('/api/linkedin/history', methods=['GET'])
@jwt_required()
def get_linkedin_history():
    """Get user's LinkedIn extraction and analysis history."""
    try:
        user_id = int(get_jwt_identity())
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))

        history_query = db.session.query(SavedContent).filter(
            SavedContent.user_id == user_id,
            (SavedContent.category == 'linkedin') | (SavedContent.source == 'linkedin')
        ).order_by(SavedContent.saved_at.desc())

        total_count = history_query.count()
        records = history_query.offset(offset).limit(limit).all()

        # Batch-load analyses in one query instead of one-per-record (was up to
        # `limit` extra round-trips per request).
        record_ids = [r.id for r in records]
        analyses_by_content_id = {
            a.content_id: a
            for a in ContentAnalysis.query.filter(ContentAnalysis.content_id.in_(record_ids)).all()
        } if record_ids else {}

        history_data = []
        for record in records:
            try:
                analysis = analyses_by_content_id.get(record.id)
                analysis_data = {}
                if analysis and analysis.analysis_data:
                    analysis_data = analysis.analysis_data if isinstance(analysis.analysis_data, dict) else json.loads(analysis.analysis_data)

                history_data.append({
                    'id': record.id,
                    'url': record.url,
                    'title': record.title,
                    'content_preview': (record.extracted_text[:200] + '...') if record.extracted_text and len(record.extracted_text) > 200 else (record.extracted_text or ''),
                    'technology_tags': (analysis.technology_tags.split(',') if analysis and analysis.technology_tags else []),
                    'quality_score': record.quality_score or 0,
                    'extracted_at': iso_utc(record.saved_at),
                    'analyzed_at': iso_utc(analysis.updated_at),
                    'extraction_method': 'linkedin_scraper',
                    'analysis_summary': analysis_data.get('summary', ''),
                    'content_type': 'linkedin_post'
                })
            except Exception:
                logger.exception("linkedin_history_record_parse_failed", record_id=record.id)
                continue

        return jsonify({
            'success': True,
            'data': {
                'history': history_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }
        }), 200

    except Exception:
        logger.exception("linkedin_history_failed")
        return jsonify({'success': False, 'error': 'Internal server error retrieving LinkedIn history'}), 500


@linkedin_bp.route('/api/linkedin/save-to-bookmarks', methods=['POST'])
@jwt_required()
def save_to_bookmarks():
    """Save LinkedIn extraction to user's bookmarks."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}
        extraction_id = data.get('extraction_id')

        if not extraction_id:
            return jsonify({'success': False, 'error': 'extraction_id is required'}), 400

        content_rec = SavedContent.query.filter_by(
            id=extraction_id,
            user_id=user_id
        ).first()

        if not content_rec:
            return jsonify({'success': False, 'error': 'Extraction not found'}), 404

        content_rec.category = 'linkedin'
        content_rec.tags = 'linkedin'
        db.session.commit()
        logger.info("linkedin_saved_to_bookmarks", user_id=user_id, bookmark_id=content_rec.id)

        return jsonify({
            'success': True,
            'message': 'Saved to bookmarks successfully',
            'bookmark_id': content_rec.id
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("linkedin_save_bookmark_failed")
        return jsonify({'success': False, 'error': 'Failed to save to bookmarks'}), 500


@linkedin_bp.route('/api/linkedin/extract/<int:extraction_id>', methods=['DELETE'])
@jwt_required()
def delete_extraction(extraction_id):
    """Delete a LinkedIn extraction."""
    try:
        user_id = int(get_jwt_identity())

        content_rec = SavedContent.query.filter_by(
            id=extraction_id,
            user_id=user_id
        ).first()

        if not content_rec:
            return jsonify({'success': False, 'error': 'Extraction not found'}), 404

        db.session.delete(content_rec)
        db.session.commit()
        logger.info("linkedin_extraction_deleted", user_id=user_id, extraction_id=extraction_id)

        return jsonify({'success': True, 'message': 'Extraction deleted successfully'}), 200

    except Exception:
        db.session.rollback()
        logger.exception("linkedin_delete_extraction_failed")
        return jsonify({'success': False, 'error': 'Failed to delete extraction'}), 500


@linkedin_bp.route('/api/linkedin/status', methods=['GET'])
def get_linkedin_status():
    """Get fast lightweight LinkedIn service operational status."""
    try:
        return jsonify({
            'success': True,
            'data': {
                'linkedin_scraper': {
                    'status': 'operational',
                    'allowed_domains': list(ALLOWED_LINKEDIN_DOMAINS),
                    'last_checked': iso_utc(datetime.utcnow())
                },
                'ai_analyzer': {
                    'status': 'operational',
                    'provider': 'gemini'
                },
                'overall_status': 'operational'
            }
        }), 200
    except Exception:
        logger.exception("linkedin_status_failed")
        return jsonify({'success': False, 'error': 'Internal server error checking LinkedIn status'}), 500
