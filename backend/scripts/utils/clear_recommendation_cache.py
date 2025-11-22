#!/usr/bin/env python3
"""
Quick utility to clear recommendation-related caches
Usage: python clear_recommendation_cache.py [user_id] [--all]

If user_id is provided, clears caches for that specific user.
If --all is provided, clears ALL recommendation caches (admin only).
If no arguments, shows usage information.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def clear_user_recommendation_cache(user_id):
    """Clear recommendation caches thoroughly for a specific user"""
    try:
        from services.cache_invalidation_service import CacheInvalidationService
        from utils.redis_utils import redis_cache
        
        print(f"  📦 Clearing Redis recommendation caches for user {user_id}...")
        success1 = CacheInvalidationService.invalidate_recommendation_cache(user_id)
        
        print(f"  🧠 Clearing in-memory Gemini analyzer cache...")
        try:
            from ml.unified_recommendation_orchestrator import clear_gemini_analyzer_cache
            cleared_gemini = clear_gemini_analyzer_cache()
            print(f"     Cleared {cleared_gemini} Gemini analyzer instances")
        except Exception as e:
            print(f"     Failed to clear Gemini cache: {e}")
        
        print(f"  💾 Clearing database intent analysis cache for user {user_id}...")
        try:
            from models import db, Project
            from run_production import app
            with app.app_context():
                cleared_projects = db.session.query(Project).filter(
                    Project.user_id == user_id,
                    Project.intent_analysis.isnot(None)
                ).update({"intent_analysis": None})
                db.session.commit()
                print(f"     Cleared intent analysis from {cleared_projects} projects")
        except Exception as e:
            print(f"     Failed to clear database intent analysis cache: {e}")
        
        print(f"   Clearing additional cache patterns for user {user_id}...")
        additional_patterns = [
            f"*ensemble_recommendations:*:{user_id}:*",
            f"*gemini_recommendations:*:{user_id}:*",
            f"*opt_recommendations:{user_id}",
            f"*fast_recommendations:{user_id}",
            f"*learning_path_recommendations:{user_id}*"
        ]
        for pattern in additional_patterns:
            try:
                count = redis_cache.delete_keys_pattern(pattern)
                if count > 0:
                    print(f"     Cleared {count} keys matching {pattern}")
            except Exception as e:
                print(f"     Failed to clear pattern {pattern}: {e}")

        if success1:
            print(f" Cleared recommendation caches thoroughly for user {user_id}")
            return True
        else:
            print(f" Failed to clear recommendation caches for user {user_id}")
            return False
    except Exception as e:
        print(f" Error clearing recommendation caches for user {user_id}: {e}")
        return False

def clear_all_recommendation_caches():
    """Clear ALL recommendation caches thoroughly (admin operation)"""
    try:
        from services.cache_invalidation_service import CacheInvalidationService
        from utils.redis_utils import redis_cache
        
        print("  📦 Clearing Redis recommendation caches...")
        success1 = CacheInvalidationService.invalidate_recommendation_cache()  # No user_id = clear all
        
        print("  🧠 Clearing in-memory Gemini analyzer cache...")
        try:
            from ml.unified_recommendation_orchestrator import clear_gemini_analyzer_cache
            cleared_gemini = clear_gemini_analyzer_cache()
            print(f"     Cleared {cleared_gemini} Gemini analyzer instances")
        except Exception as e:
            print(f"     Failed to clear Gemini cache: {e}")
        
        print("  💾 Clearing database intent analysis cache...")
        try:
            from models import db, Project
            from run_production import app
            with app.app_context():
                cleared_projects = db.session.query(Project).filter(
                    Project.intent_analysis.isnot(None)
                ).update({"intent_analysis": None})
                db.session.commit()
                print(f"     Cleared intent analysis from {cleared_projects} projects")
        except Exception as e:
            print(f"     Failed to clear database intent analysis cache: {e}")
        
        print("   Clearing additional cache patterns...")
        additional_patterns = [
            "*ensemble_recommendations:*",
            "*gemini_recommendations:*",
            "*opt_recommendations:*",
            "*fast_recommendations:*",
            "*learning_path_recommendations:*"
        ]
        for pattern in additional_patterns:
            try:
                count = redis_cache.delete_keys_pattern(pattern)
                if count > 0:
                    print(f"     Cleared {count} keys matching {pattern}")
            except Exception as e:
                print(f"     Failed to clear pattern {pattern}: {e}")

        if success1:
            print(" Cleared ALL recommendation caches thoroughly")
            return True
        else:
            print(" Failed to clear ALL recommendation caches")
            return False
    except Exception as e:
        print(f" Error clearing all recommendation caches: {e}")
        return False

def clear_user_context_cache(user_id):
    """Clear context caches (suggested-contexts, recent-contexts) for a specific user"""
    try:
        from utils.redis_utils import redis_cache
        context_keys = [
            f"suggested_contexts:{user_id}",
            f"recent_contexts:{user_id}"
        ]

        cleared_count = 0
        for key in context_keys:
            try:
                redis_cache.delete_cache(key)
                cleared_count += 1
                print(f" Cleared context cache: {key}")
            except Exception as e:
                print(f" Failed to clear context cache {key}: {e}")

        print(f" Cleared {cleared_count}/{len(context_keys)} context cache keys for user {user_id}")
        return cleared_count > 0
    except Exception as e:
        print(f" Error clearing context caches for user {user_id}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Clear recommendation-related caches')
    parser.add_argument('user_id', nargs='?', type=int, help='User ID to clear caches for')
    parser.add_argument('--all', action='store_true', help='Clear ALL recommendation caches (admin only)')
    parser.add_argument('--context-only', action='store_true', help='Clear only context caches (suggested-contexts, recent-contexts)')

    args = parser.parse_args()

    if args.all:
        print("🗑️ Clearing ALL recommendation caches...")
        success = clear_all_recommendation_caches()
        if success:
            print("🎉 All caches cleared successfully!")
        else:
            print("💥 Failed to clear some caches!")
        return success

    if not args.user_id:
        print("Usage:")
        print("  python clear_recommendation_cache.py <user_id>          # Clear caches for specific user")
        print("  python clear_recommendation_cache.py --all              # Clear ALL caches (admin)")
        print("  python clear_recommendation_cache.py <user_id> --context-only  # Clear only context caches")
        print()
        print("Examples:")
        print("  python clear_recommendation_cache.py 123               # Clear user 123's caches")
        print("  python clear_recommendation_cache.py --all             # Clear everything")
        return False

    user_id = args.user_id

    if args.context_only:
        print(f"🗑️ Clearing context caches for user {user_id}...")
        success = clear_user_context_cache(user_id)
    else:
        print(f"🗑️ Clearing ALL recommendation caches for user {user_id}...")
        success1 = clear_user_recommendation_cache(user_id)
        success2 = clear_user_context_cache(user_id)
        success = success1 and success2

    if success:
        print(f"🎉 Caches cleared successfully for user {user_id}!")
    else:
        print(f"💥 Failed to clear some caches for user {user_id}!")
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
