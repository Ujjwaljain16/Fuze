from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Task, Project, User, SavedContent, Subtask
from utils.gemini_utils import get_gemini_response
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

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
        # Generate embedding for task BEFORE committing
        try:
            from utils.embedding_utils import get_task_embedding
            new_task.embedding = get_task_embedding(new_task)
            if new_task.embedding is not None:
                # Check if it's not a zero vector (fallback case)
                try:
                    import numpy as np
                    is_zero_vector = isinstance(new_task.embedding, np.ndarray) and np.all(new_task.embedding == 0)
                except:
                    # Fallback check for list/array
                    is_zero_vector = isinstance(new_task.embedding, (list, tuple)) and all(x == 0.0 for x in new_task.embedding)

                if not is_zero_vector:
                    logger.info(f"Generated embedding for task: {title}")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for task: {e}")
            # Continue without embedding - it can be generated later

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
        'created_at': t.created_at.isoformat(),
        'subtasks': [{
            'id': st.id,
            'title': st.title,
            'description': st.description,
            'completed': bool(st.completed),
            'created_at': st.created_at.isoformat(),
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
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        project_id = data.get('project_id')
        project_description = data.get('project_description', '')
        skill_level = data.get('skill_level', 'intermediate')  # beginner, intermediate, advanced
        
        if not project_id:
            return jsonify({'success': False, 'error': 'project_id is required'}), 400
        
        # Verify project ownership
        project = Project.query.get(project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Project not found or unauthorized'}), 404
        
        # Get user's relevant bookmarks for context
        user_bookmarks = SavedContent.query.filter_by(user_id=user_id).limit(20).all()
        bookmark_technologies = set()
        for bm in user_bookmarks:
            if bm.tags:
                bookmark_technologies.update(bm.tags.lower().split(','))
        
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
        
        logger.info(f"Requesting Gemini task breakdown for project {project_id}")
        
        # Call Gemini
        user_id = int(get_jwt_identity())
        response = get_gemini_response(prompt, user_id=user_id)
        
        if not response:
            return jsonify({
                'success': False,
                'error': 'Failed to generate task breakdown',
                'details': 'No response from AI'
            }), 500
        
        # Parse response
        try:
            ai_response = response.strip() if isinstance(response, str) else str(response).strip()
            # Remove markdown code blocks if present
            if '```json' in ai_response:
                ai_response = ai_response.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_response:
                ai_response = ai_response.split('```')[1].split('```')[0].strip()
            
            tasks_data = json.loads(ai_response)
            
            if not isinstance(tasks_data, list):
                raise ValueError("Response is not a list of tasks")
            
            # Create tasks in database
            created_tasks = []
            for task_data in tasks_data:
                new_task = Task(
                    project_id=project_id,
                    title=task_data.get('title', 'Untitled Task'),
                    description=json.dumps({
                        'description': task_data.get('description', ''),
                        'estimated_time': task_data.get('estimated_time', ''),
                        'difficulty': task_data.get('difficulty', skill_level),
                        'prerequisites': task_data.get('prerequisites', []),
                        'key_technologies': task_data.get('key_technologies', []),
                        'success_criteria': task_data.get('success_criteria', '')
                    })
                )
                db.session.add(new_task)
                created_tasks.append({
                    'title': new_task.title,
                    'description': task_data.get('description', ''),
                    'estimated_time': task_data.get('estimated_time', ''),
                    'difficulty': task_data.get('difficulty', ''),
                    'prerequisites': task_data.get('prerequisites', []),
                    'key_technologies': task_data.get('key_technologies', []),
                    'success_criteria': task_data.get('success_criteria', '')
                })
            
            db.session.commit()
            
            logger.info(f"Created {len(created_tasks)} AI-generated tasks for project {project_id}")
            
            return jsonify({
                'success': True,
                'message': f'Generated {len(created_tasks)} tasks successfully',
                'tasks': created_tasks,
                'ai_powered': True
            }), 201
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Response was: {response.get('response', '')[:200]}")
            return jsonify({
                'success': False,
                'error': 'Failed to parse AI response',
                'details': str(e)
            }), 500
        except Exception as e:
            logger.error(f"Error processing AI task breakdown: {e}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'Error processing task breakdown',
                'details': str(e)
            }), 500
    
    except Exception as e:
        logger.error(f"AI task breakdown error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@tasks_bp.route('/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """Update a task"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # Verify ownership through project
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Update fields
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']

        # Regenerate embedding for updated task
        try:
            from utils.embedding_utils import get_task_embedding
            task.embedding = get_task_embedding(task)
            if task.embedding is not None:
                # Check if it's not a zero vector (fallback case)
                try:
                    import numpy as np
                    is_zero_vector = isinstance(task.embedding, np.ndarray) and np.all(task.embedding == 0)
                except:
                    # Fallback check for list/array
                    is_zero_vector = isinstance(task.embedding, (list, tuple)) and all(x == 0.0 for x in task.embedding)

                if not is_zero_vector:
                    logger.info(f"Updated embedding for task: {task.title}")
        except Exception as e:
            logger.warning(f"Failed to update embedding for task: {e}")

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task updated successfully',
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description
            }
        })
    
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@tasks_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """Delete a task"""
    try:
        user_id = int(get_jwt_identity())
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # Verify ownership through project
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# SUBTASK ENDPOINTS
# ============================================================================

@tasks_bp.route('/<int:task_id>/subtasks', methods=['POST'])
@jwt_required()
def create_subtask(task_id):
    """Create a new subtask for a task"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # Verify ownership through project
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'success': False, 'error': 'Subtask title is required'}), 400
        
        description = data.get('description', '').strip() if data.get('description') else ''
        
        new_subtask = Subtask(
            task_id=task_id,
            title=title,
            description=description,
            completed=0
        )
        
        # Generate embedding for subtask for better semantic matching
        try:
            from utils.embedding_utils import get_subtask_embedding
            new_subtask.embedding = get_subtask_embedding(new_subtask)
            if new_subtask.embedding is not None:
                # Check if it's not a zero vector (fallback case)
                try:
                    import numpy as np
                    is_zero_vector = isinstance(new_subtask.embedding, np.ndarray) and np.all(new_subtask.embedding == 0)
                except:
                    # Fallback check for list/array
                    is_zero_vector = isinstance(new_subtask.embedding, (list, tuple)) and all(x == 0.0 for x in new_subtask.embedding)

                if not is_zero_vector:
                    logger.info(f"Generated embedding for subtask: {title}")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for subtask: {e}")
            # Continue without embedding - it can be generated later
        
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
                'created_at': new_subtask.created_at.isoformat(),
                'updated_at': new_subtask.updated_at.isoformat() if new_subtask.updated_at else None
            }
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating subtask: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@tasks_bp.route('/<int:task_id>/subtasks', methods=['GET'])
@jwt_required()
def get_subtasks(task_id):
    """Get all subtasks for a task"""
    try:
        user_id = int(get_jwt_identity())
        
        task = Task.query.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        # Verify ownership through project
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        subtasks = Subtask.query.filter_by(task_id=task_id).order_by(Subtask.created_at).all()
        
        return jsonify({
            'success': True,
            'subtasks': [{
                'id': st.id,
                'title': st.title,
                'description': st.description,
                'completed': bool(st.completed),
                'created_at': st.created_at.isoformat(),
                'updated_at': st.updated_at.isoformat() if st.updated_at else None
            } for st in subtasks]
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching subtasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@tasks_bp.route('/subtasks/<int:subtask_id>', methods=['PUT'])
@jwt_required()
def update_subtask(subtask_id):
    """Update a subtask"""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        subtask = Subtask.query.get(subtask_id)
        if not subtask:
            return jsonify({'success': False, 'error': 'Subtask not found'}), 404
        
        # Verify ownership through task and project
        task = Task.query.get(subtask.task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Update fields
        title_changed = False
        description_changed = False
        
        if 'title' in data:
            subtask.title = data['title'].strip()
            title_changed = True
        if 'description' in data:
            subtask.description = data['description'].strip() if data['description'] else ''
            description_changed = True
        if 'completed' in data:
            subtask.completed = 1 if data['completed'] else 0
        
        # Regenerate embedding if title or description changed
        if title_changed or description_changed:
            try:
                from utils.embedding_utils import get_subtask_embedding
                subtask.embedding = get_subtask_embedding(subtask)
                if subtask.embedding is not None:
                    # Check if it's not a zero vector (fallback case)
                    try:
                        import numpy as np
                        is_zero_vector = isinstance(subtask.embedding, np.ndarray) and np.all(subtask.embedding == 0)
                    except:
                        # Fallback check for list/array
                        is_zero_vector = isinstance(subtask.embedding, (list, tuple)) and all(x == 0.0 for x in subtask.embedding)

                    if not is_zero_vector:
                        logger.info(f"Updated embedding for subtask: {subtask.title}")
            except Exception as e:
                logger.warning(f"Failed to update embedding for subtask: {e}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subtask updated successfully',
            'subtask': {
                'id': subtask.id,
                'title': subtask.title,
                'description': subtask.description,
                'completed': bool(subtask.completed),
                'created_at': subtask.created_at.isoformat(),
                'updated_at': subtask.updated_at.isoformat() if subtask.updated_at else None
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating subtask: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@tasks_bp.route('/subtasks/<int:subtask_id>', methods=['DELETE'])
@jwt_required()
def delete_subtask(subtask_id):
    """Delete a subtask"""
    try:
        user_id = int(get_jwt_identity())
        
        subtask = Subtask.query.get(subtask_id)
        if not subtask:
            return jsonify({'success': False, 'error': 'Subtask not found'}), 404
        
        # Verify ownership through task and project
        task = Task.query.get(subtask.task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        
        project = Project.query.get(task.project_id)
        if not project or project.user_id != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        db.session.delete(subtask)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subtask deleted successfully'
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting subtask: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
