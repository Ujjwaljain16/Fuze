"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask_jwt_extended import JWTManager
from typing import Any, Optional
from dotenv import load_dotenv

import time
import threading

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

def pytest_sessionstart(session):
    session._start_time = time.perf_counter()
    print(f"\n[TIMING HOOK] pytest_sessionstart at {time.strftime('%H:%M:%S')}")

def pytest_sessionfinish(session, exitstatus):
    start_finish = time.perf_counter()
    print(f"\n[TIMING HOOK] pytest_sessionfinish starting at {time.strftime('%H:%M:%S')}...")
    active_threads = [t for t in threading.enumerate() if t != threading.main_thread()]
    print(f"[THREAD DUMP] {len(active_threads)} active non-main thread(s) at sessionfinish:")
    for t in active_threads:
        print(f"  - Thread name='{t.name}', daemon={t.daemon}, is_alive={t.is_alive()}, id={t.ident}")
    elapsed = time.perf_counter() - start_finish
    print(f"[TIMING HOOK] pytest_sessionfinish completed in {elapsed:.4f}s")

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
    os.environ['BCRYPT_LOG_ROUNDS'] = '4'
    os.environ['DATABASE_URL'] = test_db_url
    os.environ['TESTING'] = 'true'  # Additional flag to indicate testing
    
    from run_production import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['BCRYPT_LOG_ROUNDS'] = 4
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # No expiration for tests
    flask_app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disable CSRF for tests
    flask_app.config['JWT_COOKIE_SECURE'] = False  # Allow cookies in test environment
    flask_app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']  # Allow tokens in both headers and cookies
    
    # Explicitly set database URI for SQLite (SQLite doesn't support pool parameters)
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = test_db_url
    # Remove pool parameters for SQLite
    if 'sqlite' in test_db_url.lower():
        flask_app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': False,
            'connect_args': {'check_same_thread': False}
        }
    
    # Disable rate limiting in tests to prevent 429 cascades
    flask_app.config['RATELIMIT_ENABLED'] = False
    flask_app.limiter = None
    
    with flask_app.app_context():
        from models import db
        
        # CRITICAL: Verify we're using test database before any operations
        current_db_url = flask_app.config.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL', '')
        
        if not current_db_url or 'sqlite' not in current_db_url.lower():
            test_db_url = 'sqlite:///:memory:'
            os.environ['DATABASE_URL'] = test_db_url
            flask_app.config['SQLALCHEMY_DATABASE_URI'] = test_db_url
            db.init_app(flask_app)
        
        db.create_all()
        yield flask_app
        t_app_0 = time.perf_counter()
        print(f"\n[TIMING HOOK] Session fixture 'app' teardown started at {time.strftime('%H:%M:%S')}...")
        try:
            db.drop_all()
        except Exception:
            pass
        t_app_1 = time.perf_counter()
        print(f"[TIMING HOOK] Session fixture 'app' teardown completed in {t_app_1 - t_app_0:.4f}s")

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def jwt_headers(app, test_user):
    """Fast in-memory JWT minting for non-auth tests (< 0.1ms)."""
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(test_user['id']))
        return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def auth_headers(jwt_headers):
    """Fast default auth_headers fixture delegating to direct JWT generation."""
    return jwt_headers

@pytest.fixture
def login_headers(client, test_user):
    """Full HTTP login flow for tests explicitly testing the auth endpoint."""
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    if response.status_code != 200:
        pytest.fail(f"Login failed in login_headers fixture: {response.status_code} - {response.json}")
    token = response.json.get('access_token')
    if not token:
        pytest.fail(f"No access token in login response: {response.json}")
    return {'Authorization': f'Bearer {token}'}

class FakeRedisCache:
    """In-memory Redis cache stub for fast, socketless testing."""
    def __init__(self):
        self.connected = True
        self.store = {}
        self.redis_client = MagicMock()
        # Return mock for keys / exists / set calls
        self.redis_client.keys.return_value = []
        self.redis_client.exists.return_value = False
        self.redis_client.set.return_value = True
        self.redis_client.delete.return_value = True

    def get_cache(self, key: str):
        return self.store.get(key)

    def set_cache(self, key: str, data: Any, ttl: int = 3600):
        self.store[key] = data
        return True

    def delete_cache(self, key: str):
        self.store.pop(key, None)
        return True

    def cache_query_result(self, key: str, data: Any, ttl: int = 3600):
        return self.set_cache(key, data, ttl=ttl)

    def invalidate_user_bookmarks(self, user_id: int):
        return self.invalidate_query_cache(f"bookmarks:{user_id}:*")

    def invalidate_query_cache(self, pattern: str):
        import fnmatch
        to_delete = [k for k in self.store.keys() if fnmatch.fnmatch(k, pattern)]
        for k in to_delete:
            self.store.pop(k, None)
        return len(to_delete)

    def invalidate_recommendation_cache(self, user_id: Optional[int] = None):
        if user_id:
            return self.invalidate_query_cache(f"recommendations:{user_id}:*")
        return self.invalidate_query_cache("recommendations:*")

    def get_cache_stats(self):
        return {"connected": True, "keyspace_hits": 0, "keyspace_misses": 0}

@pytest.fixture(autouse=True)
def patch_redis_for_tests(monkeypatch):
    """
    Preserve real RedisCache.__init__ logic while overriding only _try_connect.
    Mutates the existing redis_cache singleton instance in-place so all modules
    holding 'from utils.redis_utils import redis_cache' references use the fake.
    """
    from utils.redis_utils import RedisCache, redis_cache
    fake = FakeRedisCache()

    def fake_try_connect(self):
        self.redis_client = fake.redis_client
        self.connected = True
        return True

    # 1. Class-level patch for any new RedisCache() instantiations
    monkeypatch.setattr(RedisCache, "_try_connect", fake_try_connect)
    
    # 2. In-place attribute mutation on the existing singleton instance object
    monkeypatch.setattr(redis_cache, "redis_client", fake.redis_client)
    monkeypatch.setattr(redis_cache, "connected", True)
    return fake

@pytest.fixture
def mock_external_network_services(monkeypatch):
    """Optional fixture to mock external web scrapers and embedding APIs in unit tests."""
    mock_scrape = MagicMock(return_value={
        'title': 'Test Article',
        'content': 'Test content',
        'headings': ['Heading 1'],
        'meta_description': 'Test description',
        'quality_score': 8
    })
    mock_embed = MagicMock(return_value=[0.1] * 384)
    try:
        monkeypatch.setattr('blueprints.bookmarks.scrape_url_enhanced', mock_scrape)
        monkeypatch.setattr('blueprints.bookmarks.get_embedding', mock_embed)
        monkeypatch.setattr('scrapers.scrapling_enhanced_scraper.scrape_url_enhanced', mock_scrape)
        monkeypatch.setattr('utils.embedding_utils.get_embedding', mock_embed)
    except Exception:
        pass
    return mock_scrape, mock_embed

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

