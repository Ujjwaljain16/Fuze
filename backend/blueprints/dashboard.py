#!/usr/bin/env python3
"""
Dashboard Blueprint - Aggregated endpoint for fast dashboard loading
Combines multiple API calls into one to reduce latency and network overhead
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, SavedContent, Project
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    """
    Aggregated dashboard endpoint - returns all dashboard data in ONE request
    
    Combines:
    - Profile info
    - API key status
    - Bookmark stats
    - Recent bookmarks
    - Recent projects
    
    This replaces 5-6 separate API calls with 1 optimized query
    """
    import time
    start_time = time.time()
    
    try:
        user_id = int(get_jwt_identity())
        
        # CRITICAL: Cache the entire dashboard response for 30 seconds
        # This prevents duplicate calls from hammering the database
        from utils.redis_utils import RedisCache
        redis_cache = RedisCache()
        
        cache_key = f"dashboard:summary:{user_id}"
        
        # Try cache first
        if redis_cache.connected:
            try:
                import json
                cached_summary = redis_cache.redis_client.get(cache_key)
                if cached_summary:
                    cache_time = (time.time() - start_time) * 1000
                    logger.info(f"Dashboard cache hit ({cache_time:.0f}ms)")
                    return jsonify(json.loads(cached_summary)), 200
            except Exception as cache_error:
                logger.warning(f"Cache read failed: {cache_error}")
        
        # Cache miss - fetch all data in parallel using Promise.all equivalent
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        response_data = {}
        
        # 1. Get Profile (lightweight)
        user = db.session.query(User).filter_by(id=user_id).first()
        if user:
            response_data['profile'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        else:
            response_data['profile'] = None
        
        # 2. Get API Key Status (from existing function with caching)
        try:
            from services.multi_user_api_manager import get_user_api_stats
            api_stats = get_user_api_stats(user_id)
            
            if not api_stats:
                response_data['apiKeyStatus'] = {
                    'has_api_key': False,
                    'api_key_status': 'none',
                    'requests_today': 0,
                    'requests_this_month': 0,
                    'daily_limit': 1500,
                    'monthly_limit': 45000,
                    'can_make_request': False
                }
            else:
                response_data['apiKeyStatus'] = api_stats
        except Exception as e:
            logger.error(f"Error getting API key status: {e}")
            response_data['apiKeyStatus'] = {'has_api_key': False, 'api_key_status': 'error'}
        
        # 3. Get Dashboard Stats (OPTIMIZED: Single query instead of 5)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        last_week_start = week_ago - timedelta(days=7)
        
        # Execute all stats in ONE query using conditional aggregations
        from sqlalchemy import case
        
        stats_result = db.session.query(
            func.count(SavedContent.id).label('total_bookmarks'),
            func.sum(
                case((SavedContent.saved_at >= week_ago, 1), else_=0)
            ).label('bookmarks_this_week'),
            func.sum(
                case(
                    ((SavedContent.saved_at >= last_week_start) & (SavedContent.saved_at < week_ago), 1),
                    else_=0
                )
            ).label('bookmarks_last_week'),
            func.sum(
                case((SavedContent.extracted_text != None, 1), else_=0)
            ).label('successful_bookmarks')
        ).filter(SavedContent.user_id == user_id).first()
        
        # Get project count (separate simple query)
        active_projects = db.session.query(func.count(Project.id)).filter_by(
            user_id=user_id
        ).scalar() or 0
        
        # Extract results (handle None values from aggregations)
        total_bookmarks = int(stats_result.total_bookmarks or 0)
        bookmarks_this_week = int(stats_result.bookmarks_this_week or 0)
        bookmarks_last_week = int(stats_result.bookmarks_last_week or 0)
        successful_bookmarks = int(stats_result.successful_bookmarks or 0)
        
        # Calculate change
        if bookmarks_last_week > 0:
            bookmark_change = ((bookmarks_this_week - bookmarks_last_week) / bookmarks_last_week) * 100
        else:
            bookmark_change = 100 if bookmarks_this_week > 0 else 0
        
        success_rate = (successful_bookmarks / total_bookmarks * 100) if total_bookmarks > 0 else 0
        
        response_data['stats'] = {
            'total_bookmarks': {
                'value': total_bookmarks,
                'change': f"{bookmark_change:+.1f}%",
                'change_value': int(bookmark_change)
            },
            'active_projects': {
                'value': active_projects,
                'change': '0',
                'change_value': 0
            },
            'weekly_saves': {
                'value': bookmarks_this_week,
                'change': f"{bookmark_change:+.1f}%",
                'change_value': int(bookmark_change)
            },
            'success_rate': {
                'value': round(success_rate, 1),
                'change': '0%',
                'change_value': 0
            }
        }
        
        # 4. Get Recent Bookmarks (5 most recent) - optimized with column selection
        recent_bookmarks = db.session.query(
            SavedContent.id,
            SavedContent.url,
            SavedContent.title,
            SavedContent.notes,
            SavedContent.saved_at,
            SavedContent.category,
            SavedContent.extracted_text
        ).filter_by(
            user_id=user_id
        ).order_by(SavedContent.saved_at.desc()).limit(5).all()
        
        response_data['recentBookmarks'] = [
            {
                'id': b.id,
                'url': b.url,
                'title': b.title,
                'notes': b.notes,
                'saved_at': b.saved_at.isoformat() if b.saved_at else None,
                'category': b.category,
                'has_content': b.extracted_text is not None
            }
            for b in recent_bookmarks
        ]
        
        # 5. Get Recent Projects (3 most recent)
        recent_projects = db.session.query(Project).filter_by(
            user_id=user_id
        ).options(joinedload(Project.tasks)).order_by(Project.created_at.desc()).limit(3).all()
        
        response_data['recentProjects'] = [
            {
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'created_at': p.created_at.isoformat() if p.created_at else None,
                'task_count': len(p.tasks) if hasattr(p, 'tasks') else 0
            }
            for p in recent_projects
        ]
        
        response_data['totalProjects'] = active_projects
        response_data['totalBookmarks'] = total_bookmarks
        
        # Prepare final response
        total_time = (time.time() - start_time) * 1000
        logger.info(f"Dashboard summary generated ({total_time:.0f}ms)")
        
        # Cache for 30 seconds (balance between freshness and performance)
        if redis_cache.connected:
            try:
                import json
                redis_cache.redis_client.setex(
                    cache_key,
                    30,  # 30 seconds TTL
                    json.dumps(response_data)
                )
            except Exception as cache_error:
                logger.warning(f"Cache write failed: {cache_error}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
