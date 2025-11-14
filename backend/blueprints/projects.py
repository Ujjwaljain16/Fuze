from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, User, Task
import logging

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

@projects_bp.route('', methods=['GET'])
@jwt_required()
def get_projects():
    """Get projects for the current authenticated user"""
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    include_tasks = request.args.get('include_tasks', default='true').lower() == 'true'
    
    pagination = Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    projects_data = []
    
    for project in pagination.items:
        project_dict = {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "technologies": project.technologies,
            "created_at": project.created_at.isoformat()
        }
        
        # Include tasks if requested
        if include_tasks:
            tasks = Task.query.filter_by(project_id=project.id).all()
            project_dict["tasks"] = [{
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "created_at": task.created_at.isoformat()
            } for task in tasks]
        
        projects_data.append(project_dict)
    
    return jsonify({
        "projects": projects_data,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200

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
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    new_project = Project(
        user_id=user_id,
        title=title.strip(),
        description=description.strip(),
        technologies=technologies.strip() if isinstance(technologies, str) else ''
    )
    
    try:
        db.session.add(new_project)
        db.session.commit()
        
        # Generate intent analysis for the new project
        try:
            from ml.intent_analysis_engine import analyze_user_intent
            
            # Build user input from project data
            user_input = f"{new_project.title} {new_project.description} {new_project.technologies}"
            
            # Generate intent analysis
            intent = analyze_user_intent(
                user_input=user_input,
                project_id=new_project.id,
                force_analysis=True,  # Force new analysis for new project
                user_id=user_id  # Use user's API key
            )
            
            # The intent analysis is automatically saved to the project by the engine
            logger.info(f"Intent analysis generated for new project: {intent.primary_goal} - {intent.project_type}")
            
        except Exception as intent_error:
            logger.warning(f"Intent analysis failed for new project: {str(intent_error)}")
            # Don't fail the project creation if intent analysis fails
            # The analysis can be generated later when needed
        
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.after_project_save(new_project.id, user_id)
        
        return jsonify({
            "message": "Project created successfully", 
            "project_id": new_project.id,
            "project": {
                "id": new_project.id,
                "title": new_project.title,
                "description": new_project.description,
                "technologies": new_project.technologies,
                "created_at": new_project.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get a specific project by ID"""
    user_id = int(get_jwt_identity())
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    return jsonify({
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "technologies": project.technologies,
        "created_at": project.created_at.isoformat()
    }), 200

@projects_bp.route('/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def get_project_tasks(project_id):
    """Get tasks for a specific project"""
    user_id = int(get_jwt_identity())
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    tasks = Task.query.filter_by(project_id=project_id).all()
    return jsonify({'tasks': [{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'created_at': t.created_at.isoformat()
    } for t in tasks]}), 200

@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update a specific project by ID"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Find the project and ensure it belongs to the current user
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    # Validate input data
    title = data.get('title')
    description = data.get('description')
    technologies = data.get('technologies', '')
    
    if not isinstance(title, str) or not title.strip():
        return jsonify({"message": "Project title is required and must be a non-empty string"}), 400
    if not isinstance(description, str) or not description.strip():
        return jsonify({"message": "Project description is required and must be a non-empty string"}), 400
    
    # Update project fields
    project.title = title.strip()
    project.description = description.strip()
    project.technologies = technologies.strip() if isinstance(technologies, str) else ''
    
    try:
        db.session.commit()
        
        # Regenerate intent analysis for the updated project
        try:
            from ml.intent_analysis_engine import analyze_user_intent
            
            # Build user input from updated project data
            user_input = f"{project.title} {project.description} {project.technologies}"
            
            # Generate fresh intent analysis
            intent = analyze_user_intent(
                user_input=user_input,
                project_id=project.id,
                force_analysis=True,  # Force new analysis for updated project
                user_id=user_id  # Use user's API key
            )
            
            # The intent analysis is automatically saved to the project by the engine
            logger.info(f"Intent analysis updated for project: {intent.primary_goal} - {intent.project_type}")
            
        except Exception as intent_error:
            logger.warning(f"Intent analysis update failed for project: {str(intent_error)}")
            # Don't fail the project update if intent analysis fails
        
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.after_project_update(project.id, user_id)
        
        return jsonify({
            "message": "Project updated successfully",
            "project": {
                "id": project.id,
                "title": project.title,
                "description": project.description,
                "technologies": project.technologies,
                "created_at": project.created_at.isoformat()
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    """Delete a specific project by ID"""
    user_id = int(get_jwt_identity())
    
    # Find the project and ensure it belongs to the current user
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    if not project:
        return jsonify({"message": "Project not found"}), 404
    
    try:
        # Store project_id and user_id before deletion for cache invalidation
        project_id_for_cache = project.id
        user_id_for_cache = project.user_id
        
        db.session.delete(project)
        db.session.commit()
        
        # Invalidate caches using comprehensive cache invalidation service
        from cache_invalidation_service import cache_invalidator
        cache_invalidator.invalidate_project_cache(project_id_for_cache)
        cache_invalidator.invalidate_user_cache(user_id_for_cache)
        
        return jsonify({"message": "Project deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500

@projects_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_projects(user_id):
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    pagination = Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    projects_data = [{
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "technologies": project.technologies,
        "created_at": project.created_at.isoformat()
    } for project in pagination.items]
    return jsonify({
        "projects": projects_data,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200 