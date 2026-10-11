"""
Unit tests for recommendations blueprint
"""
import pytest
from unittest.mock import patch

@pytest.mark.unit
@pytest.mark.requires_db
class TestRecommendations:
    """Test recommendation endpoints"""
    
    def test_get_recommendations_success(self, client, auth_headers, test_user, app):
        """Test getting recommendations successfully"""
        from models import db, SavedContent
        
        with app.app_context():
            # Create some saved content for recommendations
            for i in range(5):
                bookmark = SavedContent(
                    user_id=test_user['id'],
                    url=f'https://example.com/{i}',
                    title=f'Content {i}',
                    extracted_text=f'Content about topic {i}',
                    quality_score=8
                )
                db.session.add(bookmark)
            db.session.commit()
        
        fake = {"results": [
            {"id": 1, "title": "Rec 1", "url": "https://example.com/1", "score": 90.0, "confidence": 90.0,
             "reason": "Matches what you're working on", "basic_summary": "Summary 1", "content_type": "tutorial",
             "difficulty": "intermediate", "technologies": ["Python"], "key_concepts": ["concept1"],
             "quality_score": 8, "engine_used": "intent_engine", "metadata": {}},
        ], "intent": {"intent_source": "context"}, "cached": False}
        with patch('ml.intent_engine.engine.recommend', return_value=fake) as rec:
            response = client.post('/api/recommendations/unified-orchestrator',
                                 json={
                                     'title': 'Test Project',
                                     'technologies': 'Python, Flask',
                                     'description': 'Test description'
                                 },
                                 headers=auth_headers)

            assert response.status_code == 200
            data = response.json
            assert data['recommendations'][0]['id'] == 1
            assert data['engine_used'] == 'intent_engine'
            # without a project/task, the request text is the query
            assert rec.call_args.kwargs['query'] == 'Test Project. Test description. Python, Flask'

    def test_get_recommendations_no_content(self, client, auth_headers):
        """Test getting recommendations with no saved content"""
        response = client.post('/api/recommendations/unified-orchestrator',
                             json={
                                 'title': 'Test Project',
                                 'technologies': 'Python'
                             },
                             headers=auth_headers)
        
        # Should still return 200, but with empty or limited recommendations
        assert response.status_code in [200, 404]
    
    def test_get_engine_status(self, client):
        """Test getting engine status"""
        response = client.get('/api/recommendations/status')
        assert response.status_code == 200
        data = response.json
        assert 'unified_orchestrator_available' in data
        assert 'total_engines_available' in data



def test_task_and_subtask_context_reach_the_engine(client, auth_headers):
    fake = {"results": [], "intent": {}, "cached": False}
    with patch('ml.intent_engine.engine.recommend', return_value=fake) as rec:
        resp = client.post('/api/recommendations/unified-orchestrator', json={
            'title': 'Auth', 'description': 'add login', 'project_id': '7', 'task_id': 12, 'subtask_id': 'bad'
        }, headers=auth_headers)
    assert resp.status_code == 200
    kw = rec.call_args.kwargs
    assert (kw['project_id'], kw['task_id'], kw['subtask_id']) == (7, 12, None)
    # with a project/task, the stored context is the intent, not the echoed request text
    assert kw['query'] == ''


def test_task_route_404_for_missing_task(client, auth_headers):
    resp = client.post('/api/recommendations/task/999999', json={}, headers=auth_headers)
    assert resp.status_code == 404


def test_task_route_404_for_other_users_task(client, app, auth_headers):
    """A real task owned by someone else must look exactly like a missing one."""
    import uuid
    from models import db, User, Project, Task
    from blueprints.auth import hash_password
    with app.app_context():
        tag = uuid.uuid4().hex[:8]
        owner = User(username=f'owner_{tag}', email=f'owner_{tag}@example.com', password_hash=hash_password('pw123456'))
        db.session.add(owner)
        db.session.flush()
        project = Project(user_id=owner.id, title='Their project')
        db.session.add(project)
        db.session.flush()
        task = Task(project_id=project.id, title='Their secret task')
        db.session.add(task)
        db.session.commit()
        owner_id, task_id = owner.id, task.id

    try:
        with patch('ml.intent_engine.engine.recommend') as rec:
            resp = client.post(f'/api/recommendations/task/{task_id}', json={}, headers=auth_headers)
        assert resp.status_code == 404
        assert 'Their secret task' not in resp.get_data(as_text=True)
        rec.assert_not_called()
    finally:
        with app.app_context():
            db.session.delete(db.session.get(User, owner_id))
            db.session.commit()
