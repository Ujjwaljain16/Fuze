"""
Every per-user cache key in one place.

Writers and invalidators used to spell keys independently and drifted apart: the profile was
cached as "profile:{id}" but invalidated as "user_profile:{id}", the dashboard as
"dashboard:v1:summary:{id}" vs "dashboard_summary:{id}", and project lists were never
invalidated at all. Build keys only through these functions.
"""


def profile(user_id: int) -> str:
    return f"profile:{user_id}"


def dashboard_summary(user_id: int) -> str:
    return f"dashboard:v1:summary:{user_id}"


def dashboard_stats(user_id: int) -> str:
    return f"dashboard:stats:{user_id}"


def bookmarks_page(user_id: int, page, per_page, search, category) -> str:
    return f"bookmarks:{user_id}:{page}:{per_page}:{search}:{category}"


def bookmarks_list(user_id: int) -> str:
    return f"bookmarks:{user_id}:list"


def bookmarks_pattern(user_id: int) -> str:
    return f"bookmarks:{user_id}:*"


def projects_page(user_id: int, page, per_page, include_tasks) -> str:
    return f"projects:{user_id}:{page}:{per_page}:{include_tasks}"


def projects_pattern(user_id: int) -> str:
    return f"projects:{user_id}:*"


def content_analysis(content_id: int) -> str:
    return f"content_analysis:{content_id}"


def user_summary_keys(user_id: int):
    """Single keys derived from a user's whole library."""
    return (profile(user_id), dashboard_summary(user_id), dashboard_stats(user_id),
            f"user_context:{user_id}", f"unified_recommendations:{user_id}")
