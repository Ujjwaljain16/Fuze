from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, User, Task, Subtask
import logging

logger = logging.getLogger(__name__)

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
    
    # PRODUCTION OPTIMIZATION: Cache projects list (changes infrequently)
    cache_key = f"projects:{user_id}:{page}:{per_page}:{include_tasks}"
    cached_projects = redis_cache.get(cache_key) if redis_cache else None
    
    if cached_projects:
        return jsonify(cached_projects), 200
    
    from uow.unit_of_work import UnitOfWork
    
    try:
        with UnitOfWork() as uow:
            pagination = uow.projects.list_by_user(user_id, page, per_page)
            
            projects_data = []
            for project in pagination.items:
                project_dict = {
                    "id": project.id,
                    "title": project.title,
                    "description": project.description,
                    "technologies": project.technologies,
                    "created_at": project.created_at.isoformat()
                }
                
                if include_tasks:
                    tasks = uow.projects.get_tasks(project.id)
                    project_dict["tasks"] = [{
                        "id": t.id,
                        "title": t.title,
                        "description": t.description,
                        "created_at": t.created_at.isoformat(),
                        "subtasks": [{
                            "id": st.id,
                            "title": st.title,
                            "description": st.description,
                            "completed": bool(st.completed),
                            "created_at": st.created_at.isoformat(),
                            "updated_at": st.updated_at.isoformat() if st.updated_at else None
                        } for st in t.subtasks]
                    } for t in tasks]
                
                projects_data.append(project_dict)
            
            response_data = {
                "projects": projects_data,
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages
            }
    except Exception as e:
        logger.error(f"project_list_failed user_id={user_id} error={str(e)}")
        return jsonify({"message": "Failed to fetch projects"}), 500
    
    # Cache for 1 minute (projects don't change frequently)
    if redis_cache:
        redis_cache.cache_query_result(cache_key, response_data, ttl=60)
    
    return jsonify(response_data), 200

@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    technologies = data.get('technologies', '')
    
    if not isinstance(title, str) or not title.strip():
        return jsonify({"message": "Project title is required and must be a non-empty string"}), 400
    if not isinstance(description, str) or not description.strip():
        return jsonify({"message": "Project description is required and must be a non-empty string"}), 400
    
    from uow.unit_of_work import UnitOfWork
    from services.project_service import ProjectService
    
    try:
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

            # Extract primitives inside session boundary — after __exit__ SQLAlchemy
            # expires all instance attributes; accessing them on a detached object is unsafe.
            new_project_id = new_project.id
            new_project_title = new_project.title
            new_project_description = new_project.description
            new_project_technologies = new_project.technologies
            new_project_created_at = new_project.created_at.isoformat()

        # ML operations (embedding and intent analysis) have been migrated to event handlers
        # Cache invalidation has been migrated to event handlers

        return jsonify({
            "message": "Project created successfully",
            "project_id": new_project_id,
            "project": {
                "id": new_project_id,
                "title": new_project_title,
                "description": new_project_description,
                "technologies": new_project_technologies,
                "created_at": new_project_created_at
            }
        }), 201
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get a specific project by ID"""
    user_id = int(get_jwt_identity())
    from uow.unit_of_work import UnitOfWork
    
    with UnitOfWork() as uow:
        project = uow.projects.get_by_id(project_id, user_id)
        if not project:
            return jsonify({"message": "Project not found"}), 404
        
        # Serialize inside session boundary to avoid DetachedInstanceError
        project_data = {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "technologies": project.technologies,
            "created_at": project.created_at.isoformat()
        }
    
    return jsonify(project_data), 200

@projects_bp.route('/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id):
    """Get tasks for a specific project"""
    user_id = int(get_jwt_identity())
    from uow.unit_of_work import UnitOfWork
    
    with UnitOfWork() as uow:
        project = uow.projects.get_by_id(project_id, user_id)
        if not project:
            return jsonify({"message": "Project not found"}), 404
        
        tasks = uow.projects.get_tasks(project_id)
        # Serialize inside session boundary to avoid DetachedInstanceError
        tasks_data = [{
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'created_at': t.created_at.isoformat(),
            'subtasks': [{
                'id': st.id,
                'title': st.title,
                'description': st.description,
                'completed': bool(st.completed),
                'created_at': st.created_at.isoformat(),
                'updated_at': st.updated_at.isoformat() if st.updated_at else None
            } for st in t.subtasks]
        } for t in tasks]
    
    return jsonify({'tasks': tasks_data}), 200

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update a specific project by ID"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    from uow.unit_of_work import UnitOfWork
    from services.project_service import ProjectService
    
    try:
        with UnitOfWork() as uow:
            service = ProjectService(uow)
            project = service.update_project(project_id, user_id, data)
            
            if not project:
                return jsonify({"message": "Project not found"}), 404
                
            p_id = project.id
            p_title = project.title
            p_desc = project.description
            p_tech = project.technologies
            p_created_at = project.created_at.isoformat()
        
        # ML operations (embedding and intent analysis) have been migrated to event handlers

        # Cache invalidation has been migrated to event handlers
        
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
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """Delete a specific project by ID"""
    user_id = int(get_jwt_identity())
    
    from uow.unit_of_work import UnitOfWork
    from services.project_service import ProjectService
    
    try:
        with UnitOfWork() as uow:
            service = ProjectService(uow)
            if not service.delete_project(project_id, user_id):
                return jsonify({"message": "Project not found"}), 404
                
        # Cache invalidation has been migrated to event handlers
        
        return jsonify({"message": "Project deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_projects(user_id):
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    from uow.unit_of_work import UnitOfWork
    with UnitOfWork() as uow:
        user = uow.users.get_by_id(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404
        pagination = uow.projects.list_by_user(user_id, page, per_page)
        # Serialize inside session boundary to avoid DetachedInstanceError
        projects_data = [{
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "technologies": project.technologies,
            "created_at": project.created_at.isoformat()
        } for project in pagination.items]
        response_data = {
            "projects": projects_data,
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "pages": pagination.pages
        }
    return jsonify(response_data), 200 