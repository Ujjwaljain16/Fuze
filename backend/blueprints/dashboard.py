"""
Dashboard API Blueprint
Combines multiple API queries into one aggregated endpoint to reduce latency and network overhead
"""

import time
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, case
from models import db, User, SavedContent, Project, Task
from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

_DEFAULT_API_KEY_STATUS = {
    'has_api_key': False,
    'api_key_status': 'none',
    'requests_today': 0,
    'requests_this_month': 0,
    'daily_limit': 1500,
    'monthly_limit': 45000,
    'can_make_request': False
}

@dashboard_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_dashboard_summary():
    """
    Aggregated dashboard endpoint - returns all dashboard metrics in ONE HTTP request.

    Combines:
    - User Profile
    - Gemini API Usage Stats
    - Bookmark Aggregate Metrics
    - Recent Bookmarks (without loading heavy TEXT blobs)
    - Recent Projects (with SQL-aggregated task counts)
    """
    start_time = time.time()
    user_id = None

    try:
        user_id = int(get_jwt_identity())
        cache_key = f"dashboard:v1:summary:{user_id}"

        # 1. Try Cache First (Versioned)
        if redis_cache.connected:
            try:
                cached_summary = redis_cache.redis_client.get(cache_key)
                if cached_summary:
                    cache_time = (time.time() - start_time) * 1000
                    logger.info("dashboard_cache_hit", latency_ms=round(cache_time), user_id=user_id)
                    return jsonify(json.loads(cached_summary)), 200
            except Exception as cache_error:
                logger.warning("dashboard_cache_read_failed", user_id=user_id, error=str(cache_error))

        response_data = {}

        # 2. Profile Info (direct primary key lookup)
        user = db.session.get(User, user_id)
        if user:
            response_data['profile'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        else:
            response_data['profile'] = None

        # 3. API Key Status (Consistent error/fallback shape)
        try:
            from services.multi_user_api_manager import get_user_api_stats
            api_stats = get_user_api_stats(user_id)
            response_data['apiKeyStatus'] = api_stats if api_stats else _DEFAULT_API_KEY_STATUS
        except Exception:
            logger.exception("dashboard_api_stats_failed", user_id=user_id)
            response_data['apiKeyStatus'] = dict(_DEFAULT_API_KEY_STATUS, api_key_status='error')

        # 4. Bookmark Metrics (UTC Timezone + SQL aggregations)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        last_week_start = week_ago - timedelta(days=7)

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
                case((SavedContent.extracted_text.isnot(None), 1), else_=0)
            ).label('successful_bookmarks')
        ).filter(SavedContent.user_id == user_id).first()

        active_projects = db.session.query(func.count(Project.id)).filter_by(
            user_id=user_id
        ).scalar() or 0

        total_bookmarks = int(stats_result.total_bookmarks or 0)
        bookmarks_this_week = int(stats_result.bookmarks_this_week or 0)
        bookmarks_last_week = int(stats_result.bookmarks_last_week or 0)
        successful_bookmarks = int(stats_result.successful_bookmarks or 0)

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

        # 5. Recent Bookmarks (DO NOT select extracted_text blob; compute has_content in SQL)
        recent_bookmarks = db.session.query(
            SavedContent.id,
            SavedContent.url,
            SavedContent.title,
            SavedContent.notes,
            SavedContent.saved_at,
            SavedContent.category,
            case((SavedContent.extracted_text.isnot(None), True), else_=False).label('has_content')
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
                'has_content': bool(b.has_content)
            }
            for b in recent_bookmarks
        ]

        # 6. Recent Projects (SQL Outer Join + Count Aggregation instead of joinedload tasks)
        recent_projects = db.session.query(
            Project.id,
            Project.title,
            Project.description,
            Project.created_at,
            func.count(Task.id).label('task_count')
        ).outerjoin(Task, Task.project_id == Project.id)\
         .filter(Project.user_id == user_id)\
         .group_by(Project.id)\
         .order_by(Project.created_at.desc()).limit(3).all()

        response_data['recentProjects'] = [
            {
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'created_at': p.created_at.isoformat() if p.created_at else None,
                'task_count': int(p.task_count or 0)
            }
            for p in recent_projects
        ]

        response_data['totalProjects'] = active_projects
        response_data['totalBookmarks'] = total_bookmarks

        # 7. Write to Versioned Cache (30s TTL)
        if redis_cache.connected:
            try:
                redis_cache.redis_client.setex(
                    cache_key,
                    30,
                    json.dumps(response_data, default=str)
                )
            except Exception as cache_error:
                logger.warning("dashboard_cache_write_failed", user_id=user_id, error=str(cache_error))

        total_time = (time.time() - start_time) * 1000
        logger.info("dashboard_generated", latency_ms=round(total_time), user_id=user_id)
        return jsonify(response_data), 200

    except Exception:
        logger.exception("dashboard_summary_failed", user_id=user_id)
        return jsonify({'error': 'Internal server error'}), 500
