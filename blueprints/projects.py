from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, User

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

@projects_bp.route('', methods=['GET'])
@jwt_required()
def get_projects():
    """Get projects for the current authenticated user"""
    user_id = int(get_jwt_identity())
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    
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
        db.session.delete(project)
        db.session.commit()
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