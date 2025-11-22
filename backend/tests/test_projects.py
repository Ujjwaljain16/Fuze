"""
Unit tests for projects blueprint
"""
import pytest

@pytest.mark.unit
@pytest.mark.requires_db
class TestProjects:
    """Test project endpoints"""
    
    def test_create_project(self, client, auth_headers):
        """Test creating a project"""
        response = client.post('/api/projects', json={
            'title': 'Test Project',
            'description': 'Test description',
            'technologies': 'Python, Flask'
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json
        assert 'project' in data
        assert data['project']['title'] == 'Test Project'
    
    def test_list_projects(self, client, auth_headers, test_user, app):
        """Test listing projects"""
        from models import db, Project
        
        with app.app_context():
            # Create test projects
            for i in range(3):
                project = Project(
                    user_id=test_user['id'],
                    title=f'Project {i}',
                    description=f'Description {i}'
                )
                db.session.add(project)
            db.session.commit()
        
        response = client.get('/api/projects', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'projects' in data
        assert len(data['projects']) == 3
    
    def test_get_project_detail(self, client, auth_headers, test_user, app):
        """Test getting project details"""
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
        
        response = client.get(f'/api/projects/{project_id}', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        # The endpoint returns a flat dict, not wrapped in 'project'
        assert data['title'] == 'Test Project'
    
    def test_update_project(self, client, auth_headers, test_user, app):
        """Test updating a project"""
        from models import db, Project
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='Original Title',
                description='Original description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
        
        response = client.put(f'/api/projects/{project_id}', json={
            'title': 'Updated Title',
            'description': 'Updated description'
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json
        assert data['project']['title'] == 'Updated Title'
    
    def test_delete_project(self, client, auth_headers, test_user, app):
        """Test deleting a project"""
        from models import db, Project
        
        with app.app_context():
            project = Project(
                user_id=test_user['id'],
                title='To Delete',
                description='Description'
            )
            db.session.add(project)
            db.session.commit()
            project_id = project.id
        
        response = client.delete(f'/api/projects/{project_id}', headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deleted
        with app.app_context():
            deleted = Project.query.get(project_id)
            assert deleted is None

