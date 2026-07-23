"""
Projects API Blueprint
Handles project creation, reading, updating, deletion, and task aggregations.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from uow.unit_of_work import UnitOfWork
from services.project_service import ProjectService
from utils.redis_utils import redis_cache
from core.logging_config import get_logger

logger = get_logger(__name__)

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

MAX_TITLE_LENGTH = 200
MAX_DESC_LENGTH = 5000
MAX_TECH_LENGTH = 1000

def parse_bool_arg(value, default=True) -> bool:
    """Parse boolean query parameter supporting true/1/yes/on values."""
    if value is None:
        return default
    val_str = str(value).strip().lower()
    return val_str in ('true', '1', 'yes', 'on')


@projects_bp.route('', methods=['GET'])
@jwt_required()
def get_projects():
    """Get paginated projects for the authenticated user with eager task loading options."""
    try:
        user_id = int(get_jwt_identity())
        page = max(1, request.args.get('page', default=1, type=int))
        per_page = min(max(1, request.args.get('per_page', default=10, type=int)), 100)
        include_tasks = parse_bool_arg(request.args.get('include_tasks'), default=True)

        cache_key = f"projects:{user_id}:{page}:{per_page}:{include_tasks}"
        if redis_cache and redis_cache.connected:
            try:
                cached_projects = redis_cache.get(cache_key)
                if cached_projects:
                    return jsonify(cached_projects), 200
            except Exception as cache_err:
                logger.warning("projects_cache_read_failed", user_id=user_id, error=str(cache_err))

        with UnitOfWork() as uow:
            pagination = uow.projects.list_by_user(
                user_id=user_id,
                page=page,
                per_page=per_page,
                eager_load_tasks=include_tasks
            )

            projects_data = []
            for project in pagination.items:
                project_dict = {
                    "id": project.id,
                    "title": project.title,
                    "description": project.description,
                    "technologies": project.technologies,
                    "created_at": project.created_at.isoformat() if project.created_at else None
                }

                if include_tasks:
                    project_dict["tasks"] = [{
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "subtasks": [{
                            "id": st.id,
                            "title": st.title,
                            "description": st.description,
                            "completed": bool(st.completed),
                            "created_at": st.created_at.isoformat() if st.created_at else None,
                            "updated_at": st.updated_at.isoformat() if st.updated_at else None
                        } for st in getattr(t, 'subtasks', [])]
                    } for t in getattr(project, 'tasks', [])]

                projects_data.append(project_dict)

            response_data = {
                "projects": projects_data,
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages
            }

        if redis_cache and redis_cache.connected:
            try:
                redis_cache.cache_query_result(cache_key, response_data, ttl=60)
            except Exception as cache_err:
                logger.warning("projects_cache_write_failed", user_id=user_id, error=str(cache_err))

        return jsonify(response_data), 200

    except Exception:
        logger.exception("get_projects_failed")
        return jsonify({"message": "Failed to fetch projects"}), 500


@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new project for the authenticated user."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        title = data.get('title')
        description = data.get('description')
        technologies = data.get('technologies', '')

        if not isinstance(title, str) or not title.strip():
            return jsonify({"message": "Project title is required and must be a non-empty string"}), 400
        title = title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            return jsonify({"message": f"Project title cannot exceed {MAX_TITLE_LENGTH} characters"}), 400

        if not isinstance(description, str) or not description.strip():
            return jsonify({"message": "Project description is required and must be a non-empty string"}), 400
        description = description.strip()
        if len(description) > MAX_DESC_LENGTH:
            return jsonify({"message": f"Project description cannot exceed {MAX_DESC_LENGTH} characters"}), 400

        if technologies is not None:
            if not isinstance(technologies, str):
                return jsonify({"message": "Technologies must be a string"}), 400
            technologies = technologies.strip()
            if len(technologies) > MAX_TECH_LENGTH:
                return jsonify({"message": f"Technologies cannot exceed {MAX_TECH_LENGTH} characters"}), 400
        else:
            technologies = ''

        with UnitOfWork() as uow:
            user = uow.users.get_by_id(user_id)
            if not user:
                return jsonify({"message": "User not found"}), 404

            service = ProjectService(uow)
            new_project = service.create_project(
                user_id=user_id,
                title=title,
                description=description,
                technologies=technologies
            )

            p_id = new_project.id
            p_title = new_project.title
            p_desc = new_project.description
            p_tech = new_project.technologies
            p_created_at = new_project.created_at.isoformat() if new_project.created_at else None

        return jsonify({
            "message": "Project created successfully",
            "project_id": p_id,
            "project": {
                "id": p_id,
                "title": p_title,
                "description": p_desc,
                "technologies": p_tech,
                "created_at": p_created_at
            }
        }), 201

    except Exception:
        logger.exception("create_project_failed")
        return jsonify({"message": "Failed to create project"}), 500


@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id: int):
    """Get a specific project by ID."""
    try:
        user_id = int(get_jwt_identity())
        with UnitOfWork() as uow:
            project = uow.projects.get_by_id(project_id, user_id)
            if not project:
                return jsonify({"message": "Project not found"}), 404

            project_data = {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "technologies": project.technologies,
                "created_at": project.created_at.isoformat() if project.created_at else None
            }

        return jsonify(project_data), 200

    except Exception:
        logger.exception("get_project_failed", project_id=project_id)
        return jsonify({"message": "Failed to fetch project"}), 500


@projects_bp.route('/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id: int):
    """Get tasks for a specific project."""
    try:
        user_id = int(get_jwt_identity())
        with UnitOfWork() as uow:
            project = uow.projects.get_by_id(project_id, user_id)
            if not project:
                return jsonify({"message": "Project not found"}), 404

            tasks = uow.projects.get_tasks(project_id)
            tasks_data = [{
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'subtasks': [{
                    'id': st.id,
                    'title': st.title,
                    'description': st.description,
                    'completed': bool(st.completed),
                    'created_at': st.created_at.isoformat() if st.created_at else None,
                    'updated_at': st.updated_at.isoformat() if st.updated_at else None
                } for st in getattr(t, 'subtasks', [])]
            } for t in tasks]

        return jsonify({'tasks': tasks_data}), 200

    except Exception:
        logger.exception("get_project_tasks_failed", project_id=project_id)
        return jsonify({"message": "Failed to fetch project tasks"}), 500


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id: int):
    """Update a specific project by ID."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        with UnitOfWork() as uow:
            service = ProjectService(uow)
            project = service.update_project(project_id, user_id, data)

            if not project:
                return jsonify({"message": "Project not found"}), 404

            p_id = project.id
            p_title = project.title
            p_desc = project.description
            p_tech = project.technologies
            p_created_at = project.created_at.isoformat() if project.created_at else None

        return jsonify({
            "message": "Project updated successfully",
            "project": {
                "id": p_id,
                "title": p_title,
                "description": p_desc,
                "technologies": p_tech,
                "created_at": p_created_at
            }
        }), 200

    except Exception:
        logger.exception("update_project_failed", project_id=project_id)
        return jsonify({"message": "Failed to update project"}), 500


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id: int):
    """Delete a specific project by ID."""
    try:
        user_id = int(get_jwt_identity())
        with UnitOfWork() as uow:
            service = ProjectService(uow)
            if not service.delete_project(project_id, user_id):
                return jsonify({"message": "Project not found"}), 404

        return jsonify({"message": "Project deleted successfully"}), 200

    except Exception:
        logger.exception("delete_project_failed", project_id=project_id)
        return jsonify({"message": "Failed to delete project"}), 500


@projects_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_projects(user_id: int):
    """Get paginated projects for a user - strictly authorized to logged-in user."""
    try:
        current_user_id = int(get_jwt_identity())
        if current_user_id != user_id:
            logger.warning("unauthorized_user_projects_access", current_user_id=current_user_id, target_user_id=user_id)
            return jsonify({"message": "Unauthorized"}), 403

        page = max(1, request.args.get('page', default=1, type=int))
        per_page = min(max(1, request.args.get('per_page', default=10, type=int)), 100)

        with UnitOfWork() as uow:
            user = uow.users.get_by_id(user_id)
            if not user:
                return jsonify({"message": "User not found"}), 404

            pagination = uow.projects.list_by_user(user_id, page, per_page)
            projects_data = [{
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "technologies": project.technologies,
                "created_at": project.created_at.isoformat() if project.created_at else None
            } for project in pagination.items]

            response_data = {
                "projects": projects_data,
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages
            }

        return jsonify(response_data), 200

    except Exception:
        logger.exception("get_user_projects_failed", user_id=user_id)
        return jsonify({"message": "Failed to fetch user projects"}), 500