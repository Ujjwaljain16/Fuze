from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent, User, Project, ContentAnalysis
import requests
from readability import Document
from bs4 import BeautifulSoup
import numpy as np
from sqlalchemy.exc import IntegrityError
from scrapers.scrapling_enhanced_scraper import scrape_url_enhanced
from urllib.parse import urlparse, urljoin, urlunparse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.redis_utils import redis_cache
from middleware.security_middleware import validate_request_data, sanitize_string
import logging
import traceback
from datetime import datetime, timedelta
from sqlalchemy import func

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

def generate_comprehensive_embedding(title, description, meta_description, headings, extracted_text, url=None):
    """
    Generate comprehensive embedding using optimized strategy from test workflow.
    Priority: title > meta_description > headings > notes > extracted_text (first 5000 + last 1000)
    Always generates embedding even with minimal content - ensures semantic search works.
    """
    embedding_parts = []
    
    # Add title (highest priority)
    if title and title.strip():
        embedding_parts.append(title.strip())
    
    # Add meta description if available
    if meta_description and meta_description.strip():
        embedding_parts.append(meta_description.strip())
    
    # Add headings if available (limit to first 10)
    if headings:
        embedding_parts.append(' '.join(headings[:10]))
    
    # Add user notes/description if available
    if description and description.strip():
        embedding_parts.append(description.strip())
    
    # Add extracted text (first 5000 + last 1000 chars for better context)
    if extracted_text and extracted_text.strip():
        text_for_embedding = extracted_text[:5000]
        if len(extracted_text) > 5000:
            text_for_embedding += " " + extracted_text[-1000:]
        embedding_parts.append(text_for_embedding)
    
    # Join all parts
    content_for_embedding = ' '.join(embedding_parts).strip()
    
    # If we have no content at all, use URL as absolute minimum fallback
    if not content_for_embedding:
        content_for_embedding = url or "unknown content"
    
    # Generate embedding
    try:
        embedding = get_embedding(content_for_embedding)
        return embedding
    except Exception as embed_error:
        logger.error(f"Embedding generation failed: {embed_error}")
        # Fallback: try with just title and URL
        try:
            fallback_content = f"{title or 'Unknown'} {url or ''}".strip()
            if fallback_content:
                return get_embedding(fallback_content)
        except Exception as fallback_error:
            logger.error(f"Fallback embedding also failed: {fallback_error}")
            # Last resort: return None (will be handled by caller)
            return None

@bookmarks_bp.route('', methods=['POST'])
@jwt_required()
@validate_request_data(
    required_fields=['url'],
    field_rules={
        'url': {'check_sql_injection': False},  # URLs can contain SQL keywords legitimately
        'extracted_text': {'max_string_length': None, 'check_sql_injection': False, 'check_xss': False},  # No limits for extracted text
        'content': {'max_string_length': None, 'check_sql_injection': False, 'check_xss': False},  # No limits for content
    }
)
def save_bookmark():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # PRODUCTION OPTIMIZATION: Sanitize input
    url = sanitize_string(data.get('url')) if data.get('url') else None
    # PRODUCTION OPTIMIZATION: Sanitize all string inputs
    title = sanitize_string(data.get('title', ''))
    description = sanitize_string(data.get('description', ''))  # Keep for API compatibility
    category = sanitize_string(data.get('category', 'other'))
    tags = data.get('tags', [])
    if isinstance(tags, list):
        tags = [sanitize_string(tag) if isinstance(tag, str) else tag for tag in tags]
    
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
        from services.cache_invalidation_service import cache_invalidator
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

    # Save all bookmarks regardless of quality score - embeddings are always generated
    # Quality score is stored for reference but doesn't prevent saving
    
    # Prefer scraped title if not provided
    if not title or title == 'Untitled Bookmark':
        title = scraped_title or 'Untitled Bookmark'
    
    # Ensure title fits within database column limit (200 characters)
    # Truncate if necessary, preserving meaningful content
    final_title = title.strip() if title else 'Untitled Bookmark'
    if len(final_title) > 200:
        # Try to truncate at a word boundary if possible
        truncated = final_title[:197]  # Leave room for "..."
        last_space = truncated.rfind(' ')
        if last_space > 150:  # Only use word boundary if it's not too early
            final_title = truncated[:last_space] + "..."
        else:
            final_title = truncated + "..."
    
    # Generate comprehensive embedding using optimized strategy
    embedding = generate_comprehensive_embedding(
        title=final_title,
        description=description,
        meta_description=meta_description,
        headings=headings,
        extracted_text=extracted_text,
        url=url
    )
    
    # If embedding generation failed, still save bookmark but log warning
    if embedding is None:
        logger.warning(f"Failed to generate embedding for {url}, saving bookmark without embedding")
    
    # Ensure extracted_text is saved in full (TEXT column supports unlimited length)
    # Don't truncate - save the complete extracted content
    if extracted_text:
        # Remove null bytes that could cause issues
        extracted_text = extracted_text.replace('\x00', '')
        # Ensure it's a string
        if not isinstance(extracted_text, str):
            extracted_text = str(extracted_text)
    
    new_bm = SavedContent(
        user_id=user_id,
        url=url.strip(),
        title=final_title,  # Truncated to 200 chars max
        notes=description.strip() if isinstance(description, str) else '',
        extracted_text=extracted_text,  # Full extracted text - no truncation
        embedding=embedding,
        quality_score=quality_score
        # Optionally: store headings/meta_description in new columns if desired
    )
    try:
        db.session.add(new_bm)
        db.session.commit()
        # Invalidate caches using comprehensive cache invalidation service
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_save(new_bm.id, user_id)
        
        # PRODUCTION OPTIMIZATION: Invalidate query cache for user's bookmarks
        redis_cache.invalidate_query_cache(f"bookmarks:{user_id}:*")

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
    skip_reasons = {}  # Track skip reasons: {reason: count}
    new_bookmarks = []
    max_workers = 8  # Tune as needed

    # Store import progress in Redis for real-time updates
    import_key = f"import_progress:{user_id}"
    redis_cache.set_cache(import_key, {
        'total': total_count,
        'processed': 0,
        'added': 0,
        'skipped': 0,
        'updated': 0,
        'errors': 0,
        'status': 'processing'
    }, ttl=3600)  # Expire in 1 hour

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
                return ('skip', url, 'Empty URL', 'empty_url')

            # Filter out invalid URL schemes that can't be scraped
            invalid_schemes = ['javascript:', 'chrome://', 'chrome-extension://', 'file://', 'about:', 'data:', 'mailto:', 'tel:']
            url_lower = url.lower()
            if any(url_lower.startswith(scheme) for scheme in invalid_schemes):
                return ('skip', url, f'Invalid URL scheme (cannot scrape {urlparse(url).scheme}:// URLs)', 'invalid_scheme')

            # Validate URL format
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    # Allow relative URLs or URLs without scheme (will be treated as http)
                    if not parsed.scheme and not parsed.netloc and not parsed.path:
                        return ('skip', url, 'Invalid URL format', 'invalid_format')
            except Exception:
                return ('skip', url, 'Invalid URL format', 'invalid_format')

            norm_url = normalize_url(url)
            # Fast duplicate check using cached data
            if url in existing_urls or norm_url in normalized_urls:
                return ('skip', url, 'Duplicate bookmark', 'duplicate')

            # Scrape and embed (same workflow as single save) with retry logic
            # Use the same enhanced scraper that the test script uses
            # This ensures GitHub API and other enhanced features are used
            scraped = None
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    scraped = extract_article_content(url)
                    
                    if scraped:
                        content_length = len(scraped.get('content', ''))
                        quality = scraped.get('quality_score', 0)
                        
                        # Accept if we have reasonable content (even if quality is low)
                        # The scraper handles GitHub API, Scrapling, etc. automatically
                        if content_length > 50:
                            break  # Got good content, exit retry loop
                        elif attempt < max_retries - 1:
                            # Content too short, retry with exponential backoff
                            import time
                            time.sleep(0.5 * (attempt + 1))  # 0.5s, 1s delays
                    else:
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(0.5 * (attempt + 1))
                            
                except Exception as scrape_error:
                    error_str = str(scrape_error).lower()
                    # Check for rate limiting errors
                    if any(rate_limit_indicator in error_str for rate_limit_indicator in 
                           ['rate limit', '429', 'too many requests', 'quota exceeded']):
                        if attempt < max_retries - 1:
                            # Rate limited - wait longer before retry
                            import time
                            wait_time = 2 * (attempt + 1)  # 2s, 4s delays
                            logger.warning(f"Rate limited for {url[:50]}, waiting {wait_time}s before retry...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Rate limited for {url[:50]} after {max_retries} attempts")
                    elif attempt < max_retries - 1:
                        # Other errors - shorter retry delay
                        import time
                        time.sleep(1 * (attempt + 1))  # 1s, 2s delays
                    else:
                        logger.error(f"All scraping attempts failed for {url[:50]}: {scrape_error}")
            
            # If scraping failed completely, use proper fallback (never save "Unable to extract")
            if not scraped or not scraped.get('content'):
                logger.warning(f"Scraping failed for {url}, using proper fallback")
                parsed = urlparse(url)
                domain = parsed.netloc.replace('www.', '')
                path_parts = [p for p in parsed.path.strip('/').split('/') if p]
                
                # Generate meaningful fallback content (same as test script)
                fallback_content = f"Content from {domain}"
                if path_parts:
                    meaningful_parts = [p.replace('-', ' ').replace('_', ' ') 
                                      for p in path_parts[:3] 
                                      if p.lower() not in {'www', 'index', 'home', 'page'}]
                    if meaningful_parts:
                        fallback_content += f". Topic: {' '.join(meaningful_parts)}"
                
                scraped = {
                    'content': fallback_content,
                    'title': title or f"Content from {domain}",
                    'headings': [],
                    'meta_description': f"Content from {domain}",
                    'quality_score': 3  # Low but not zero
                }
            
            extracted_text = scraped.get('content', '')
            scraped_title = scraped.get('title', '')
            headings = scraped.get('headings', [])
            meta_description = scraped.get('meta_description', '')
            quality_score = scraped.get('quality_score', 10)
            
            # Never save "Unable to extract" or "extraction failed" messages
            # Replace them with proper fallback content
            if extracted_text and ('unable to extract' in extracted_text.lower() or 
                                 'extraction failed' in extracted_text.lower()):
                logger.warning(f"Replacing 'Unable to extract' message for {url[:50]} with proper fallback")
                parsed = urlparse(url)
                domain = parsed.netloc.replace('www.', '')
                extracted_text = f"Content from {domain}. URL: {url}"
                scraped['content'] = extracted_text
                scraped['quality_score'] = 3
            
            # Update title if scraped title is better
            if scraped_title and scraped_title != title:
                title = scraped_title
            
            # Ensure title fits within database column limit (200 characters)
            # Truncate if necessary, preserving meaningful content
            final_title = title if title else 'Untitled Bookmark'
            if len(final_title) > 200:
                # Try to truncate at a word boundary if possible
                truncated = final_title[:197]  # Leave room for "..."
                last_space = truncated.rfind(' ')
                if last_space > 150:  # Only use word boundary if it's not too early
                    final_title = truncated[:last_space] + "..."
                else:
                    final_title = truncated + "..."
            
            # Save all bookmarks regardless of quality score - embeddings are always generated
            # Quality score is stored for reference but doesn't prevent saving
            
            # Generate comprehensive embedding using same optimized strategy
            embedding = generate_comprehensive_embedding(
                title=final_title,
                description='',  # No description in bulk import
                meta_description=meta_description,
                headings=headings,
                extracted_text=extracted_text,
                url=url
            )
            
            # If embedding generation failed, still save bookmark but log warning
            if embedding is None:
                logger.warning(f"Failed to generate embedding for {url} during bulk import")
            
            # Ensure extracted_text is saved in full (TEXT column supports unlimited length)
            # Don't truncate - save the complete extracted content
            if extracted_text:
                # Remove null bytes that could cause issues
                extracted_text = extracted_text.replace('\x00', '')
                # Ensure it's a string
                if not isinstance(extracted_text, str):
                    extracted_text = str(extracted_text)
            
            new_bm = SavedContent(
                user_id=user_id,
                url=url,
                title=final_title,  # Truncated to 200 chars max
                notes='',
                category=category,  # Set category from bookmark data
                extracted_text=extracted_text,  # Full extracted text - no truncation
                embedding=embedding,
                quality_score=quality_score
            )
            return ('add', url, new_bm, None)
        except Exception as e:
            return ('error', bookmark_data.get('url', ''), str(e), 'exception')

    # Use ThreadPoolExecutor for parallel scraping/embedding
    # Keep full parallelism for speed - rate limiting is handled in the scraper
    # Each worker adds a small random delay to spread out requests naturally
    processed_count = 0
    import time
    import random
    
    def process_with_smart_delay(bookmark_data):
        """Process bookmark with smart delay to avoid rate limiting"""
        # Small random delay (0-200ms) to spread out requests naturally
        # This prevents all workers from hitting APIs at exactly the same time
        # while maintaining full parallelism
        time.sleep(random.uniform(0, 0.2))
        return process_bookmark(bookmark_data)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_with_smart_delay, bm) for bm in data]
        for future in as_completed(futures):
            result = future.result()
            processed_count += 1

            if result[0] == 'add':
                _, url, new_bm, _ = result
                new_bookmarks.append(new_bm)
                added_count += 1
            elif result[0] == 'skip':
                # Handle both 3-tuple (old) and 4-tuple (new) formats
                if len(result) == 4:
                    _, url, reason, reason_code = result
                else:
                    _, url, reason = result
                    reason_code = 'unknown'
                skipped_count += 1
                # Track skip reasons
                reason_code = reason_code or 'unknown'
                skip_reasons[reason_code] = skip_reasons.get(reason_code, 0) + 1
                logger.debug(f"Skipped bookmark {url[:50]}: {reason}")
            elif result[0] == 'error':
                # Handle both 3-tuple (old) and 4-tuple (new) formats
                if len(result) == 4:
                    _, url, err, _ = result
                else:
                    _, url, err = result
                errors.append(f"Error processing {url}: {err}")

            # Update progress in Redis every 10 bookmarks or at the end
            if processed_count % 10 == 0 or processed_count == total_count:
                redis_cache.set_cache(import_key, {
                    'total': total_count,
                    'processed': processed_count,
                    'added': added_count,
                    'skipped': skipped_count,
                    'updated': updated_count,
                    'errors': len(errors),
                    'skip_reasons': skip_reasons.copy(),  # Include skip reason breakdown
                    'status': 'processing' if processed_count < total_count else 'completed'
                }, ttl=3600)

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
        redis_cache.set_cache(import_key, {
            'total': total_count,
            'processed': total_count,
            'added': added_count,
            'skipped': skipped_count,
            'updated': updated_count,
            'errors': len(errors),
            'skip_reasons': skip_reasons.copy(),  # Include skip reason breakdown
            'status': 'completed'
        }, ttl=3600)

        return jsonify({
            'message': 'Bulk import completed (optimized with Redis)',
            'total': total_count,
            'added': added_count,
            'skipped': skipped_count,
            'updated': updated_count,
            'errors': len(errors),
            'skip_reasons': skip_reasons,  # Breakdown of why bookmarks were skipped
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
    
    # PRODUCTION OPTIMIZATION: Check cache first
    cache_key = f"bookmarks:{user_id}:{page}:{per_page}:{search}:{category}"
    cached_result = redis_cache.get_cached_query_result(cache_key)
    if cached_result:
        return jsonify(cached_result), 200
    
    # Build query - SECURITY: Always filter by user_id
    # PRODUCTION OPTIMIZATION: Use eager loading to prevent N+1 queries
    from sqlalchemy.orm import joinedload
    query = SavedContent.query.options(joinedload(SavedContent.analyses)).filter_by(user_id=user_id)
    
    # Add search filter
    if search:
        query = query.filter(
            db.or_(
                SavedContent.title.ilike(f'%{search}%'),
                SavedContent.notes.ilike(f'%{search}%'),
                SavedContent.url.ilike(f'%{search}%')
            )
        )
    
    # Add category filter (only if category is provided and not 'all')
    # Handle None/empty categories by treating them as 'other'
    if category and category != 'all':
        # Filter by category, but also include bookmarks with None/empty category if filtering for 'other'
        if category == 'other':
            query = query.filter(
                db.or_(
                    SavedContent.category == category,
                    SavedContent.category.is_(None),
                    SavedContent.category == ''
                )
            )
        else:
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
    
    result = {
        'bookmarks': bookmarks,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    }
    
    # PRODUCTION OPTIMIZATION: Cache result (shorter TTL for search results)
    cache_ttl = 60 if search else 300  # 1 min for search, 5 min for regular
    redis_cache.cache_query_result(cache_key, result, ttl=cache_ttl)
    
    return jsonify(result), 200

@bookmarks_bp.route('/<int:bookmark_id>', methods=['DELETE'])
@jwt_required()
def delete_bookmark(bookmark_id):
    user_id = int(get_jwt_identity())
    
    # PRODUCTION OPTIMIZATION: Invalidate query cache before deletion
    redis_cache.invalidate_query_cache(f"bookmarks:{user_id}:*")
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
        from services.cache_invalidation_service import cache_invalidator
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
        from services.cache_invalidation_service import cache_invalidator
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
    """Get current import progress for the user (legacy endpoint - use SSE instead)"""
    user_id = int(get_jwt_identity())
    import_key = f"import_progress:{user_id}"

    progress = redis_cache.get(import_key)
    if not progress:
        return jsonify({
            'status': 'no_import',
            'message': 'No import in progress'
        }), 200

    return jsonify(progress), 200

@bookmarks_bp.route('/import/progress/stream', methods=['GET'])
def stream_import_progress():
    """Server-Sent Events stream for import progress"""
    from flask import Response, stream_with_context, request
    from flask_jwt_extended import decode_token
    import json
    import time
    
    # Get token from Authorization header (for fetch/extension) or query param (for EventSource)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
    else:
        token = request.args.get('token')
    
    if not token:
        return Response('Token required', status=401, mimetype='text/plain')
    
    try:
        decoded = decode_token(token)
        user_id = int(decoded['sub'])
    except Exception as e:
        logger.error(f"Error decoding token for SSE: {e}")
        return Response('Invalid token', status=401, mimetype='text/plain')
    
    import_key = f"import_progress:{user_id}"
    
    def generate():
        last_status = None
        start_time = time.time()
        max_connection_time = 1800  # 30 minutes maximum connection time
        heartbeat_interval = 30  # Send heartbeat every 30 seconds
        last_heartbeat = time.time()
        
        while True:
            try:
                # Check if connection has been open too long
                elapsed = time.time() - start_time
                if elapsed > max_connection_time:
                    yield f"data: {json.dumps({'status': 'timeout', 'message': 'Connection timeout - please refresh'})}\n\n"
                    break
                
                # Send heartbeat to keep connection alive
                if time.time() - last_heartbeat > heartbeat_interval:
                    yield f": heartbeat\n\n"  # SSE comment (keeps connection alive)
                    last_heartbeat = time.time()
                
                progress = redis_cache.get(import_key)
                
                if not progress:
                    if last_status != 'no_import':
                        yield f"data: {json.dumps({'status': 'no_import', 'message': 'No import in progress'})}\n\n"
                        last_status = 'no_import'
                else:
                    current_status = progress.get('status', 'unknown')
                    if progress != last_status:
                        yield f"data: {json.dumps(progress)}\n\n"
                        last_status = progress
                        
                        # If import is completed, send final update and close
                        if current_status == 'completed':
                            time.sleep(1)  # Give client time to process
                            break
                
                time.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"Error in import progress stream: {e}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                break
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@bookmarks_bp.route('/analysis/progress', methods=['GET'])
@jwt_required()
def get_analysis_progress():
    """Get current background analysis progress for the user (legacy endpoint - use SSE instead)"""
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

@bookmarks_bp.route('/analysis/progress/stream', methods=['GET'])
def stream_analysis_progress():
    """Server-Sent Events stream for analysis progress"""
    from flask import Response, stream_with_context, request
    from flask_jwt_extended import decode_token
    import json
    import time
    
    # Get token from Authorization header (for fetch/extension) or query param (for EventSource)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]  # Remove 'Bearer ' prefix
    else:
        token = request.args.get('token')
    
    if not token:
        return Response('Token required', status=401, mimetype='text/plain')
    
    try:
        decoded = decode_token(token)
        user_id = int(decoded['sub'])
    except Exception as e:
        logger.error(f"Error decoding token for SSE: {e}")
        return Response('Invalid token', status=401, mimetype='text/plain')
    
    analysis_key = f"analysis_progress:{user_id}"
    
    def generate():
        last_status = None
        while True:
            try:
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

                        idle_status = {
                            'status': 'idle',
                            'message': 'No analysis in progress',
                            'pending_items': unanalyzed_count
                        }
                        
                        if idle_status != last_status:
                            yield f"data: {json.dumps(idle_status)}\n\n"
                            last_status = idle_status
                    except Exception as e:
                        logger.error(f"Error checking analysis status: {e}")
                        error_status = {'status': 'error', 'message': str(e)}
                        if error_status != last_status:
                            yield f"data: {json.dumps(error_status)}\n\n"
                            last_status = error_status
                else:
                    current_status = progress.get('status', 'unknown')
                    if progress != last_status:
                        yield f"data: {json.dumps(progress)}\n\n"
                        last_status = progress
                
                time.sleep(2)  # Check every 2 seconds (analysis is slower)
            except Exception as e:
                logger.error(f"Error in analysis progress stream: {e}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                break
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

@bookmarks_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics with historical comparisons for percentage changes"""
    from utils.redis_utils import redis_cache
    
    try:
        user_id = int(get_jwt_identity())
        
        # PRODUCTION OPTIMIZATION: Cache dashboard stats (changes infrequently)
        cache_key = f"dashboard:stats:{user_id}"
        cached_stats = redis_cache.get(cache_key) if redis_cache else None
        
        if cached_stats:
            return jsonify(cached_stats), 200
        
        # Get current date and calculate comparison periods
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        month_ago = now - timedelta(days=30)
        
        # Total Bookmarks - compare current vs 30 days ago
        total_bookmarks = SavedContent.query.filter_by(user_id=user_id).count()
        bookmarks_month_ago = SavedContent.query.filter(
            SavedContent.user_id == user_id,
            SavedContent.saved_at <= month_ago
        ).count()
        
        bookmarks_change = 0
        if bookmarks_month_ago > 0:
            bookmarks_change = ((total_bookmarks - bookmarks_month_ago) / bookmarks_month_ago) * 100
        elif total_bookmarks > 0:
            bookmarks_change = 100  # New user, 100% increase
        
        # Active Projects - compare current vs 30 days ago
        total_projects = Project.query.filter_by(user_id=user_id).count()
        projects_month_ago = Project.query.filter(
            Project.user_id == user_id,
            Project.created_at <= month_ago
        ).count()
        
        projects_change = total_projects - projects_month_ago
        if projects_month_ago > 0:
            projects_change_percent = ((total_projects - projects_month_ago) / projects_month_ago) * 100
            projects_change_display = f"+{projects_change_percent:.0f}%" if projects_change_percent > 0 else f"{projects_change_percent:.0f}%"
        else:
            projects_change_display = f"+{projects_change}" if projects_change > 0 else str(projects_change)
        
        # Weekly Saves - compare this week vs last week
        weekly_saves = SavedContent.query.filter(
            SavedContent.user_id == user_id,
            SavedContent.saved_at >= week_ago
        ).count()
        
        last_week_saves = SavedContent.query.filter(
            SavedContent.user_id == user_id,
            SavedContent.saved_at >= two_weeks_ago,
            SavedContent.saved_at < week_ago
        ).count()
        
        weekly_change = 0
        if last_week_saves > 0:
            weekly_change = ((weekly_saves - last_week_saves) / last_week_saves) * 100
        elif weekly_saves > 0:
            weekly_change = 100  # First week with saves
        
        # Success Rate - based on quality scores and analysis completion
        # Success = bookmarks with quality_score >= 5 and have analysis
        successful_bookmarks = db.session.query(SavedContent).join(
            ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
        ).filter(
            SavedContent.user_id == user_id,
            SavedContent.quality_score >= 5
        ).count()
        
        success_rate = 0
        if total_bookmarks > 0:
            success_rate = (successful_bookmarks / total_bookmarks) * 100
        
        # Get previous success rate (30 days ago)
        successful_bookmarks_month_ago = db.session.query(SavedContent).join(
            ContentAnalysis, SavedContent.id == ContentAnalysis.content_id
        ).filter(
            SavedContent.user_id == user_id,
            SavedContent.quality_score >= 5,
            SavedContent.saved_at <= month_ago
        ).count()
        
        success_rate_month_ago = 0
        if bookmarks_month_ago > 0:
            success_rate_month_ago = (successful_bookmarks_month_ago / bookmarks_month_ago) * 100
        
        success_rate_change = success_rate - success_rate_month_ago
        
        # Format changes
        def format_change(value):
            if value > 0:
                return f"+{value:.0f}%"
            elif value < 0:
                return f"{value:.0f}%"
            else:
                return "0%"
        
        stats = {
            'total_bookmarks': {
                'value': total_bookmarks,
                'change': format_change(bookmarks_change),
                'change_value': bookmarks_change
            },
            'active_projects': {
                'value': total_projects,
                'change': projects_change_display,
                'change_value': projects_change
            },
            'weekly_saves': {
                'value': weekly_saves,
                'change': format_change(weekly_change),
                'change_value': weekly_change
            },
            'success_rate': {
                'value': round(success_rate, 0),
                'change': format_change(success_rate_change),
                'change_value': success_rate_change
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@bookmarks_bp.route('/extract-url', methods=['POST'])
@jwt_required()
def extract_url_content():
    """Extract content from a URL for preview purposes"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'message': 'URL is required'}), 400
    
    try:
        # Extract content from URL (scrape_url_enhanced now handles LinkedIn URLs automatically)
        scraped = scrape_url_enhanced(url)
        extracted_text = scraped.get('content', '')
        scraped_title = scraped.get('title', '')
        headings = scraped.get('headings', [])
        meta_description = scraped.get('meta_description', '')
        quality_score = scraped.get('quality_score', 0)
        
        # Use scraped title as primary, fallback to page title only if needed
        page_title = scraped_title or 'Untitled'
        
        # For LinkedIn URLs, the LinkedIn scraper already provides good title
        # For other URLs, try to get title from the page if scraped title is generic
        if not scraped_title or scraped_title in ['Untitled', 'LinkedIn Post']:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; FuzeBot/1.0)"}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.find('title')
                if title:
                    page_title = title.get_text().strip() or scraped_title or 'Untitled'
            except Exception as e:
                logger.debug(f"Error getting page title: {e}")
                # Use scraped title as fallback
                page_title = scraped_title or 'Untitled'
        
        return jsonify({
            'title': page_title,
            'description': extracted_text[:1000],  # Limit preview content
            'url': url,
            'success': True,
            'quality_score': quality_score,
            'scraped': {
                'title': scraped_title,
                'headings': headings,
                'meta_description': meta_description,
                'content_length': len(extracted_text)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in extract_url_content: {e}")
        import traceback
        logger.debug(traceback.format_exc())
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