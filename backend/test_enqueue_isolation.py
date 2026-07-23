import os
import sys
import unittest
from unittest.mock import patch
import json

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from run_production import create_app
from models import db, User

class TestEnqueueIsolation(unittest.TestCase):
    def setUp(self):
        os.environ['FUZE_ENV'] = 'testing'
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            from werkzeug.security import generate_password_hash
            self.test_user = User(
                email="test_enqueue@example.com",
                username="test_enqueue",
                password_hash=generate_password_hash("password123")
            )
            db.session.add(self.test_user)
            db.session.commit()
            
            response = self.client.post('/api/auth/login', json={
                'email': 'test_enqueue@example.com',
                'password': 'password123'
            })
            self.token = response.json['access_token']
            self.headers = {'Authorization': f'Bearer {self.token}'}

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('services.task_queue.enqueue_project_ml_job')
    def test_project_creation_succeeds_when_enqueue_fails(self, mock_enqueue):
        mock_enqueue.side_effect = Exception("Mock enqueue failure")
        
        with self.app.app_context():
            response = self.client.post('/api/projects', json={
                'title': 'Test Enqueue Isolation Project',
                'description': 'This should succeed even though the enqueue fails.',
                'technologies': 'Python'
            }, headers=self.headers)
            
            # The transaction should succeed!
            self.assertEqual(response.status_code, 201)
            self.assertIn('project_id', response.json)
            
            # Verify the mock was actually called via the event bus
            mock_enqueue.assert_called_once()
            print("SUCCESS: Event bus triggered handler, enqueue failed, but request succeeded with 201 Created!")

if __name__ == '__main__':
    unittest.main()
