"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

# Test database URL (use in-memory SQLite for fast tests)
TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')

@pytest.fixture(scope='session')
def app():
    """Create Flask app for testing"""
    from run_production import create_app
    
    # Override database URL for testing
    os.environ['DATABASE_URL'] = TEST_DATABASE_URL
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['JWT_SECRET_KEY'] = 'test-secret-key'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # No expiration for tests
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disable CSRF for tests
    app.config['JWT_COOKIE_SECURE'] = False  # Allow cookies in test environment
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']  # Allow tokens in both headers and cookies
    
    # Explicitly set database URI for SQLite (SQLite doesn't support pool parameters)
    app.config['SQLALCHEMY_DATABASE_URI'] = TEST_DATABASE_URL
    # Remove pool parameters for SQLite
    if 'sqlite' in TEST_DATABASE_URL.lower():
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': False,
            'connect_args': {'check_same_thread': False}
        }
    
    # Disable rate limiting in tests
    app.limiter = None
    
    with app.app_context():
        from models import db
        db.create_all()
        yield app
        try:
            db.drop_all()
        except Exception as e:
            # Ignore teardown errors (like database timeouts) - tests already passed
            pass

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    # Handle rate limiting or other errors
    if response.status_code != 200:
        pytest.fail(f"Login failed in auth_headers fixture: {response.status_code} - {response.json}")
    token = response.json.get('access_token')
    if not token:
        pytest.fail(f"No access token in login response: {response.json}")
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def test_user(app):
    """Create a test user"""
    from models import db, User
    from werkzeug.security import generate_password_hash
    import uuid
    
    with app.app_context():
        # Use unique username/email to avoid conflicts
        unique_id = str(uuid.uuid4())[:8]
        username = f'testuser_{unique_id}'
        email = f'test_{unique_id}@example.com'
        
        # Check if user already exists and delete if so
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash('testpass123')
        )
        db.session.add(user)
        db.session.commit()
        
        yield {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'password': 'testpass123'
        }
        
        # Cleanup
        try:
            db.session.delete(user)
            db.session.commit()
        except:
            db.session.rollback()

@pytest.fixture
def mock_redis():
    """Mock Redis for testing"""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    return mock_redis

@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing"""
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1] * 384]  # Mock embedding vector
    return mock_model

@pytest.fixture
def mock_gemini():
    """Mock Gemini API for testing"""
    with patch('utils.gemini_utils.GeminiAnalyzer') as mock:
        mock_instance = MagicMock()
        mock_instance.analyze_text.return_value = {
            'summary': 'Test summary',
            'key_concepts': ['concept1', 'concept2'],
            'difficulty': 'intermediate'
        }
        mock.return_value = mock_instance
        yield mock_instance

