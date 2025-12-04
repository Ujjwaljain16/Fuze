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
    # CRITICAL: Save original DATABASE_URL to restore later
    original_db_url = os.environ.get('DATABASE_URL', '')
    
    # CRITICAL SAFETY CHECK: Prevent tests from using production database
    production_db_url = original_db_url
    test_db_url = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
    
    # ALWAYS use in-memory SQLite for tests unless explicitly overridden
    # This ensures tests NEVER touch production database
    if not test_db_url or test_db_url == original_db_url:
        test_db_url = 'sqlite:///:memory:'
    
    if production_db_url:
        # Check for production database indicators
        production_indicators = ['supabase.co', 'amazonaws.com', 'azure.com', 'gcp.com', 'heroku.com', 'postgresql://', 'postgres://']
        is_production = any(indicator in production_db_url.lower() for indicator in production_indicators)
        
        if is_production and 'sqlite' not in production_db_url.lower():
            # This looks like a production database!
            # Force test database to prevent accidental data loss
            print("\n" + "="*70)
            print("⚠️  WARNING: Production database detected in DATABASE_URL!")
            print(f"   Found: {production_db_url[:50]}...")
            print("   Forcing in-memory SQLite test database to prevent data loss.")
            print("="*70 + "\n")
            test_db_url = 'sqlite:///:memory:'
    
    # CRITICAL: Override database URL BEFORE importing create_app
    # This ensures create_app() and all its imports use the test database
    os.environ['DATABASE_URL'] = test_db_url
    os.environ['TESTING'] = 'true'  # Additional flag to indicate testing
    
    from run_production import create_app
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
    app.config['SQLALCHEMY_DATABASE_URI'] = test_db_url
    # Remove pool parameters for SQLite
    if 'sqlite' in test_db_url.lower():
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': False,
            'connect_args': {'check_same_thread': False}
        }
    
    # Disable rate limiting in tests
    app.limiter = None
    
    with app.app_context():
        from models import db
        
        # CRITICAL: Verify we're using test database before any operations
        current_db_url = app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL', '')
        
        # Must be SQLite in-memory database for tests
        if not current_db_url or 'sqlite' not in current_db_url.lower():
            # Check for production indicators
            production_indicators = ['supabase.co', 'amazonaws.com', 'azure.com', 'gcp.com', 'heroku.com', 'postgresql://', 'postgres://']
            is_production = any(indicator in current_db_url.lower() for indicator in production_indicators) if current_db_url else False
            
            if is_production or not current_db_url:
                # Force in-memory SQLite
                print("\n" + "="*70)
                print("⚠️  CRITICAL: Forcing in-memory SQLite database for tests!")
                if current_db_url:
                    print(f"   Detected: {current_db_url[:100]}...")
                else:
                    print("   No database URL set - using in-memory SQLite")
                print("="*70 + "\n")
                
                # Force SQLite in-memory
                test_db_url = 'sqlite:///:memory:'
                os.environ['DATABASE_URL'] = test_db_url
                app.config['SQLALCHEMY_DATABASE_URI'] = test_db_url
                # Re-initialize database connection
                db.init_app(app)
        
        db.create_all()
        yield app
        try:
            # Double-check before dropping
            final_db_url = app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL', '')
            if final_db_url and 'sqlite' not in final_db_url.lower():
                production_indicators = ['supabase.co', 'amazonaws.com', 'azure.com', 'gcp.com', 'heroku.com']
                is_production = any(indicator in final_db_url.lower() for indicator in production_indicators)
                if is_production:
                    print("\n" + "="*70)
                    print("⚠️  CRITICAL: Refusing to drop production database!")
                    print("   Skipping db.drop_all() to prevent data loss.")
                    print("="*70 + "\n")
                    return  # Don't drop production database!
            
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
    from blueprints.auth import hash_password
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
            password_hash=hash_password('testpass123')
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

