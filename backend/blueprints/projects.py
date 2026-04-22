from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, User, Task, Subtask
from uow.unit_of_work import UnitOfWork
from services.project_service import ProjectService
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

@projects_bp.route('', methods=['GET'])
@jwt_required()
def get_projects():
    """Get projects for the current authenticated user"""
    from utils.redis_utils import redis_cache
    
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    include_tasks = request.args.get('include_tasks', default='true').lower() == 'true'
    
    # PRODUCTION OPTIMIZATION: Cache projects list
    cache_key = f"projects:{user_id}:{page}:{per_page}:{include_tasks}"
    cached_projects = redis_cache.get(cache_key) if redis_cache else None
    
    if cached_projects:
        logger.info("project_list_cache_hit", user_id=user_id)
        return jsonify(cached_projects), 200
    
    try:
        uow = UnitOfWork()
    pagination = uow.projects.list_by_user(user_id, page, per_page)
    
    projects_data = []
    for project in pagination.items:
        project_dict = project.to_dict()
        project_dict["created_at"] = project.created_at.isoformat()
        
        if include_tasks:
            tasks = uow.projects.get_tasks(project.id)
            project_dict["tasks"] = [{
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "created_at": t.created_at.isoformat(),
                "subtasks": [st.to_dict() for st in t.subtasks]
            } for t in tasks]
        
        projects_data.append(project_dict)
    
    response_data = {
        "projects": projects_data,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }
    
    if redis_cache:
        redis_cache.cache_query_result(cache_key, response_data, ttl=60)
    
    logger.info("project_list_success", user_id=user_id, count=len(projects_data))
    return jsonify(response_data), 200
    
    except Exception as e:
        logger.error("project_list_failed", user_id=user_id, error=str(e))
        return jsonify({"message": "Failed to fetch projects"}), 500

@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    
    if not title or not description:
        return jsonify({"message": "Title and description are required"}), 400
    
    service = ProjectService(UnitOfWork())
    try:
        new_project = service.create_project(
            user_id=user_id,
            title=title,
            description=description,
            technologies=data.get('technologies', '')
        )
        
        logger.info("project_create_success", user_id=user_id, project_id=new_project.id)
        return jsonify({
            "message": "Project created successfully", 
            "project_id": new_project.id,
            "project": new_project.to_dict()
        }), 201
    except Exception as e:
        logger.error("project_creation_failed", user_id=user_id, error=str(e))
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get a specific project by ID"""
    user_id = int(get_jwt_identity())
    uow = UnitOfWork()
    project = uow.projects.get_by_id(project_id, user_id)
    if not project:
        logger.warning("project_get_not_found", project_id=project_id, user_id=user_id)
        return jsonify({"message": "Project not found"}), 404
    
    logger.info("project_get_success", project_id=project_id, user_id=user_id)
    return jsonify(project.to_dict()), 200

@projects_bp.route('/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id):
    """Get tasks for a specific project"""
    user_id = int(get_jwt_identity())
    uow = UnitOfWork()
    project = uow.projects.get_by_id(project_id, user_id)
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    tasks = uow.projects.get_tasks(project_id)
    logger.info("project_tasks_get_success", project_id=project_id, user_id=user_id, count=len(tasks))
    return jsonify({'tasks': [{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'created_at': t.created_at.isoformat(),
        'subtasks': [st.to_dict() for st in t.subtasks]
    } for t in tasks]}), 200

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update a specific project by ID"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    service = ProjectService(UnitOfWork())
    project = service.update_project(project_id, user_id, data)
    
    if not project:
        logger.warning("project_update_not_found", project_id=project_id, user_id=user_id)
        return jsonify({"message": "Project not found"}), 404
        
    logger.info("project_update_success", project_id=project_id, user_id=user_id)
    return jsonify({
        "message": "Project updated successfully",
        "project": project.to_dict()
    }), 200

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """Delete a specific project by ID"""
    user_id = int(get_jwt_identity())
    service = ProjectService(UnitOfWork())
    
    if service.delete_project(project_id, user_id):
        logger.info("project_delete_success", project_id=project_id, user_id=user_id)
        return jsonify({"message": "Project deleted successfully"}), 200
    else:
        logger.warning("project_delete_not_found", project_id=project_id, user_id=user_id)
        return jsonify({"message": "Project not found"}), 404

@projects_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_projects(user_id):
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    uow = UnitOfWork()
    user = uow.users.get_by_id(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    pagination = uow.projects.list_by_user(user_id, page, per_page)
    projects_data = []
    for project in pagination.items:
        p_dict = project.to_dict()
        p_dict["created_at"] = project.created_at.isoformat()
        projects_data.append(p_dict)
    return jsonify({
        "projects": projects_data,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200