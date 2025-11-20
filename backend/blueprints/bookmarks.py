from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent, User
import requests
from readability import Document
from bs4 import BeautifulSoup
import numpy as np
from sqlalchemy.exc import IntegrityError
from scrapers.enhanced_web_scraper import scrape_url_enhanced
from urllib.parse import urlparse, urljoin, urlunparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.redis_utils import redis_cache
import logging

# Import embedding function
from utils.embedding_utils import get_embedding

logger = logging.getLogger(__name__)

bookmarks_bp = Blueprint('bookmarks', __name__, url_prefix='/api/bookmarks')

def normalize_url(url):
    """Normalize URL to handle different formats of the same URL"""
    if not url:
        return url
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Remove common tracking parameters
    parsed = urlparse(url)
    query_params = parsed.query.split('&') if parsed.query else []
    
    # Filter out common tracking parameters
    filtered_params = []
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 
                      'fbclid', 'gclid', 'ref', 'source', 'campaign']
    
    for param in query_params:
        if param:
            key = param.split('=')[0] if '=' in param else param
            if key.lower() not in tracking_params:
                filtered_params.append(param)
    
    # Reconstruct URL without tracking parameters
    clean_query = '&'.join(filtered_params) if filtered_params else ''
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        clean_query,
        ''  # Remove fragment
    ))
    
    return normalized.lower()

def is_duplicate_url(url, user_id):
    """Check if URL is a duplicate (exact match or normalized match)"""
    normalized_url = normalize_url(url)
    
    # Check exact match first
    existing_exact = SavedContent.query.filter_by(user_id=user_id, url=url).first()
    if existing_exact:
        return existing_exact, 'exact'
    
    # Check normalized match
    if normalized_url != url:
        existing_normalized = SavedContent.query.filter_by(user_id=user_id, url=normalized_url).first()
        if existing_normalized:
            return existing_normalized, 'normalized'
    
    # Check for similar URLs (same domain and path, different query params)
    parsed = urlparse(url)
    domain_path = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    # Find bookmarks with same domain and path
    similar_bookmarks = SavedContent.query.filter(
        SavedContent.user_id == user_id,
        SavedContent.url.like(f"{domain_path}%")
    ).all()
    
    for bookmark in similar_bookmarks:
        bookmark_parsed = urlparse(bookmark.url)
        bookmark_domain_path = f"{bookmark_parsed.scheme}://{bookmark_parsed.netloc}{bookmark_parsed.path}"
        
        if bookmark_domain_path == domain_path:
            return bookmark, 'similar'
    
    return None, None

def extract_article_content(url):
    """Extract main content, title, headings, and meta from a URL"""
    return scrape_url_enhanced(url)

@bookmarks_bp.route('', methods=['POST'])
@jwt_required()
def save_bookmark():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    url = data.get('url')
    title = data.get('title', '')
    description = data.get('description', '')  # Keep for API compatibility
    category = data.get('category', 'other')
    tags = data.get('tags', [])
    
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    # Check if bookmark already exists
    existing_bookmark, duplicate_type = is_duplicate_url(url, user_id)
    
    if existing_bookmark:
        # Update existing bookmark
        existing_bookmark.title = title.strip() if title else existing_bookmark.title
        existing_bookmark.notes = description.strip() if description else existing_bookmark.notes
        db.session.commit()
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_update(existing_bookmark.id, user_id)
        return jsonify({
            'message': 'Bookmark updated',
            'bookmark': {'id': existing_bookmark.id, 'url': existing_bookmark.url},
            'wasDuplicate': True,
            'duplicateType': duplicate_type
        }), 200
    
    # Ensure title is not empty (required field)
    if not title or not title.strip():
        title = 'Untitled Bookmark'
    
    # Extract content from URL (now returns dict)
    scraped = extract_article_content(url)
    extracted_text = scraped.get('content', '')
    scraped_title = scraped.get('title', '')
    headings = scraped.get('headings', [])
    meta_description = scraped.get('meta_description', '')
    quality_score = scraped.get('quality_score', 10)

    if quality_score < 5:
        return jsonify({'message': 'Content quality too low (login page, homepage, or too short). Please save a more content-rich page.'}), 400
    
    # Prefer scraped title if not provided
    if not title or title == 'Untitled Bookmark':
        title = scraped_title or 'Untitled Bookmark'
    
    # Generate embedding for semantic search
    content_for_embedding = f"{title} {description} {meta_description} {' '.join(headings)} {extracted_text}"
    embedding = get_embedding(content_for_embedding)
    
    new_bm = SavedContent(
        user_id=user_id,
        url=url.strip(),
        title=title.strip(),
        notes=description.strip() if isinstance(description, str) else '',
        extracted_text=extracted_text,
        embedding=embedding,
        quality_score=quality_score
        # Optionally: store headings/meta_description in new columns if desired
    )
    try:
        db.session.add(new_bm)
        db.session.commit()
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_save(new_bm.id, user_id)

        # Trigger background analysis for this new content (non-blocking)
        try:
            import threading
            def analyze_async():
                try:
                    from services.background_analysis_service import analyze_content
                    analyze_content(new_bm.id, user_id)
                except Exception as e:
                    logger.error(f"Error triggering background analysis for bookmark {new_bm.id}: {e}")

            analysis_thread = threading.Thread(target=analyze_async, daemon=True)
            analysis_thread.start()
        except Exception as analysis_error:
            logger.warning(f"Could not trigger background analysis: {analysis_error}")
            # Don't fail the bookmark save if analysis fails

        return jsonify({
            'message': 'Bookmark saved',
            'bookmark': {'id': new_bm.id, 'url': new_bm.url},
            'content_extracted': len(extracted_text) > 0,
            'wasDuplicate': False,
            'scraped': {
                'title': scraped_title,
                'headings': headings,
                'meta_description': meta_description
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@bookmarks_bp.route('/import', methods=['POST'])
@jwt_required()
def bulk_import_bookmarks():
    """Bulk import bookmarks from Chrome extension (optimized with Redis and progress tracking)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not isinstance(data, list):
        return jsonify({'message': 'Expected array of bookmarks'}), 400

    total_count = len(data)
    added_count = 0
    skipped_count = 0
    updated_count = 0
    errors = []
    new_bookmarks = []
    max_workers = 8  # Tune as needed

    # Store import progress in Redis for real-time updates
    import_key = f"import_progress:{user_id}"
    redis_cache.set(import_key, {
        'total': total_count,
        'processed': 0,
        'added': 0,
        'skipped': 0,
        'updated': 0,
        'errors': 0,
        'status': 'processing'
    }, expire=3600)  # Expire in 1 hour

    # Try to get cached user bookmarks first
    cached_bookmarks = redis_cache.get_cached_user_bookmarks(user_id)
    if cached_bookmarks:
        logger.debug(f"Using cached bookmarks for user {user_id}")
        existing_urls = set(bm['url'] for bm in cached_bookmarks)
        normalized_urls = set(normalize_url(bm['url']) for bm in cached_bookmarks)
        url_to_bm = {bm['url']: bm for bm in cached_bookmarks}
    else:
        # Fallback to database query
        logger.debug(f"Loading bookmarks from database for user {user_id}")
        existing_bms = SavedContent.query.filter_by(user_id=user_id).all()
        existing_urls = set(bm.url for bm in existing_bms)
        normalized_urls = set(normalize_url(bm.url) for bm in existing_bms)
        url_to_bm = {bm.url: bm for bm in existing_bms}
        
        # Cache the bookmarks for future use
        bookmarks_data = [{'url': bm.url, 'title': bm.title, 'id': bm.id} for bm in existing_bms]
        redis_cache.cache_user_bookmarks(user_id, bookmarks_data)

    def process_bookmark(bookmark_data):
        try:
            url = bookmark_data.get('url', '').strip()
            title = bookmark_data.get('title', '').strip()
            category = bookmark_data.get('category', 'other')
            if len(title) > 512:
                title = title[:512]
            if len(url) > 2048:
                url = url[:2048]
            if not url:
                return ('skip', url, 'Empty URL')

            norm_url = normalize_url(url)
            # Fast duplicate check using cached data
            if url in existing_urls or norm_url in normalized_urls:
                return ('skip', url, 'Duplicate bookmark')

            # Scrape and embed
            scraped = extract_article_content(url)
            extracted_text = scraped.get('content', '')
            quality_score = scraped.get('quality_score', 10)
            if quality_score < 5:
                return ('skip', url, 'Low quality content')

            content_for_embedding = f"{title} {extracted_text}"
            embedding = get_embedding(content_for_embedding)
            new_bm = SavedContent(
                user_id=user_id,
                url=url,
                title=title if title else 'Untitled Bookmark',
                notes='',
                extracted_text=extracted_text,
                embedding=embedding,
                quality_score=quality_score
            )
            return ('add', url, new_bm)
        except Exception as e:
            return ('error', bookmark_data.get('url', ''), str(e))

    # Use ThreadPoolExecutor for parallel scraping/embedding
    processed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_bookmark, bm) for bm in data]
        for future in as_completed(futures):
            result = future.result()
            processed_count += 1

            if result[0] == 'add':
                _, url, new_bm = result
                new_bookmarks.append(new_bm)
                added_count += 1
            elif result[0] == 'update':
                updated_count += 1
            elif result[0] == 'skip':
                skipped_count += 1
            elif result[0] == 'error':
                _, url, err = result
                errors.append(f"Error processing {url}: {err}")

            # Update progress in Redis every 10 bookmarks or at the end
            if processed_count % 10 == 0 or processed_count == total_count:
                redis_cache.set(import_key, {
                    'total': total_count,
                    'processed': processed_count,
                    'added': added_count,
                    'skipped': skipped_count,
                    'updated': updated_count,
                    'errors': len(errors),
                    'status': 'processing' if processed_count < total_count else 'completed'
                }, expire=3600)

    try:
        for bm in new_bookmarks:
            db.session.add(bm)
        db.session.commit()
        
        # Invalidate caches after adding new bookmarks
        if new_bookmarks:
            redis_cache.invalidate_user_bookmarks(user_id)
            # Also invalidate recommendations since new bookmarks affect recommendations
            from blueprints.recommendations import invalidate_user_recommendations
            invalidate_user_recommendations(user_id)

            # Trigger background analysis for newly imported content
            try:
                import threading
                def analyze_bulk_async():
                    try:
                        from services.background_analysis_service import batch_analyze_content
                        content_ids = [bm.id for bm in new_bookmarks]
                        result = batch_analyze_content(content_ids, user_id)
                        logger.info(f"Bulk analysis completed: {result}")
                    except Exception as e:
                        logger.error(f"Error triggering bulk background analysis: {e}")

                analysis_thread = threading.Thread(target=analyze_bulk_async, daemon=True)
                analysis_thread.start()
            except Exception as analysis_error:
                logger.warning(f"Could not trigger bulk background analysis: {analysis_error}")
        
        # Mark import as completed in Redis
        redis_cache.set(import_key, {
            'total': total_count,
            'processed': total_count,
            'added': added_count,
            'skipped': skipped_count,
            'updated': updated_count,
            'errors': len(errors),
            'status': 'completed'
        }, expire=3600)

        return jsonify({
            'message': 'Bulk import completed (optimized with Redis)',
            'total': total_count,
            'added': added_count,
            'skipped': skipped_count,
            'updated': updated_count,
            'errors': len(errors),
            'error_details': errors[:10] if errors else [],  # Limit error details to first 10
            'cache_used': cached_bookmarks is not None
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Bulk import failed: {str(e)}'}), 500

@bookmarks_bp.route('', methods=['GET'])
@jwt_required()
def list_bookmarks():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    
    # Build query
    query = SavedContent.query.filter_by(user_id=user_id)
    
    # Add search filter
    if search:
        query = query.filter(
            db.or_(
                SavedContent.title.ilike(f'%{search}%'),
                SavedContent.notes.ilike(f'%{search}%'),
                SavedContent.url.ilike(f'%{search}%')
            )
        )
    
    # Add category filter
    if category and category != 'all':
        query = query.filter(SavedContent.category == category)
    
    # Order by saved date and paginate
    pagination = query.order_by(SavedContent.saved_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    bookmarks = [{
        'id': b.id,
        'url': b.url,
        'title': b.title,
        'description': b.notes,  # Map 'notes' to 'description' for API consistency
        'saved_at': b.saved_at.isoformat(),
        'category': b.category,
        'has_content': bool(b.extracted_text)
    } for b in pagination.items]
    
    return jsonify({
        'bookmarks': bookmarks,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    }), 200

@bookmarks_bp.route('/<int:bookmark_id>', methods=['DELETE'])
@jwt_required()
def delete_bookmark(bookmark_id):
    user_id = int(get_jwt_identity())
    bm = SavedContent.query.get(bookmark_id)
    if not bm or bm.user_id != user_id:
        return jsonify({'message': 'Bookmark not found or unauthorized'}), 404
    try:
        # Store user_id and bookmark_id before deletion for cache invalidation
        user_id_for_cache = bm.user_id
        bookmark_id_for_cache = bm.id
        
        db.session.delete(bm)
        db.session.commit()
        
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_delete(bookmark_id_for_cache, user_id_for_cache)
        
        return jsonify({'message': 'Bookmark deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@bookmarks_bp.route('/url/<path:url>', methods=['DELETE'])
@jwt_required()
def delete_bookmark_by_url(url):
    """Delete bookmark by URL (for Chrome extension compatibility)"""
    user_id = int(get_jwt_identity())
    from urllib.parse import unquote
    decoded_url = unquote(url)
    
    bm = SavedContent.query.filter_by(user_id=user_id, url=decoded_url).first()
    if not bm:
        return jsonify({'message': 'Bookmark not found'}), 404
    try:
        # Store user_id and bookmark_id before deletion for cache invalidation
        user_id_for_cache = bm.user_id
        bookmark_id_for_cache = bm.id
        
        db.session.delete(bm)
        db.session.commit()
        
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_delete(bookmark_id_for_cache, user_id_for_cache)
        
        return jsonify({'message': 'Bookmark deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@bookmarks_bp.route('/check-duplicate', methods=['POST'])
@jwt_required()
def check_duplicate():
    """Check if a URL is already bookmarked by the user"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    existing_bookmark, duplicate_type = is_duplicate_url(url, user_id)
    
    if existing_bookmark:
        return jsonify({
            'isDuplicate': True,
            'duplicateType': duplicate_type,
            'existingBookmark': {
                'id': existing_bookmark.id,
                'title': existing_bookmark.title,
                'url': existing_bookmark.url,
                'notes': existing_bookmark.notes,
                'saved_at': existing_bookmark.saved_at.isoformat()
            }
        }), 200
    else:
        return jsonify({
            'isDuplicate': False,
            'duplicateType': None,
            'existingBookmark': None
        }), 200

@bookmarks_bp.route('/import/progress', methods=['GET'])
@jwt_required()
def get_import_progress():
    """Get current import progress for the user"""
    user_id = int(get_jwt_identity())
    import_key = f"import_progress:{user_id}"

    progress = redis_cache.get(import_key)
    if not progress:
        return jsonify({
            'status': 'no_import',
            'message': 'No import in progress'
        }), 200

    return jsonify(progress), 200

@bookmarks_bp.route('/analysis/progress', methods=['GET'])
@jwt_required()
def get_analysis_progress():
    """Get current background analysis progress for the user"""
    user_id = int(get_jwt_identity())
    analysis_key = f"analysis_progress:{user_id}"

    progress = redis_cache.get(analysis_key)
    if not progress:
        # Check if user has any unanalyzed content
        try:
            from models import SavedContent, ContentAnalysis
            from sqlalchemy import select

            analyzed_content_ids_subquery = select(ContentAnalysis.content_id).subquery()
            analyzed_content_ids_select = select(analyzed_content_ids_subquery.c.content_id)
            unanalyzed_count = db.session.query(SavedContent).filter(
                SavedContent.user_id == user_id,
                ~SavedContent.id.in_(analyzed_content_ids_select),
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).count()

            return jsonify({
                'status': 'idle',
                'message': 'No analysis in progress',
                'pending_items': unanalyzed_count
            }), 200
        except Exception as e:
            logger.error(f"Error checking analysis status: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Unable to check analysis status'
            }), 500

    return jsonify(progress), 200

@bookmarks_bp.route('/extract-url', methods=['POST'])
@jwt_required()
def extract_url_content():
    """Extract content from a URL for preview purposes"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    try:
        # Extract content from URL
        scraped = scrape_url_enhanced(url)
        extracted_text = scraped.get('content', '')
        scraped_title = scraped.get('title', '')
        headings = scraped.get('headings', [])
        meta_description = scraped.get('meta_description', '')
        
        # Try to get title from the page
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; FuzeBot/1.0)"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find('title')
            page_title = title.get_text().strip() if title else 'Untitled'
        except Exception as e:
            logger.warning(f"Error getting title: {e}")
            page_title = 'Untitled'
        
        return jsonify({
            'title': page_title,
            'description': extracted_text[:1000],  # Limit preview content
            'url': url,
            'success': True,
            'scraped': {
                'title': scraped_title,
                'headings': headings,
                'meta_description': meta_description
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in extract_url_content: {e}")
        return jsonify({
            'title': 'Untitled',
            'description': '',
            'url': url,
            'success': False,
            'message': f'Error extracting content: {str(e)}'
        }), 200  # Return 200 instead of 500 to avoid breaking the frontend 

@bookmarks_bp.route('/all', methods=['DELETE'])
@jwt_required()
def delete_all_bookmarks():
    user_id = int(get_jwt_identity())
    try:
        num_deleted = SavedContent.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({'message': f'Deleted {num_deleted} bookmarks'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500 