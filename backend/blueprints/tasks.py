import json
from typing import Optional, Tuple
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import joinedload

from models import db, Task, Project, SavedContent, Subtask
from utils.gemini_utils import get_gemini_response
from core.logging_config import get_logger

logger = get_logger(__name__)

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

MAX_TITLE_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 10000
MAX_AI_TASKS = 20


# --- Helper Functions ---

def get_user_project(project_id: int, user_id: int) -> Optional[Project]:
    """Fetch project and verify ownership"""
    project = db.session.get(Project, project_id)
    if not project or project.user_id != user_id:
        return None
    return project


def get_user_task(task_id: int, user_id: int) -> Tuple[Optional[Task], Optional[Project]]:
    """Fetch task and verify user ownership through parent project"""
    task = db.session.get(Task, task_id)
    if not task:
        return None, None
    project = db.session.get(Project, task.project_id)
    if not project or project.user_id != user_id:
        return None, None
    return task, project


def get_user_subtask(subtask_id: int, user_id: int) -> Tuple[Optional[Subtask], Optional[Task], Optional[Project]]:
    """Fetch subtask and verify user ownership through parent task and project"""
    subtask = db.session.get(Subtask, subtask_id)
    if not subtask:
        return None, None, None
    task, project = get_user_task(subtask.task_id, user_id)
    if not task or not project:
        return None, None, None
    return subtask, task, project


# --- Task Endpoints ---

@tasks_bp.route('', methods=['POST'])
@jwt_required()
def create_task():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    project_id = data.get('project_id')
    raw_title = str(data.get('title', '')).strip()
    raw_description = str(data.get('description', '')).strip() if data.get('description') is not None else ''

    if not project_id or not raw_title:
        return jsonify({'message': 'project_id and title are required'}), 400

    if len(raw_title) > MAX_TITLE_LENGTH:
        return jsonify({'message': f'Title exceeds maximum length of {MAX_TITLE_LENGTH} characters'}), 400

    if len(raw_description) > MAX_DESCRIPTION_LENGTH:
        return jsonify({'message': f'Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH} characters'}), 400

    project = get_user_project(project_id, user_id)
    if not project:
        return jsonify({'message': 'Project not found or unauthorized'}), 404

    new_task = Task(
        project_id=project_id,
        title=raw_title,
        description=raw_description
    )

    try:
        # Generate embedding for task BEFORE committing
        try:
            from utils.embedding_utils import get_task_embedding
            new_task.embedding = get_task_embedding(new_task)
        except Exception as e:
            logger.warning("task_embedding_generation_failed", extra={"error": str(e)})

        db.session.add(new_task)
        db.session.commit()
        return jsonify({'message': 'Task created', 'task_id': new_task.id}), 201
    except Exception:
        db.session.rollback()
        logger.exception("create_task_failed", extra={"user_id": user_id, "project_id": project_id})
        return jsonify({'message': 'Internal server error'}), 500


@tasks_bp.route('/project/<int:project_id>', methods=['GET'])
@jwt_required()
def get_tasks_for_project(project_id):
    user_id = int(get_jwt_identity())
    project = get_user_project(project_id, user_id)
    if not project:
        return jsonify({'message': 'Project not found or unauthorized'}), 404

    # Optimize subtask loading with joinedload to eliminate N+1 queries
    tasks = db.session.query(Task).options(
        joinedload(Task.subtasks)
    ).filter(
        Task.project_id == project_id
    ).order_by(Task.created_at.asc()).all()

    return jsonify({'tasks': [{
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
        } for st in t.subtasks]
    } for t in tasks]}), 200


@tasks_bp.route('/ai-breakdown', methods=['POST'])
@jwt_required()
def ai_task_breakdown():
    """
    AI-powered task breakdown using Gemini
    Automatically generates tasks from project description
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    project_id = data.get('project_id')
    project_description = str(data.get('project_description', '')).strip()[:2000]
    skill_level = str(data.get('skill_level', 'intermediate')).strip()[:50]

    if not project_id:
        return jsonify({'success': False, 'error': 'project_id is required'}), 400

    project = get_user_project(project_id, user_id)
    if not project:
        return jsonify({'success': False, 'error': 'Project not found or unauthorized'}), 404

    try:
        # Get user's relevant bookmarks for context
        user_bookmarks = db.session.query(SavedContent).filter_by(user_id=user_id).limit(20).all()
        bookmark_technologies = set()
        for bm in user_bookmarks:
            if bm.tags:
                bookmark_technologies.update([t.strip().lower() for t in bm.tags.split(',') if t.strip()])

        # Build Gemini prompt
        prompt = f"""
You are an expert project manager and technical mentor. Break down the following project into detailed, actionable tasks.

Project: {project.title}
Description: {project_description or project.description or 'No description provided'}
Technologies: {project.technologies or 'Not specified'}
User Skill Level: {skill_level}
User's Known Technologies: {', '.join(list(bookmark_technologies)[:10]) if bookmark_technologies else 'None specified'}

Generate a JSON array of tasks with this exact structure:
[
  {{
    "title": "Task title (clear and actionable)",
    "description": "Detailed description (3-4 sentences with specific steps)",
    "estimated_time": "realistic time estimate (e.g., '2 hours', '1 day')",
    "difficulty": "beginner|intermediate|advanced",
    "prerequisites": ["list", "of", "previous", "task", "titles"],
    "key_technologies": ["tech1", "tech2"],
    "success_criteria": "How to know this task is complete"
  }}
]

Guidelines:
1. Create 5-8 tasks that form a logical progression
2. Start with setup/foundation tasks
3. Build towards the main functionality
4. Include testing and documentation tasks
5. Match difficulty to user's skill level
6. Be specific about technologies and tools
7. Each task should take 30 minutes to 1 day
8. Prerequisites should reference earlier task titles

Return ONLY the JSON array, no additional text.
"""

        logger.info("requesting_gemini_task_breakdown", extra={"project_id": project_id, "user_id": user_id})

        response = get_gemini_response(prompt, user_id=user_id)

        if not response:
            return jsonify({
                'success': False,
                'error': 'Failed to generate task breakdown',
                'details': 'No response from AI'
            }), 500

        # Parse response safely
        try:
            ai_response = response.strip() if isinstance(response, str) else str(response).strip()
            if '```json' in ai_response:
                ai_response = ai_response.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_response:
                ai_response = ai_response.split('```')[1].split('```')[0].strip()

            tasks_data = json.loads(ai_response)

            if not isinstance(tasks_data, list):
                raise ValueError("Response is not a list of tasks")

            # Limit tasks data to prevent DB flooding
            tasks_data = tasks_data[:MAX_AI_TASKS]

            created_tasks = []
            for task_data in tasks_data:
                if not isinstance(task_data, dict):
                    continue

                title = str(task_data.get('title', 'Untitled Task')).strip()[:MAX_TITLE_LENGTH]
                if not title:
                    title = "Untitled Task"

                desc_text = str(task_data.get('description', '')).strip()[:MAX_DESCRIPTION_LENGTH]

                desc_json = json.dumps({
                    'description': desc_text,
                    'estimated_time': str(task_data.get('estimated_time', ''))[:100],
                    'difficulty': str(task_data.get('difficulty', skill_level))[:50],
                    'prerequisites': task_data.get('prerequisites', []) if isinstance(task_data.get('prerequisites'), list) else [],
                    'key_technologies': task_data.get('key_technologies', []) if isinstance(task_data.get('key_technologies'), list) else [],
                    'success_criteria': str(task_data.get('success_criteria', ''))[:500]
                })

                new_task = Task(
                    project_id=project_id,
                    title=title,
                    description=desc_json
                )
                db.session.add(new_task)
                created_tasks.append({
                    'title': title,
                    'description': desc_text,
                    'estimated_time': str(task_data.get('estimated_time', '')),
                    'difficulty': str(task_data.get('difficulty', '')),
                    'prerequisites': task_data.get('prerequisites', []) if isinstance(task_data.get('prerequisites'), list) else [],
                    'key_technologies': task_data.get('key_technologies', []) if isinstance(task_data.get('key_technologies'), list) else [],
                    'success_criteria': str(task_data.get('success_criteria', ''))
                })

            db.session.commit()
            logger.info("ai_task_breakdown_created", extra={"count": len(created_tasks), "project_id": project_id})

            return jsonify({
                'success': True,
                'message': f'Generated {len(created_tasks)} tasks successfully',
                'tasks': created_tasks,
                'ai_powered': True
            }), 201

        except json.JSONDecodeError as e:
            safe_resp = str(response)[:200]
            logger.exception("gemini_json_parse_failed", extra={"response_snippet": safe_resp})
            return jsonify({
                'success': False,
                'error': 'Failed to parse AI response'
            }), 500
        except Exception:
            db.session.rollback()
            logger.exception("processing_ai_breakdown_failed", extra={"project_id": project_id})
            return jsonify({
                'success': False,
                'error': 'Error processing task breakdown'
            }), 500

    except Exception:
        db.session.rollback()
        logger.exception("ai_task_breakdown_route_failed", extra={"project_id": project_id})
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """Update a task"""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    task, project = get_user_task(task_id, user_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    try:
        title_changed = False
        if 'title' in data:
            title = str(data['title']).strip()
            if not title:
                return jsonify({'success': False, 'error': 'Task title cannot be empty'}), 400
            if len(title) > MAX_TITLE_LENGTH:
                return jsonify({'success': False, 'error': f'Title exceeds maximum length of {MAX_TITLE_LENGTH}'}), 400
            task.title = title
            title_changed = True

        if 'description' in data:
            desc = str(data['description']).strip() if data['description'] is not None else ''
            if len(desc) > MAX_DESCRIPTION_LENGTH:
                return jsonify({'success': False, 'error': f'Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}'}), 400
            task.description = desc

        if title_changed:
            try:
                from utils.embedding_utils import get_task_embedding
                task.embedding = get_task_embedding(task)
            except Exception as e:
                logger.warning("task_embedding_update_failed", extra={"error": str(e)})

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Task updated successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description
            }
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("update_task_failed", extra={"task_id": task_id, "user_id": user_id})
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """Delete a task"""
    user_id = int(get_jwt_identity())
    task, project = get_user_task(task_id, user_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    try:
        db.session.delete(task)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("delete_task_failed", extra={"task_id": task_id, "user_id": user_id})
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ============================================================================
# SUBTASK ENDPOINTS
# ============================================================================

@tasks_bp.route('/<int:task_id>/subtasks', methods=['POST'])
@jwt_required()
def create_subtask(task_id):
    """Create a new subtask for a task"""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    task, project = get_user_task(task_id, user_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    title = str(data.get('title', '')).strip()
    if not title:
        return jsonify({'success': False, 'error': 'Subtask title is required'}), 400

    if len(title) > MAX_TITLE_LENGTH:
        return jsonify({'success': False, 'error': f'Title exceeds maximum length of {MAX_TITLE_LENGTH}'}), 400

    description = str(data.get('description', '')).strip() if data.get('description') is not None else ''
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return jsonify({'success': False, 'error': f'Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}'}), 400

    new_subtask = Subtask(
        task_id=task_id,
        title=title,
        description=description,
        completed=0
    )

    try:
        try:
            from utils.embedding_utils import get_subtask_embedding
            new_subtask.embedding = get_subtask_embedding(new_subtask)
        except Exception as e:
            logger.warning("subtask_embedding_generation_failed", extra={"error": str(e)})

        db.session.add(new_subtask)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Subtask created successfully',
            'subtask': {
                'id': new_subtask.id,
                'title': new_subtask.title,
                'description': new_subtask.description,
                'completed': bool(new_subtask.completed),
                'created_at': new_subtask.created_at.isoformat() if new_subtask.created_at else None,
                'updated_at': new_subtask.updated_at.isoformat() if new_subtask.updated_at else None
            }
        }), 201

    except Exception:
        db.session.rollback()
        logger.exception("create_subtask_failed", extra={"task_id": task_id, "user_id": user_id})
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@tasks_bp.route('/<int:task_id>/subtasks', methods=['GET'])
@jwt_required()
def get_subtasks(task_id):
    """Get all subtasks for a task"""
    user_id = int(get_jwt_identity())
    task, project = get_user_task(task_id, user_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404

    try:
        subtasks = db.session.query(Subtask).filter_by(task_id=task_id).order_by(Subtask.created_at.asc()).all()

        return jsonify({
            'success': True,
            'subtasks': [{
                'id': st.id,
                'title': st.title,
                'description': st.description,
                'completed': bool(st.completed),
                'created_at': st.created_at.isoformat() if st.created_at else None,
                'updated_at': st.updated_at.isoformat() if st.updated_at else None
            } for st in subtasks]
        }), 200

    except Exception:
        logger.exception("get_subtasks_failed", extra={"task_id": task_id, "user_id": user_id})
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@tasks_bp.route('/subtasks/<int:subtask_id>', methods=['PUT'])
@jwt_required()
def update_subtask(subtask_id):
    """Update a subtask"""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    subtask, task, project = get_user_subtask(subtask_id, user_id)
    if not subtask:
        return jsonify({'success': False, 'error': 'Subtask not found'}), 404

    try:
        title_changed = False
        description_changed = False

        if 'title' in data:
            title = str(data['title']).strip()
            if not title:
                return jsonify({'success': False, 'error': 'Subtask title cannot be empty'}), 400
            if len(title) > MAX_TITLE_LENGTH:
                return jsonify({'success': False, 'error': f'Title exceeds maximum length of {MAX_TITLE_LENGTH}'}), 400
            subtask.title = title
            title_changed = True

        if 'description' in data:
            desc = str(data['description']).strip() if data['description'] is not None else ''
            if len(desc) > MAX_DESCRIPTION_LENGTH:
                return jsonify({'success': False, 'error': f'Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH}'}), 400
            subtask.description = desc
            description_changed = True

        if 'completed' in data:
            subtask.completed = 1 if data['completed'] else 0

        if title_changed or description_changed:
            try:
                from utils.embedding_utils import get_subtask_embedding
                subtask.embedding = get_subtask_embedding(subtask)
            except Exception as e:
                logger.warning("subtask_embedding_update_failed", extra={"error": str(e)})

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Subtask updated successfully',
            'subtask': {
                'id': subtask.id,
                'title': subtask.title,
                'description': subtask.description,
                'completed': bool(subtask.completed),
                'created_at': subtask.created_at.isoformat() if subtask.created_at else None,
                'updated_at': subtask.updated_at.isoformat() if subtask.updated_at else None
            }
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("update_subtask_failed", extra={"subtask_id": subtask_id, "user_id": user_id})
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@tasks_bp.route('/subtasks/<int:subtask_id>', methods=['DELETE'])
@jwt_required()
def delete_subtask(subtask_id):
    """Delete a subtask"""
    user_id = int(get_jwt_identity())
    subtask, task, project = get_user_subtask(subtask_id, user_id)
    if not subtask:
        return jsonify({'success': False, 'error': 'Subtask not found'}), 404

    try:
        db.session.delete(subtask)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Subtask deleted successfully'
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("delete_subtask_failed", extra={"subtask_id": subtask_id, "user_id": user_id})
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
