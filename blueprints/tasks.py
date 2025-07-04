from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Task, Project, User

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@tasks_bp.route('', methods=['POST'])
@jwt_required()
def create_task():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    project_id = data.get('project_id')
    title = data.get('title')
    description = data.get('description', '')
    if not project_id or not title:
        return jsonify({'message': 'project_id and title are required'}), 400
    project = Project.query.get(project_id)
    if not project or project.user_id != user_id:
        return jsonify({'message': 'Project not found or unauthorized'}), 404
    new_task = Task(
        project_id=project_id,
        title=title.strip(),
        description=description.strip() if isinstance(description, str) else ''
    )
    try:
        db.session.add(new_task)
        db.session.commit()
        return jsonify({'message': 'Task created', 'task_id': new_task.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

@tasks_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_tasks_for_project(project_id):
    user_id = int(get_jwt_identity())
    project = Project.query.get(project_id)
    if not project or project.user_id != user_id:
        return jsonify({'message': 'Project not found or unauthorized'}), 404
    tasks = Task.query.filter_by(project_id=project_id).all()
    return jsonify({'tasks': [{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'created_at': t.created_at.isoformat()
    } for t in tasks]}), 200 