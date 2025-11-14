"""
Configuration module for Fuze
Now uses UnifiedConfig as single source of truth - NO hardcoded values!
"""

from unified_config import get_config

# Get unified configuration instance
unified_config = get_config()

# Create Config class for Flask compatibility
class Config:
    """Flask configuration - now powered by UnifiedConfig"""
    
    # Get all Flask-specific config from unified config
    _flask_config = unified_config.get_flask_config()
    
    # Apply Flask config - all values come from unified_config (environment variables or defaults)
    SECRET_KEY = _flask_config['SECRET_KEY']
    JWT_SECRET_KEY = _flask_config['JWT_SECRET_KEY']
    JWT_ACCESS_TOKEN_EXPIRES = _flask_config['JWT_ACCESS_TOKEN_EXPIRES']
    JWT_REFRESH_TOKEN_EXPIRES = _flask_config['JWT_REFRESH_TOKEN_EXPIRES']
    
    SQLALCHEMY_DATABASE_URI = _flask_config['SQLALCHEMY_DATABASE_URI']
    SQLALCHEMY_TRACK_MODIFICATIONS = _flask_config['SQLALCHEMY_TRACK_MODIFICATIONS']
    SQLALCHEMY_ENGINE_OPTIONS = _flask_config['SQLALCHEMY_ENGINE_OPTIONS']
    
    CORS_ORIGINS = _flask_config['CORS_ORIGINS']
    
    # Redis URL
    REDIS_URL = unified_config.get_redis_url()
    
    # Gemini API
    GEMINI_API_KEY = unified_config.ai.gemini_api_key

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = unified_config.debug and unified_config.is_development()

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Production settings are already handled in unified_config

# Select config based on environment
config = ProductionConfig if unified_config.is_production() else DevelopmentConfig

# Export unified config for direct access if needed
__all__ = ['Config', 'DevelopmentConfig', 'ProductionConfig', 'config', 'unified_config']
