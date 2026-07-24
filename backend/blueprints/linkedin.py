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
from core.logging_config import get_logger

logger = get_logger(__name__)

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

def extract_json_from_response(text: str) -> dict:
    """Safely extract JSON dictionary from LLM response strings including markdown code blocks."""
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith('```'):
        lines = cleaned.splitlines()
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        cleaned = '\n'.join(lines).strip()
    try:
        res = json.loads(cleaned)
        return res if isinstance(res, dict) else {}
    except Exception:
        return {}


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

        # Store or update extraction record in SavedContent
        try:
            content_rec = SavedContent.query.filter_by(
                user_id=user_id,
                url=linkedin_url
            ).first()

            if not content_rec:
                content_rec = SavedContent(
                    user_id=user_id,
                    url=linkedin_url,
                    title=extracted_data.get('title', 'LinkedIn Post'),
                    source='linkedin',
                    category='linkedin',
                    extracted_text=extracted_data.get('content', ''),
                    quality_score=extracted_data.get('quality_score', 0)
                )
                db.session.add(content_rec)
            else:
                content_rec.title = extracted_data.get('title') or content_rec.title
                content_rec.extracted_text = extracted_data.get('content') or content_rec.extracted_text
                content_rec.quality_score = extracted_data.get('quality_score', content_rec.quality_score)

            db.session.commit()
            logger.info("linkedin_extract_saved", user_id=user_id, content_id=content_rec.id)

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
                'extracted_at': datetime.utcnow().isoformat()
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

        gemini_analyzer = GeminiAnalyzer(api_key=api_key)

        analysis_prompt = f"""
        Analyze this LinkedIn post content and provide structured insights:
        Title: {title}
        Meta Description: {meta_description}
        Content: {content}
        URL: {url}

        Return JSON format:
        {{
            "technologies": ["list"],
            "content_type": "tutorial|article|news|case_study|opinion|other",
            "difficulty_level": "beginner|intermediate|advanced",
            "learning_goals": "summary",
            "summary": "2-3 sentence summary",
            "key_insights": ["insights"],
            "target_audience": "audience",
            "practical_applications": "applications"
        }}
        """

        try:
            analysis_response = gemini_analyzer.analyze_text(analysis_prompt)
            analysis_data = extract_json_from_response(analysis_response) if analysis_response else {}
        except Exception:
            logger.exception("linkedin_ai_analysis_failed", user_id=user_id)
            analysis_data = {}

        if not analysis_data:
            analysis_data = {
                'technologies': [],
                'content_type': 'linkedin_post',
                'difficulty_level': 'intermediate',
                'learning_goals': 'Content from LinkedIn post',
                'summary': f'LinkedIn post: {title[:100]}',
                'key_insights': ['Content extracted successfully'],
                'target_audience': 'General audience',
                'practical_applications': 'Learning and reference'
            }

        try:
            content_rec = SavedContent.query.filter_by(
                user_id=user_id,
                url=url
            ).first()

            if not content_rec:
                content_rec = SavedContent(
                    user_id=user_id,
                    url=url,
                    title=title or 'LinkedIn Post',
                    source='linkedin',
                    category='linkedin',
                    extracted_text=content
                )
                db.session.add(content_rec)
                db.session.flush()

            analysis_rec = ContentAnalysis.query.filter_by(content_id=content_rec.id).first()
            if not analysis_rec:
                analysis_rec = ContentAnalysis(
                    content_id=content_rec.id,
                    analysis_data=analysis_data,
                    content_type=analysis_data.get('content_type', 'linkedin_post'),
                    difficulty_level=analysis_data.get('difficulty_level', 'intermediate'),
                    technology_tags=','.join(analysis_data.get('technologies', []))
                )
                db.session.add(analysis_rec)
            else:
                analysis_rec.analysis_data = analysis_data
                analysis_rec.content_type = analysis_data.get('content_type', 'linkedin_post')
                analysis_rec.difficulty_level = analysis_data.get('difficulty_level', 'intermediate')
                analysis_rec.technology_tags = ','.join(analysis_data.get('technologies', []))

            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            logger.exception("linkedin_analysis_db_failed", user_id=user_id)

        return jsonify({
            'success': True,
            'message': 'LinkedIn content analyzed successfully',
            'data': {
                'technologies': analysis_data.get('technologies', []),
                'content_type': analysis_data.get('content_type', 'article'),
                'difficulty_level': analysis_data.get('difficulty_level', 'intermediate'),
                'learning_goals': analysis_data.get('learning_goals', ''),
                'summary': analysis_data.get('summary', ''),
                'key_insights': analysis_data.get('key_insights', []),
                'target_audience': analysis_data.get('target_audience', ''),
                'practical_applications': analysis_data.get('practical_applications', ''),
                'analyzed_at': datetime.utcnow().isoformat()
            }
        }), 200

    except Exception:
        logger.exception("linkedin_analysis_endpoint_failed")
        return jsonify({'success': False, 'error': 'Internal server error during LinkedIn analysis'}), 500


@linkedin_bp.route('/api/linkedin/batch-extract', methods=['POST'])
@jwt_required()
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

        scraper = EasyLinkedInScraper()
        results = []
        successful = 0
        failed = 0

        for url in urls:
            url_str = (url or '').strip()
            if not validate_linkedin_url(url_str):
                results.append({'url': url_str, 'success': False, 'error': 'Invalid LinkedIn URL'})
                failed += 1
                continue

            try:
                extracted = scraper.scrape_post(url_str)
                if extracted and extracted.get('success'):
                    results.append({
                        'url': url_str,
                        'success': True,
                        'data': {
                            'title': extracted.get('title'),
                            'content': extracted.get('content'),
                            'quality_score': extracted.get('quality_score', 0),
                            'method_used': extracted.get('method_used', '')
                        }
                    })
                    successful += 1
                else:
                    results.append({'url': url_str, 'success': False, 'error': 'Extraction failed'})
                    failed += 1
            except Exception:
                logger.exception("linkedin_batch_url_failed", user_id=user_id)
                results.append({'url': url_str, 'success': False, 'error': 'Extraction failed'})
                failed += 1

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

        history_data = []
        for record in records:
            try:
                analysis = ContentAnalysis.query.filter_by(content_id=record.id).first()
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
                    'extracted_at': record.saved_at.isoformat() if record.saved_at else None,
                    'analyzed_at': analysis.updated_at.isoformat() if (analysis and analysis.updated_at) else None,
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
                    'last_checked': datetime.utcnow().isoformat()
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
