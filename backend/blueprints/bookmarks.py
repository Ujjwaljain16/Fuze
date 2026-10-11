from flask import Blueprint, request, jsonify
from core.http_errors import error_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SavedContent, User, Project, ContentAnalysis, processed_bookmark_clause
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from services.bookmark_processing_service import scrape_url_summary
from urllib.parse import urlparse, urlunparse
from core import cache_keys
from utils.redis_utils import redis_cache
from middleware.security_middleware import validate_request_data, sanitize_string
import logging
import traceback
from datetime import datetime, timedelta
from utils.timefmt import iso_utc

logger = logging.getLogger(__name__)

bookmarks_bp = Blueprint('bookmarks', __name__, url_prefix='/api/bookmarks')

TRACKING_PARAMS = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                   'fbclid', 'gclid', 'ref', 'source', 'campaign'}


# The (user_id, url) unique index is a B-tree, whose entries must fit in about a third of a page
# (~2.7 KB); a longer URL makes the INSERT fail. 2048 bytes covers every URL browsers accept.
MAX_URL_BYTES = 2048
MAX_IMPORT_ITEMS = 5000  # the extension imports 1000 at a time by default
MAX_PER_PAGE = 100


def url_too_long(url: str) -> bool:
    return len(url.encode('utf-8')) > MAX_URL_BYTES


def normalize_url(url):
    """Canonical form used to compare URLs: same resource -> same string.

    Lowercases scheme and host, drops the fragment, tracking params and a trailing
    path slash, and sorts the remaining query params. Params that identify the
    resource (YouTube ?v=, HN ?id=) are kept, so different resources stay different.
    """
    if not url:
        return url
    parsed = urlparse(url.strip())
    params = [p for p in parsed.query.split('&') if p and p.split('=')[0].lower() not in TRACKING_PARAMS]
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip('/'),
        parsed.params,
        '&'.join(sorted(params)),
        '',
    ))


def is_duplicate_url(service, url, user_id):
    """Return (existing_bookmark, 'exact' | 'normalized') if the user already saved this resource."""
    existing_exact = service.get_bookmark_by_url(user_id, url)
    if existing_exact:
        return existing_exact, 'exact'

    # Stored URLs are kept as the user saved them, so gather the bookmarks on the same
    # host+path and compare canonical forms (this also catches a saved URL that carried tracking params).
    normalized_url = normalize_url(url)
    parsed = urlparse(normalized_url)
    from utils.query_sanitizer import sanitize_like_query
    safe_domain_path = sanitize_like_query(f"{parsed.scheme}://{parsed.netloc}{parsed.path}")
    for bookmark in service.uow.bookmarks.get_similar_by_domain_path(user_id, safe_domain_path):
        if normalize_url(bookmark.url) == normalized_url:
            return bookmark, 'normalized'

    return None, None

def _sse_user_id():
    """Authenticate an SSE request; returns the user id or None.

    Accepts an access token in the Authorization header (fetch-based clients such as the
    extension) or a single-use ticket from POST /api/realtime/stream-ticket (EventSource).
    verify_jwt_in_request checks the token type, expiry and revocation list; the old manual
    decode_token accepted revoked tokens and 30-day refresh tokens. Tokens are never read
    from the query string, where access logs and browser history would keep them.
    """
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request(locations=['headers'])
        return int(get_jwt_identity())
    except Exception:
        pass
    ticket = request.args.get('ticket')
    if ticket:
        from utils.stream_tickets import consume_stream_ticket
        user_id = consume_stream_ticket(ticket)
        return int(user_id) if user_id else None
    return None


def process_bookmark_content_async(bookmark_id: int, url: str, user_id: int) -> bool:
    """
    Enqueue bookmark processing. Called after the bookmark is committed, so it never raises:
    the save already succeeded, and raising here turned a saved bookmark into a 500. When the
    queue is unreachable the bookmark stays PENDING and the pipeline reconciler enqueues it.
    """
    from services.task_queue import enqueue_bookmark_processing, is_rq_available

    if not is_rq_available() or not enqueue_bookmark_processing(bookmark_id, url, user_id):
        logger.warning(f"Bookmark {bookmark_id} not enqueued now; the reconciler will pick it up")
        return False
    return True

@bookmarks_bp.route('/quick-save', methods=['POST'])
@jwt_required()
@validate_request_data(
    required_fields=['url'],
    field_rules={
        'url': {'check_sql_injection': False},
        'title': {'check_sql_injection': False},
        'description': {'check_sql_injection': False},
    }
)
def quick_save_bookmark():
    """
    Quick save endpoint: Save bookmark immediately with minimal data,
    then process content extraction, embedding, and analysis in background.
    Returns immediately so user can return to previous app.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    url = sanitize_string(data.get('url')) if data.get('url') else None
    title = sanitize_string(data.get('title', ''))
    description = sanitize_string(data.get('description', ''))
    
    if not url:
        return error_response('url_required', 'URL is required', 400)
    if url_too_long(url):
        return error_response('url_too_long', f'URL is longer than {MAX_URL_BYTES} bytes', 400)
    
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService
    
    try:
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            existing_bookmark, duplicate_type = is_duplicate_url(service, url, user_id)
            
            if existing_bookmark:
                # Update existing bookmark with new title/description if provided
                if title:
                    existing_bookmark.title = title.strip()
                if description:
                    existing_bookmark.notes = description.strip()
                
                existing_bookmark_id = existing_bookmark.id
                existing_bookmark_url = existing_bookmark.url
                uow.flush()
            else:
                existing_bookmark_id = None
                
                # Ensure title is not empty
                if not title or not title.strip():
                    title = 'Untitled Bookmark'
                
                # Truncate title if needed
                final_title = title.strip() if title else 'Untitled Bookmark'
                if len(final_title) > 200:
                    truncated = final_title[:197]
                    last_space = truncated.rfind(' ')
                    if last_space > 150:
                        final_title = truncated[:last_space] + "..."
                    else:
                        final_title = truncated + "..."
                
                # Save bookmark immediately with minimal data
                new_bm = service.create_bookmark(
                    user_id=user_id,
                    url=url.strip(),
                    title=final_title,
                    notes=description.strip() if isinstance(description, str) else ''
                )
                new_bm_id = new_bm.id
    except IntegrityError:
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            existing_bm = service.get_bookmark_by_url(user_id, url.strip())
            existing_bm_id = existing_bm.id if existing_bm else None
            existing_bm_url = existing_bm.url if existing_bm else url.strip()
        return jsonify({
            'message': 'Bookmark updated',
            'bookmark': {'id': existing_bm_id, 'url': existing_bm_url},
            'wasDuplicate': True,
            'duplicateType': 'exact',
            'processing': 'background'
        }), 200
            
    # Outside UoW block: Side effects
    if existing_bookmark_id:
        # Invalidate caches
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_update(existing_bookmark_id, user_id)
        
        # Still trigger background processing in case content needs updating
        process_bookmark_content_async(existing_bookmark_id, existing_bookmark_url, user_id)
        
        return jsonify({
            'message': 'Bookmark updated',
            'bookmark': {'id': existing_bookmark_id, 'url': existing_bookmark_url},
            'wasDuplicate': True,
            'duplicateType': duplicate_type,
            'processing': 'background'
        }), 200
    
    else:
        # Invalidate caches
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_save(new_bm_id, user_id)
        redis_cache.invalidate_query_cache(cache_keys.bookmarks_pattern(user_id))
        
        return jsonify({
            'message': 'Bookmark saved',
            'bookmark': {'id': new_bm_id, 'url': url.strip()},
            'processing': 'background',
            'wasDuplicate': False
        }), 201

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
        return error_response('url_required', 'URL is required', 400)
    if url_too_long(url):
        return error_response('url_too_long', f'URL is longer than {MAX_URL_BYTES} bytes', 400)
    
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService
    
    tags_str = ','.join(tags) if isinstance(tags, list) else (tags if isinstance(tags, str) else '')

    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        existing_bookmark, duplicate_type = is_duplicate_url(service, url, user_id)
        
        if existing_bookmark:
            # Update existing bookmark
            existing_bookmark.title = title.strip() if title else existing_bookmark.title
            existing_bookmark.notes = description.strip() if description else existing_bookmark.notes
            if 'tags' in data:
                existing_bookmark.tags = tags_str
            # Will commit when UoW exits
            
            existing_bookmark_id = existing_bookmark.id
            existing_bookmark_url = existing_bookmark.url
            uow.flush()
            
    # Outside UoW
    if existing_bookmark:
        from services.cache_invalidation_service import cache_invalidator
        cache_invalidator.after_content_update(existing_bookmark_id, user_id)
        return jsonify({
            'message': 'Bookmark updated',
            'bookmark': {'id': existing_bookmark_id, 'url': existing_bookmark_url},
            'wasDuplicate': True,
            'duplicateType': duplicate_type
        }), 200
    
    # Ensure title is not empty
    if not title or not title.strip():
        title = 'Untitled Bookmark'
    
    final_title = title.strip()
    if len(final_title) > 200:
        truncated = final_title[:197]
        last_space = truncated.rfind(' ')
        if last_space > 150:
            final_title = truncated[:last_space] + "..."
        else:
            final_title = truncated + "..."
    
    try:
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            new_bm = service.create_bookmark(
                user_id=user_id,
                url=url.strip(),
                title=final_title,
                notes=description.strip() if isinstance(description, str) else '',
                tags=tags_str,
                category=category
            )
            new_bm_id = new_bm.id
            new_bm_url = new_bm.url
    except IntegrityError:
        # Only a unique-constraint violation (a genuine insert race with another
        # concurrent request for the same URL, since is_duplicate_url() already
        # checked above) is a legitimate "someone else just created it" case.
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            existing_bm = service.get_bookmark_by_url(user_id, url.strip())
        if not existing_bm:
            # The insert failed but no matching row exists either -- this is a
            # real failure, not a race, so don't lie to the client with a 200.
            logger.error(f"Bookmark insert failed with IntegrityError but no existing row found for user {user_id}, url {url.strip()}")
            return error_response('insert_conflict_unresolved', 'Failed to save bookmark', 500)
        return jsonify({
            'message': 'Bookmark updated',
            'bookmark': {'id': existing_bm.id, 'url': existing_bm.url},
            'wasDuplicate': True,
            'processing': 'background'
        }), 200

    # Post-commit: Cache invalidation
    from services.cache_invalidation_service import cache_invalidator
    cache_invalidator.after_content_save(new_bm_id, user_id)
    redis_cache.invalidate_query_cache(cache_keys.bookmarks_pattern(user_id))

    return jsonify({
        'message': 'Bookmark saved',
        'bookmark': {'id': new_bm_id, 'url': new_bm_url},
        'processing': 'background',
        'wasDuplicate': False
    }), 201

IMPORT_INSERT_CHUNK = 200


def _insert_import_rows(rows, skip_reasons):
    """Insert the import's new rows, skipping any row the database rejects.

    Each chunk goes in under its own savepoint, so the usual case stays a few batched
    INSERTs. When a chunk fails (a URL another request saved after the import read the
    user's bookmarks, or any other bad row) it is retried one row per savepoint, so only
    the bad rows are lost. Returns [(id, url)] for the rows that were saved.
    """
    from uow.unit_of_work import UnitOfWork

    inserted = []
    with UnitOfWork() as uow:
        session = uow.session
        for start in range(0, len(rows), IMPORT_INSERT_CHUNK):
            chunk = rows[start:start + IMPORT_INSERT_CHUNK]
            try:
                with session.begin_nested():
                    # Fresh objects per attempt: a rolled-back savepoint leaves its objects unusable.
                    bms = [SavedContent(**row) for row in chunk]
                    session.add_all(bms)
                inserted.extend((bm.id, bm.url) for bm in bms)
                continue
            except SQLAlchemyError as chunk_err:
                logger.info(f"[IMPORT] Chunk insert failed, retrying row by row: {chunk_err.__class__.__name__}")

            for row in chunk:
                try:
                    with session.begin_nested():
                        bm = SavedContent(**row)
                        session.add(bm)
                    inserted.append((bm.id, bm.url))
                except IntegrityError:
                    skip_reasons['duplicate'] = skip_reasons.get('duplicate', 0) + 1
                except SQLAlchemyError as row_err:
                    logger.warning(f"[IMPORT] Skipping bookmark that could not be saved: {row_err.__class__.__name__}")
                    skip_reasons['insert_failed'] = skip_reasons.get('insert_failed', 0) + 1
    return inserted


@bookmarks_bp.route('/import', methods=['POST'])
@jwt_required()
def bulk_import_bookmarks():
    """Bulk import bookmarks from Chrome extension (optimized with Redis and progress tracking)"""
    user_id = int(get_jwt_identity())
    logger.info(f"[IMPORT] Starting bulk import for user {user_id} - received {len(request.get_json()) if isinstance(request.get_json(), list) else 0} bookmarks")
    data = request.get_json()

    if not isinstance(data, list):
        return error_response('invalid_import_payload', 'Expected array of bookmarks', 400)
    if len(data) > MAX_IMPORT_ITEMS:
        return error_response('import_too_large', f'Import at most {MAX_IMPORT_ITEMS} bookmarks per request', 413)

    total_count = len(data)
    added_count = 0
    skipped_count = 0
    skip_reasons = {}  # Track skip reasons: {reason: count}

    # Store import progress in Redis for real-time updates. The extension polls this key,
    # so it must always end in a terminal state, even when the import fails.
    import_key = f"import_progress:{user_id}"
    progress = {
        'total': total_count,
        'processed': 0,
        'added': 0,
        'skipped': 0,
        'updated': 0,
        'errors': 0,
        'status': 'processing'
    }
    redis_cache.set_cache(import_key, progress, ttl=3600)  # Expire in 1 hour

    try:
        # Try to get cached user bookmarks first
        cached_bookmarks = redis_cache.get_cached_user_bookmarks(user_id)
        if cached_bookmarks:
            logger.debug(f"Using cached bookmarks for user {user_id}")
            existing_urls = set(bm['url'] for bm in cached_bookmarks)
            normalized_urls = set(normalize_url(bm['url']) for bm in cached_bookmarks)
        else:
            # Fallback to database query
            logger.debug(f"Loading bookmarks from database for user {user_id}")

            from uow.unit_of_work import UnitOfWork
            from services.bookmark_service import BookmarkService

            with UnitOfWork() as uow:
                service = BookmarkService(uow)
                existing_bms = service.uow.bookmarks.get_url_index(user_id)

                existing_urls = set(bm.url for bm in existing_bms)
                normalized_urls = set(normalize_url(bm.url) for bm in existing_bms)

                # Cache the bookmarks for future use
                bookmarks_data = [{'url': bm.url, 'title': bm.title, 'id': bm.id} for bm in existing_bms]

            redis_cache.cache_user_bookmarks(user_id, bookmarks_data)

        new_rows = []

        for bm_data in data:
            if not isinstance(bm_data, dict):
                skipped_count += 1
                continue

            url = (bm_data.get('url') or '').strip()
            title = (bm_data.get('title') or '').strip() or 'Untitled Bookmark'
            category = bm_data.get('category', 'other')

            if not url:
                skipped_count += 1
                skip_reasons['empty_url'] = skip_reasons.get('empty_url', 0) + 1
                continue
            if url_too_long(url):
                skipped_count += 1
                skip_reasons['url_too_long'] = skip_reasons.get('url_too_long', 0) + 1
                continue

            invalid_schemes = ['javascript:', 'chrome://', 'chrome-extension://', 'file://', 'about:', 'data:', 'mailto:', 'tel:']
            if any(url.lower().startswith(s) for s in invalid_schemes):
                skipped_count += 1
                skip_reasons['invalid_scheme'] = skip_reasons.get('invalid_scheme', 0) + 1
                continue

            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    skipped_count += 1
                    skip_reasons['invalid_format'] = skip_reasons.get('invalid_format', 0) + 1
                    continue
            except Exception:
                skipped_count += 1
                skip_reasons['invalid_format'] = skip_reasons.get('invalid_format', 0) + 1
                continue

            norm_url = normalize_url(url)
            if url in existing_urls or norm_url in normalized_urls:
                skipped_count += 1
                skip_reasons['duplicate'] = skip_reasons.get('duplicate', 0) + 1
                continue

            if len(title) > 200:
                title = title[:197] + "..."

            new_rows.append({
                'user_id': user_id,
                'url': url[:2048],
                'title': title,
                'notes': '',
                'category': category,
                'quality_score': 0
            })
            existing_urls.add(url)
            normalized_urls.add(norm_url)

        if new_rows:
            created_ids_urls = _insert_import_rows(new_rows, skip_reasons)
            added_count = len(created_ids_urls)
            skipped_count += len(new_rows) - added_count

            for bm_id, bm_url in created_ids_urls:
                try:
                    process_bookmark_content_async(bm_id, bm_url, user_id)
                except Exception as enqueue_err:
                    logger.warning(f"Could not enqueue bulk processing for bookmark {bm_id}: {enqueue_err}")

            redis_cache.invalidate_query_cache(cache_keys.bookmarks_pattern(user_id))
            from blueprints.recommendations import invalidate_user_recommendations
            invalidate_user_recommendations(user_id)

        progress.update({
            'processed': total_count,
            'added': added_count,
            'skipped': skipped_count,
            'skip_reasons': skip_reasons,
            'status': 'completed'
        })
    finally:
        if progress['status'] != 'completed':
            progress['status'] = 'failed'
        redis_cache.set_cache(import_key, progress, ttl=3600)

    logger.info(f"[IMPORT] Completed bulk import for user {user_id}: added={added_count}, skipped={skipped_count}")
    return jsonify({
        'message': f'Bulk import queued. {added_count} bookmarks enqueued for background processing.',
        'total': total_count,
        'added': added_count,
        'skipped': skipped_count,
        'updated': 0,
        'errors': 0,
        'skip_reasons': skip_reasons,
        'status': 'completed'
    }), 200

@bookmarks_bp.route('', methods=['GET'])
@jwt_required()
def list_bookmarks():
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = max(1, min(request.args.get('per_page', default=10, type=int) or 10, MAX_PER_PAGE))
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    
    # PRODUCTION OPTIMIZATION: Check cache first
    cache_key = cache_keys.bookmarks_page(user_id, page, per_page, search, category)
    cached_result = redis_cache.get_cache(cache_key)
    if cached_result:
        return jsonify(cached_result), 200
    
    # Build query - SECURITY: Always filter by user_id
    # PRODUCTION OPTIMIZATION: Use eager loading to prevent N+1 queries
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService
    
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        pagination = service.list_bookmarks(
            user_id=user_id,
            search=search,
            category=category,
            page=page,
            per_page=per_page
        )
        
        bookmarks = [{
            'id': b.id,
            'url': b.url,
            'title': b.title,
            'description': b.notes,  # Map 'notes' to 'description' for API consistency
            'saved_at': iso_utc(b.saved_at),
            'category': b.category,
            'has_content': bool(b.has_extracted_text)
        } for b in pagination.items]
        
        total = pagination.total
        page_num = pagination.page
        per_page_num = pagination.per_page
        pages = pagination.pages
    
    result = {
        'bookmarks': bookmarks,
        'total': total,
        'page': page_num,
        'per_page': per_page_num,
        'pages': pages
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
    redis_cache.invalidate_query_cache(cache_keys.bookmarks_pattern(user_id))
    
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService
    
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        bm = service.get_bookmark(bookmark_id)
        if not bm or bm.user_id != user_id:
            return error_response('bookmark_not_found', 'Bookmark not found or unauthorized', 404)
            
        # Store user_id and bookmark_id before deletion for cache invalidation
        user_id_for_cache = bm.user_id
        bookmark_id_for_cache = bm.id
        
        service.delete_bookmark(bm)
        
    # Invalidate caches using comprehensive cache invalidation service (outside UoW)
    from services.cache_invalidation_service import cache_invalidator
    cache_invalidator.after_content_delete(bookmark_id_for_cache, user_id_for_cache)
    
    return jsonify({'message': 'Bookmark deleted'}), 200

@bookmarks_bp.route('/url/<path:url>', methods=['DELETE'])
@jwt_required()
def delete_bookmark_by_url(url):
    """Delete bookmark by URL (for Chrome extension compatibility)"""
    user_id = int(get_jwt_identity())
    from urllib.parse import unquote
    decoded_url = unquote(url)
    
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService
    
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        bm = service.get_bookmark_by_url(user_id, decoded_url)
        if not bm:
            return error_response('bookmark_not_found', 'Bookmark not found', 404)
            
        # Store user_id and bookmark_id before deletion for cache invalidation
        user_id_for_cache = bm.user_id
        bookmark_id_for_cache = bm.id
        
        service.delete_bookmark(bm)
        
    # Invalidate caches using comprehensive cache invalidation service (outside UoW)
    from services.cache_invalidation_service import cache_invalidator
    cache_invalidator.after_content_delete(bookmark_id_for_cache, user_id_for_cache)
    
    # PRODUCTION OPTIMIZATION: Invalidate query cache for user's bookmarks
    redis_cache.invalidate_query_cache(cache_keys.bookmarks_pattern(user_id))
    
    return jsonify({'message': 'Bookmark deleted'}), 200

@bookmarks_bp.route('/lookup', methods=['GET'])
@jwt_required()
def lookup_bookmark_by_url():
    """Find the caller's bookmark saved under exactly this URL (no normalization).

    The extension resolves a removed Chrome bookmark to its Fuze id here, then deletes by id.
    The URL travels as a query parameter: inside the path, proxies may collapse the '//' of
    the scheme and percent-escapes get decoded once more than intended.
    """
    user_id = int(get_jwt_identity())
    url = request.args.get('url', '')
    if not url:
        return jsonify({'message': 'url is required'}), 400
    if url_too_long(url):
        return jsonify({'message': f'URL is longer than {MAX_URL_BYTES} bytes'}), 400

    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService

    with UnitOfWork() as uow:
        bm = BookmarkService(uow).get_bookmark_by_url(user_id, url)
        if not bm:
            return jsonify({'message': 'Bookmark not found'}), 404
        result = {'id': bm.id, 'url': bm.url, 'title': bm.title}
    return jsonify({'bookmark': result}), 200


@bookmarks_bp.route('/check-duplicate', methods=['POST'])
@jwt_required()
def check_duplicate():
    """Check if a URL is already bookmarked by the user"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return error_response('url_required', 'URL is required', 400)
    if url_too_long(url):
        return error_response('url_too_long', f'URL is longer than {MAX_URL_BYTES} bytes', 400)
    
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService

    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        existing_bookmark, duplicate_type = is_duplicate_url(service, url, user_id)
        if existing_bookmark:
            bookmark_data = {
                'id': existing_bookmark.id,
                'title': existing_bookmark.title,
                'url': existing_bookmark.url,
                'notes': existing_bookmark.notes,
                'saved_at': iso_utc(existing_bookmark.saved_at)
            }
        else:
            bookmark_data = None
    
    if existing_bookmark:
        return jsonify({
            'isDuplicate': True,
            'duplicateType': duplicate_type,
            'existingBookmark': bookmark_data
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
    import json
    import time
    
    user_id = _sse_user_id()
    if not user_id:
        return error_response('authorization_required', 'Authentication required', 401)
    
    import_key = f"import_progress:{user_id}"
    
    def generate():
        last_status = None
        start_time = time.time()
        max_connection_time = 1800  # 30 minutes maximum (for long imports)
        idle_timeout = 30  # Close connection after 30 seconds of no activity
        last_activity = time.time()
        heartbeat_interval = 15  # Send heartbeat every 15 seconds
        last_heartbeat = time.time()
        consecutive_errors = 0
        max_errors = 5
        
        while True:
            try:
                # Check if connection has been open too long
                elapsed = time.time() - start_time
                if elapsed > max_connection_time:
                    yield f"data: {json.dumps({'status': 'timeout', 'message': 'Connection timeout - please refresh'})}\n\n"
                    break
                
                progress = redis_cache.get(import_key)
                
                if not progress:
                    # No import in progress - send idle status once, then close after timeout
                    if last_status != 'no_import':
                        yield f"data: {json.dumps({'status': 'no_import', 'message': 'No import in progress'})}\n\n"
                        last_status = 'no_import'
                        last_activity = time.time()
                    else:
                        # Already sent no_import - check if we should close
                        idle_elapsed = time.time() - last_activity
                        if idle_elapsed > idle_timeout:
                            # No activity for 30 seconds, close connection
                            yield f"data: {json.dumps({'status': 'idle', 'message': 'Closing connection - no activity'})}\n\n"
                            break
                else:
                    # Import in progress - update status
                    current_status = progress.get('status', 'unknown')
                    if progress != last_status:
                        yield f"data: {json.dumps(progress)}\n\n"
                        last_status = progress
                        last_activity = time.time()  # Reset idle timer
                        
                        # If import is completed, send final update and close
                        if current_status == 'completed':
                            time.sleep(1)  # Give client time to process
                            break
                
                # Send heartbeat periodically to keep connection alive during active imports
                if progress and time.time() - last_heartbeat > heartbeat_interval:
                    yield f": heartbeat\n\n"  # SSE comment (keeps connection alive)
                    last_heartbeat = time.time()
                    consecutive_errors = 0  # Reset error count on successful heartbeat
                
                time.sleep(1)  # Check every second
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in import progress stream (attempt {consecutive_errors}/{max_errors}): {e}")
                
                # If too many consecutive errors, close connection
                if consecutive_errors >= max_errors:
                    yield f"data: {json.dumps({'status': 'error', 'message': 'Too many errors - connection closed'})}\n\n"
                    break
                
                # Send error but continue
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                time.sleep(2)  # Wait longer before retrying after error
    
    # SSE headers - optimized for Hugging Face Spaces and other reverse proxies
    import os
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',  # Nginx
        'Transfer-Encoding': 'chunked',  # Ensure chunked encoding
    }
    
    # Additional headers for Hugging Face Spaces to prevent buffering
    if os.environ.get('HUGGINGFACE_SPACE') or 'hf.space' in request.host:
        headers['X-Content-Type-Options'] = 'nosniff'
        headers['X-No-Buffering'] = '1'
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=headers
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
            return error_response('internal_error', 'Unable to check analysis status', 500, status='error')

    return jsonify(progress), 200

@bookmarks_bp.route('/progress/check', methods=['GET'])
@jwt_required()
def check_active_work():
    """
    Check if there's any active import/analysis/content-analysis work in progress
    Returns hasActiveWork: true/false to determine if SSE connection is needed
    
    Checks:
    1. Import progress (bulk import)
    2. Analysis progress (background content analysis)
    3. Pending unanalyzed content (queued for analysis)
    """
    user_id = int(get_jwt_identity())
    
    # Check Redis for active import or analysis
    import_key = f"import_progress:{user_id}"
    analysis_key = f"analysis_progress:{user_id}"
    
    import_progress = redis_cache.get(import_key)
    analysis_progress = redis_cache.get(analysis_key)
    
    # Active work exists if either progress is running (not completed/error)
    has_import_work = import_progress and import_progress.get('status') in ['processing', 'analyzing', 'in_progress']
    has_analysis_work = analysis_progress and analysis_progress.get('status') == 'analyzing'
    
    # Also check if there's pending unanalyzed content (means analysis will start soon)
    has_pending_analysis = False
    if not has_analysis_work:  # Only check DB if no active analysis
        try:
            from models import SavedContent, ContentAnalysis
            from sqlalchemy import select
            
            # Quick count of unanalyzed items for this user
            analyzed_content_ids_subquery = select(ContentAnalysis.content_id).subquery()
            analyzed_content_ids_select = select(analyzed_content_ids_subquery.c.content_id)
            unanalyzed_count = db.session.query(SavedContent).filter(
                SavedContent.user_id == user_id,
                ~SavedContent.id.in_(analyzed_content_ids_select),
                SavedContent.extracted_text.isnot(None),
                SavedContent.extracted_text != ''
            ).limit(1).count()  # Just check if ANY exist, don't count all
            
            has_pending_analysis = unanalyzed_count > 0
        except Exception as e:
            logger.error(f"Error checking pending analysis: {e}")
    
    has_active_work = has_import_work or has_analysis_work or has_pending_analysis
    
    return jsonify({
        'hasActiveWork': has_active_work,
        'importActive': has_import_work,
        'analysisActive': has_analysis_work,
        'pendingAnalysis': has_pending_analysis
    }), 200

@bookmarks_bp.route('/progress/stream', methods=['GET'])
def stream_combined_progress():
    """Combined Server-Sent Events stream for both import and analysis progress
    
    FIXED: Proper heartbeat mechanism to prevent browser reconnections
    - Sends heartbeat every 15 seconds to keep connection alive
    - Closes after 10 seconds of NO activity (no progress updates)
    - Compatible with serverless environments (max 30 min connection)
    """
    from flask import Response, stream_with_context, request
    import json
    import time
    
    user_id = _sse_user_id()
    if not user_id:
        return error_response('authorization_required', 'Authentication required', 401)
    
    import_key = f"import_progress:{user_id}"
    analysis_key = f"analysis_progress:{user_id}"
    
    def generate():
        last_import_status = None
        last_analysis_status = None
        start_time = time.time()
        max_connection_time = 1800  # 30 minutes maximum (serverless limit)
        # REMOVED idle_timeout - keep connection alive with heartbeats until client disconnects
        heartbeat_interval = 15  # CRITICAL: Send heartbeat every 15 seconds
        last_heartbeat = time.time()
        consecutive_errors = 0
        max_errors = 5
        
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connection established'})}\n\n"
        
        while True:
            try:
                current_time = time.time()
                
                # Check if connection has been open too long
                elapsed = current_time - start_time
                if elapsed > max_connection_time:
                    yield f"data: {json.dumps({'type': 'timeout', 'message': 'Connection timeout - please refresh'})}\n\n"
                    break
                
                import_progress = redis_cache.get(import_key)
                analysis_progress = redis_cache.get(analysis_key)
                
                # Check if we have any active progress
                has_activity = import_progress is not None or analysis_progress is not None
                
                if has_activity:
                    # We have activity - reset error count
                    consecutive_errors = 0
                    
                    # Send import progress if changed
                    if import_progress != last_import_status:
                        yield f"data: {json.dumps({'type': 'import', 'data': import_progress})}\n\n"
                        last_import_status = import_progress
                        last_heartbeat = current_time  # Reset heartbeat timer after data send
                        
                        # If import completed, wait a bit then continue
                        if import_progress and import_progress.get('status') == 'completed':
                            time.sleep(1)
                    
                    # Send analysis progress if changed
                    if analysis_progress != last_analysis_status:
                        yield f"data: {json.dumps({'type': 'analysis', 'data': analysis_progress})}\n\n"
                        last_analysis_status = analysis_progress
                        last_heartbeat = current_time  # Reset heartbeat timer after data send
                
                # CRITICAL: Send heartbeat comment to prevent browser reconnection
                # Even when there's no data, we need to keep connection alive
                heartbeat_elapsed = current_time - last_heartbeat
                if heartbeat_elapsed >= heartbeat_interval:
                    # Send heartbeat as SSE comment (browsers ignore but keeps connection alive)
                    yield f": heartbeat at {int(current_time)}\n\n"
                    last_heartbeat = current_time
                
                time.sleep(1)  # Check every second
                
            except GeneratorExit:
                # Client disconnected - exit gracefully
                logger.info(f"SSE client disconnected for user {user_id}")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in combined progress stream (attempt {consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Too many errors - connection closed'})}\n\n"
                    break
                
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                time.sleep(2)
    
    # SSE headers - CRITICAL configuration
    import os
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',  # Disable nginx buffering
    }
    
    # HuggingFace Space specific headers
    if os.environ.get('HUGGINGFACE_SPACE') or 'hf.space' in request.host:
        headers['X-Content-Type-Options'] = 'nosniff'
        headers['X-No-Buffering'] = '1'
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=headers
    )

@bookmarks_bp.route('/analysis/progress/stream', methods=['GET'])
def stream_analysis_progress():
    """Server-Sent Events stream for analysis progress"""
    from flask import Response, stream_with_context, request
    import json
    import time
    
    user_id = _sse_user_id()
    if not user_id:
        return error_response('authorization_required', 'Authentication required', 401)
    
    analysis_key = f"analysis_progress:{user_id}"
    
    def generate():
        last_status = None
        start_time = time.time()
        max_connection_time = 1800  # 30 minutes maximum (for long analyses)
        idle_timeout = 30  # Close connection after 30 seconds of no activity
        last_activity = time.time()
        heartbeat_interval = 15  # Send heartbeat every 15 seconds
        last_heartbeat = time.time()
        consecutive_errors = 0
        max_errors = 5
        
        while True:
            try:
                # Check if connection has been open too long
                elapsed = time.time() - start_time
                if elapsed > max_connection_time:
                    yield f"data: {json.dumps({'status': 'timeout', 'message': 'Connection timeout - please refresh'})}\n\n"
                    break
                
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
                            last_activity = time.time()
                        else:
                            # Already sent idle - check if we should close
                            idle_elapsed = time.time() - last_activity
                            if idle_elapsed > idle_timeout:
                                # No activity for 30 seconds, close connection
                                yield f"data: {json.dumps({'status': 'idle', 'message': 'Closing connection - no activity'})}\n\n"
                                break
                    except Exception as e:
                        logger.error(f"Error checking analysis status: {e}")
                        error_status = {'status': 'error', 'message': str(e)}
                        if error_status != last_status:
                            yield f"data: {json.dumps(error_status)}\n\n"
                            last_status = error_status
                else:
                    # Analysis in progress - update status
                    current_status = progress.get('status', 'unknown')
                    if progress != last_status:
                        yield f"data: {json.dumps(progress)}\n\n"
                        last_status = progress
                        last_activity = time.time()  # Reset idle timer
                
                # Send heartbeat periodically to keep connection alive during active analysis
                if progress and time.time() - last_heartbeat > heartbeat_interval:
                    yield f": heartbeat\n\n"  # SSE comment (keeps connection alive)
                    last_heartbeat = time.time()
                    consecutive_errors = 0  # Reset error count on successful heartbeat
                
                time.sleep(2)  # Check every 2 seconds (analysis is slower)
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in analysis progress stream (attempt {consecutive_errors}/{max_errors}): {e}")
                
                # If too many consecutive errors, close connection
                if consecutive_errors >= max_errors:
                    yield f"data: {json.dumps({'status': 'error', 'message': 'Too many errors - connection closed'})}\n\n"
                    break
                
                # Send error but continue
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                time.sleep(3)  # Wait longer before retrying after error
    
    # SSE headers - optimized for Hugging Face Spaces and other reverse proxies
    import os
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',  # Nginx
        'Transfer-Encoding': 'chunked',  # Ensure chunked encoding
    }
    
    # Additional headers for Hugging Face Spaces to prevent buffering
    if os.environ.get('HUGGINGFACE_SPACE') or 'hf.space' in request.host:
        headers['X-Content-Type-Options'] = 'nosniff'
        headers['X-No-Buffering'] = '1'
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=headers
    )

@bookmarks_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics with historical comparisons for percentage changes"""
    from utils.redis_utils import redis_cache
    
    try:
        user_id = int(get_jwt_identity())
        
        # PRODUCTION OPTIMIZATION: Cache dashboard stats (changes infrequently)
        cache_key = cache_keys.dashboard_stats(user_id)
        cached_stats = redis_cache.get(cache_key) if redis_cache else None
        
        if cached_stats:
            return jsonify(cached_stats), 200
        
        # Get current date and calculate comparison periods
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        month_ago = now - timedelta(days=30)
        
        from uow.unit_of_work import UnitOfWork
        from services.bookmark_service import BookmarkService
        
        with UnitOfWork() as uow:
            service = BookmarkService(uow)
            stats_data = service.get_bookmark_stats(user_id, month_ago, week_ago, two_weeks_ago)
            
        # Total Bookmarks - compare current vs 30 days ago
        total_bookmarks = stats_data['total']
        bookmarks_month_ago = stats_data['month']
        
        bookmarks_change = 0
        if bookmarks_month_ago > 0:
            bookmarks_change = ((total_bookmarks - bookmarks_month_ago) / bookmarks_month_ago) * 100
        elif total_bookmarks > 0:
            bookmarks_change = 100  # New user, 100% increase
            
        # Active Projects - compare current vs 30 days ago (Keep Project queries in blueprint for now)
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
            
        # Weekly Saves
        weekly_saves = stats_data['weekly']
        weekly_change = stats_data['trend']
        
        # Success rate: share of bookmarks that are fully processed (same rule as the dashboard)
        successful_bookmarks = db.session.query(SavedContent).filter(
            SavedContent.user_id == user_id, processed_bookmark_clause()
        ).count()
        
        success_rate = 0
        if total_bookmarks > 0:
            success_rate = (successful_bookmarks / total_bookmarks) * 100
        
        # Get previous success rate (30 days ago)
        successful_bookmarks_month_ago = db.session.query(SavedContent).filter(
            SavedContent.user_id == user_id, processed_bookmark_clause(),
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
        
        # Cache for 2 minutes (stats don't change frequently)
        if redis_cache:
            redis_cache.cache_query_result(cache_key, stats, ttl=120)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        logger.error(traceback.format_exc())
        return error_response('internal_error', 'Failed to load dashboard stats', 500)

@bookmarks_bp.route('/extract-url', methods=['POST'])
@jwt_required()
def extract_url_content():
    """Extract content from a URL for preview purposes"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return error_response('url_required', 'URL is required', 400)
    if url_too_long(url):
        return error_response('url_too_long', f'URL is longer than {MAX_URL_BYTES} bytes', 400)
    
    try:
        scraped = scrape_url_summary(url)
        extracted_text = scraped.get('content', '')
        scraped_title = scraped.get('title', '')
        headings = scraped.get('headings', [])
        meta_description = scraped.get('meta_description', '')
        quality_score = scraped.get('quality_score', 0)
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
            'message': 'Could not extract content from this URL'
        }), 200  # Return 200 instead of 500 to avoid breaking the frontend 

@bookmarks_bp.route('/all', methods=['DELETE'])
@jwt_required()
def delete_all_bookmarks():
    user_id = int(get_jwt_identity())
    from uow.unit_of_work import UnitOfWork
    from services.bookmark_service import BookmarkService
    
    with UnitOfWork() as uow:
        service = BookmarkService(uow)
        num_deleted = service.delete_all_for_user(user_id)

    # Synchronously: the import path dedupes against the cached bookmark list, so a re-import
    # right after "delete all" skipped every URL until the cache expired an hour later.
    from services.cache_invalidation_service import cache_invalidator
    cache_invalidator.invalidate_user_cache(user_id)
    return jsonify({'message': f'Deleted {num_deleted} bookmarks'}), 200 