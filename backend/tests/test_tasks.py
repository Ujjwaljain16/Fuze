"""
Unit tests for tasks blueprint
"""
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.unit
@pytest.mark.requires_db
class TestTasks:
    """Test task endpoints"""
    
    def test_create_task(self, client, auth_headers, test_user, app):
        """Test creating a task"""
        from models import db, Project
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='Test Project',
                description='Test description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
        
        response = client.post('/api/tasks', json={
            'project_id': project_id,
            'title': 'Test Task',
            'description': 'Test task description'
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json
        assert 'task' in data or 'id' in data
        if 'task' in data:
            assert data['task']['title'] == 'Test Task'
    
    def test_create_task_invalid_project(self, client, auth_headers):
        """Test creating a task with invalid project"""
        response = client.post('/api/tasks', json={
            'project_id': 99999,
            'title': 'Test Task'
        }, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_list_tasks(self, client, auth_headers, test_user, app):
        """Test listing tasks for a project"""
        from models import db, Project, Task
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='Test Project',
                description='Test description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
            
            # Create tasks
            for i in range(3):
                task = Task(
                    project_id=project_id,
                    title=f'Task {i}',
                    description=f'Description {i}'
                )
                db.session.add(task)
            db.session.commit()
        
        response = client.get(f'/api/tasks/project/{project_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'tasks' in data
        assert len(data['tasks']) == 3
    
    def test_update_task(self, client, auth_headers, test_user, app):
        """Test updating a task"""
        from models import db, Project, Task
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='Test Project',
                description='Test description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
            
            task = Task(
                project_id=project_id,
                title='Original Task',
                description='Original description'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        response = client.put(f'/api/tasks/{task_id}', json={
            'title': 'Updated Task',
            'description': 'Updated description'
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json
        assert data.get('success') == True or 'task' in data
    
    def test_delete_task(self, client, auth_headers, test_user, app):
        """Test deleting a task"""
        from models import db, Project, Task
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='Test Project',
                description='Test description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
            
            task = Task(
                project_id=project_id,
                title='To Delete',
                description='Description'
            )
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        
        response = client.delete(f'/api/tasks/{task_id}', headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deleted
        with app.app_context():
            deleted = Task.query.get(task_id)
            assert deleted is None
    
    def test_ai_breakdown(self, client, auth_headers, test_user, app):
        """Test AI task breakdown"""
        from models import db, Project
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='Test Project',
                description='Test description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
        
        with patch('blueprints.tasks.get_gemini_response') as mock_gemini:
            mock_gemini.return_value = {
                'response': '{"tasks": [{"title": "Task 1", "description": "Desc 1"}, {"title": "Task 2", "description": "Desc 2"}]}'
            }
            
            response = client.post('/api/tasks/ai-breakdown', json={
                'project_id': project_id,
                'description': 'Build a web app'
            }, headers=auth_headers)
            
            assert response.status_code == 201
            data = response.json
            assert data.get('success') == True
            assert 'tasks' in data

