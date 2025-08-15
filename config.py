import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-jwt-secret-key-here'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Enhanced database connection settings to fix SSL issues and timeouts
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,           # Keep moderate pool size
        'pool_timeout': 20,       # Reasonable timeout
        'pool_recycle': 300,      # Recycle connections every 5 minutes
        'pool_pre_ping': True,    # Enable pre-ping to detect dead connections
        'max_overflow': 10,       # Allow overflow connections
        'echo': False,            # Disable SQL echoing for production
        'connect_args': {
            'connect_timeout': 30,  # Increased connection timeout
            'sslmode': 'require',   # Require SSL for security
            'sslcert': None,        # No client certificate required
            'sslkey': None,         # No client key required
            'sslrootcert': None,    # No root certificate required
            'keepalives': 1,        # Enable keepalives
            'keepalives_idle': 30,  # Send keepalive after 30s idle
            'keepalives_interval': 10,  # Send keepalive every 10s
            'keepalives_count': 5,  # Retry keepalive 5 times
            'application_name': 'fuze_app',  # Identify application
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
        }
    }
    
    # CORS settings
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173'
    ]
    
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Gemini API
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 3,
        'pool_timeout': 15,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 5,
        'echo': True,  # Enable SQL echoing for development
        'connect_args': {
            'connect_timeout': 20,  # Increased connection timeout
            'sslmode': 'prefer',   # Prefer SSL but allow fallback in development
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'application_name': 'fuze_dev',
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
        }
    }

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 30,
        'pool_recycle': 600,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'echo': False,
        'connect_args': {
            'connect_timeout': 30,  # Increased connection timeout
            'sslmode': 'require',   # Require SSL in production
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'application_name': 'fuze_prod',
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000'
        }
    }

# Use development config by default
config = DevelopmentConfig
