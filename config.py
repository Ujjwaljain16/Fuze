import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Suppresses a warning; good practice to set to False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Environment detection
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # HTTPS and Security Settings
    HTTPS_ENABLED = os.environ.get('HTTPS_ENABLED', 'False').lower() == 'true'
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', 'False').lower() == 'true'
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = 15  # minutes
    JWT_REFRESH_TOKEN_EXPIRES = 14  # days
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = HTTPS_ENABLED  # Only send cookies over HTTPS
    JWT_COOKIE_SAMESITE = 'Strict'
    JWT_COOKIE_CSRF_PROTECT = CSRF_ENABLED
    JWT_CSRF_IN_COOKIES = CSRF_ENABLED
    JWT_CSRF_CHECK_FORM = CSRF_ENABLED
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = HTTPS_ENABLED
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

class DevelopmentConfig(Config):
    DEBUG = True
    HTTPS_ENABLED = False
    CSRF_ENABLED = False
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False

class ProductionConfig(Config):
    DEBUG = False
    HTTPS_ENABLED = True
    CSRF_ENABLED = True
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True 