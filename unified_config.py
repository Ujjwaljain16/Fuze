#!/usr/bin/env python3
"""
Unified Configuration System for Fuze
=====================================

Single source of truth for all configuration values.
NO hardcoded values in code - everything comes from here.
Supports environment variables, defaults, and runtime updates.

Author: Fuze AI System
Date: November 2024
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION DATA CLASSES
# ============================================================================

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', ''))
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '5')))
    max_overflow: int = field(default_factory=lambda: int(os.getenv('DB_MAX_OVERFLOW', '10')))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv('DB_POOL_TIMEOUT', '20')))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv('DB_POOL_RECYCLE', '300')))
    pool_pre_ping: bool = field(default_factory=lambda: os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true')
    echo: bool = field(default_factory=lambda: os.getenv('DB_ECHO', 'false').lower() == 'true')
    connect_timeout: int = field(default_factory=lambda: int(os.getenv('DB_CONNECT_TIMEOUT', '30')))
    ssl_mode: str = field(default_factory=lambda: os.getenv('DB_SSL_MODE', 'prefer'))

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    port: int = field(default_factory=lambda: int(os.getenv('REDIS_PORT', '6379')))
    db: int = field(default_factory=lambda: int(os.getenv('REDIS_DB', '0')))
    password: Optional[str] = field(default_factory=lambda: os.getenv('REDIS_PASSWORD'))
    default_ttl: int = field(default_factory=lambda: int(os.getenv('REDIS_DEFAULT_TTL', '3600')))
    max_connections: int = field(default_factory=lambda: int(os.getenv('REDIS_MAX_CONNECTIONS', '50')))

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = field(default_factory=lambda: os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'))
    jwt_secret_key: str = field(default_factory=lambda: os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-production'))
    jwt_access_token_expires_hours: int = field(default_factory=lambda: int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', '1')))
    jwt_refresh_token_expires_days: int = field(default_factory=lambda: int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES_DAYS', '30')))
    password_min_length: int = field(default_factory=lambda: int(os.getenv('PASSWORD_MIN_LENGTH', '8')))
    max_login_attempts: int = field(default_factory=lambda: int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')))

@dataclass
class MLConfig:
    """Machine Learning configuration"""
    # Model paths and names
    embedding_model: str = field(default_factory=lambda: os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'))
    spacy_model: str = field(default_factory=lambda: os.getenv('SPACY_MODEL', 'en_core_web_sm'))
    
    # ML parameters (adaptive, but these are initial values)
    learning_rate: float = field(default_factory=lambda: float(os.getenv('ML_LEARNING_RATE', '0.05')))
    decay_rate: float = field(default_factory=lambda: float(os.getenv('ML_DECAY_RATE', '0.95')))
    
    # Feature extraction
    tfidf_max_features: int = field(default_factory=lambda: int(os.getenv('TFIDF_MAX_FEATURES', '5000')))
    tfidf_ngram_min: int = field(default_factory=lambda: int(os.getenv('TFIDF_NGRAM_MIN', '1')))
    tfidf_ngram_max: int = field(default_factory=lambda: int(os.getenv('TFIDF_NGRAM_MAX', '3')))
    
    # BM25 parameters (will be adaptive)
    bm25_k1_initial: float = field(default_factory=lambda: float(os.getenv('BM25_K1_INITIAL', '1.5')))
    bm25_b_initial: float = field(default_factory=lambda: float(os.getenv('BM25_B_INITIAL', '0.75')))
    
    # Personalization
    interaction_weight_decay: float = field(default_factory=lambda: float(os.getenv('INTERACTION_WEIGHT_DECAY', '0.95')))
    min_interactions_for_personalization: int = field(default_factory=lambda: int(os.getenv('MIN_INTERACTIONS_FOR_PERSONALIZATION', '5')))

@dataclass
class RecommendationConfig:
    """Recommendation engine configuration"""
    # General settings
    max_recommendations_default: int = field(default_factory=lambda: int(os.getenv('MAX_RECOMMENDATIONS_DEFAULT', '10')))
    max_recommendations_limit: int = field(default_factory=lambda: int(os.getenv('MAX_RECOMMENDATIONS_LIMIT', '50')))
    
    # Quality thresholds (adaptive, these are minimums)
    min_quality_score: float = field(default_factory=lambda: float(os.getenv('MIN_QUALITY_SCORE', '0.0')))
    min_relevance_score: float = field(default_factory=lambda: float(os.getenv('MIN_RELEVANCE_SCORE', '0.1')))
    min_confidence_score: float = field(default_factory=lambda: float(os.getenv('MIN_CONFIDENCE_SCORE', '0.3')))
    
    # Diversity settings
    enable_diversity: bool = field(default_factory=lambda: os.getenv('ENABLE_DIVERSITY', 'true').lower() == 'true')
    diversity_threshold: float = field(default_factory=lambda: float(os.getenv('DIVERSITY_THRESHOLD', '0.7')))
    
    # Caching
    cache_recommendations: bool = field(default_factory=lambda: os.getenv('CACHE_RECOMMENDATIONS', 'true').lower() == 'true')
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('CACHE_TTL_SECONDS', '1800')))
    
    # Content retrieval limits
    max_content_items_to_process: int = field(default_factory=lambda: int(os.getenv('MAX_CONTENT_ITEMS_TO_PROCESS', '1000')))
    content_text_max_length: int = field(default_factory=lambda: int(os.getenv('CONTENT_TEXT_MAX_LENGTH', '2000')))

@dataclass
class AIConfig:
    """AI services configuration"""
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY'))
    gemini_model: str = field(default_factory=lambda: os.getenv('GEMINI_MODEL', 'gemini-pro'))
    gemini_temperature: float = field(default_factory=lambda: float(os.getenv('GEMINI_TEMPERATURE', '0.7')))
    gemini_max_tokens: int = field(default_factory=lambda: int(os.getenv('GEMINI_MAX_TOKENS', '1024')))
    gemini_timeout: int = field(default_factory=lambda: int(os.getenv('GEMINI_TIMEOUT', '30')))
    enable_gemini: bool = field(default_factory=lambda: os.getenv('ENABLE_GEMINI', 'true').lower() == 'true')

@dataclass
class CORSConfig:
    """CORS configuration"""
    origins: list = field(default_factory=lambda: [
        origin.strip() 
        for origin in os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173,chrome-extension://*').split(',')
        if origin.strip()
    ])
    supports_credentials: bool = field(default_factory=lambda: os.getenv('CORS_SUPPORTS_CREDENTIALS', 'true').lower() == 'true')
    max_age: int = field(default_factory=lambda: int(os.getenv('CORS_MAX_AGE', '86400')))

@dataclass
class PerformanceConfig:
    """Performance and optimization configuration"""
    enable_query_caching: bool = field(default_factory=lambda: os.getenv('ENABLE_QUERY_CACHING', 'true').lower() == 'true')
    enable_embedding_caching: bool = field(default_factory=lambda: os.getenv('ENABLE_EMBEDDING_CACHING', 'true').lower() == 'true')
    enable_parallel_processing: bool = field(default_factory=lambda: os.getenv('ENABLE_PARALLEL_PROCESSING', 'true').lower() == 'true')
    max_workers: int = field(default_factory=lambda: int(os.getenv('MAX_WORKERS', '4')))
    request_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('REQUEST_TIMEOUT_SECONDS', '30')))
    slow_query_threshold_ms: int = field(default_factory=lambda: int(os.getenv('SLOW_QUERY_THRESHOLD_MS', '1000')))

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    format: str = field(default_factory=lambda: os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_path: Optional[str] = field(default_factory=lambda: os.getenv('LOG_FILE_PATH'))
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv('LOG_MAX_FILE_SIZE_MB', '10')))
    backup_count: int = field(default_factory=lambda: int(os.getenv('LOG_BACKUP_COUNT', '5')))
    enable_console: bool = field(default_factory=lambda: os.getenv('LOG_ENABLE_CONSOLE', 'true').lower() == 'true')

# ============================================================================
# UNIFIED CONFIGURATION CLASS
# ============================================================================

class UnifiedConfig:
    """
    Unified configuration manager - single source of truth
    Supports environment variables, runtime updates, and configuration export/import
    """
    
    def __init__(self):
        # Initialize all configuration sections
        self.database = DatabaseConfig()
        self.redis = RedisConfig()
        self.security = SecurityConfig()
        self.ml = MLConfig()
        self.recommendation = RecommendationConfig()
        self.ai = AIConfig()
        self.cors = CORSConfig()
        self.performance = PerformanceConfig()
        self.logging = LoggingConfig()
        
        # Environment name
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'true' if self.environment == 'development' else 'false').lower() == 'true'
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"✅ Unified configuration loaded for environment: {self.environment}")
    
    def _validate_config(self):
        """Validate configuration values"""
        warnings = []
        errors = []
        
        # Check database URL
        if not self.database.url:
            errors.append("DATABASE_URL is not set")
        
        # Check secret keys in production
        if self.environment == 'production':
            if self.security.secret_key == 'dev-secret-key-change-in-production':
                errors.append("SECRET_KEY must be changed in production")
            if self.security.jwt_secret_key == 'dev-jwt-secret-change-in-production':
                errors.append("JWT_SECRET_KEY must be changed in production")
            if self.debug:
                warnings.append("DEBUG mode should be disabled in production")
        
        # Check AI configuration
        if self.ai.enable_gemini and not self.ai.gemini_api_key:
            warnings.append("GEMINI_API_KEY is not set, Gemini features will be disabled")
        
        # Log warnings and errors
        for warning in warnings:
            logger.warning(f"⚠️ Configuration warning: {warning}")
        
        for error in errors:
            logger.error(f"❌ Configuration error: {error}")
        
        if errors and self.environment == 'production':
            raise ValueError(f"Invalid production configuration: {', '.join(errors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            'environment': self.environment,
            'debug': self.debug,
            'database': asdict(self.database),
            'redis': asdict(self.redis),
            'security': {k: v for k, v in asdict(self.security).items() if 'key' not in k.lower()},  # Exclude sensitive keys
            'ml': asdict(self.ml),
            'recommendation': asdict(self.recommendation),
            'ai': {k: v for k, v in asdict(self.ai).items() if 'key' not in k.lower()},  # Exclude API keys
            'cors': asdict(self.cors),
            'performance': asdict(self.performance),
            'logging': asdict(self.logging)
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export configuration as JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def save_to_file(self, filepath: str):
        """Save configuration to JSON file"""
        try:
            with open(filepath, 'w') as f:
                f.write(self.to_json())
            logger.info(f"✅ Configuration saved to {filepath}")
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration"""
        return {
            # Application
            'SECRET_KEY': self.security.secret_key,
            'DEBUG': self.debug,
            'ENV': self.environment,
            
            # JWT
            'JWT_SECRET_KEY': self.security.jwt_secret_key,
            'JWT_ACCESS_TOKEN_EXPIRES': timedelta(hours=self.security.jwt_access_token_expires_hours),
            'JWT_REFRESH_TOKEN_EXPIRES': timedelta(days=self.security.jwt_refresh_token_expires_days),
            
            # Database
            'SQLALCHEMY_DATABASE_URI': self.database.url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': self.database.pool_size,
                'pool_timeout': self.database.pool_timeout,
                'pool_recycle': self.database.pool_recycle,
                'pool_pre_ping': self.database.pool_pre_ping,
                'max_overflow': self.database.max_overflow,
                'echo': self.database.echo,
                'connect_args': {
                    'connect_timeout': self.database.connect_timeout,
                    'sslmode': self.database.ssl_mode,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5,
                    'application_name': f'fuze_{self.environment}',
                }
            },
            
            # CORS
            'CORS_ORIGINS': self.cors.origins,
            'CORS_SUPPORTS_CREDENTIALS': self.cors.supports_credentials,
            'CORS_MAX_AGE': self.cors.max_age,
        }
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == 'development'

# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_config_instance = None

def get_config() -> UnifiedConfig:
    """Get singleton configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = UnifiedConfig()
    return _config_instance

def reload_config():
    """Reload configuration (useful for testing or dynamic updates)"""
    global _config_instance
    _config_instance = None
    return get_config()

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config().database

def get_ml_config() -> MLConfig:
    """Get ML configuration"""
    return get_config().ml

def get_recommendation_config() -> RecommendationConfig:
    """Get recommendation configuration"""
    return get_config().recommendation

def get_ai_config() -> AIConfig:
    """Get AI configuration"""
    return get_config().ai

# ============================================================================
# ENVIRONMENT FILE GENERATOR
# ============================================================================

def generate_env_template(output_file: str = '.env.example'):
    """Generate .env template file with all available configuration options"""
    template = """# ==============================================================================
# FUZE - UNIFIED CONFIGURATION
# ==============================================================================
# Copy this file to .env and fill in your values
# All values shown are defaults - only override what you need

# ==============================================================================
# ENVIRONMENT
# ==============================================================================
ENVIRONMENT=development
DEBUG=true

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================
DATABASE_URL=postgresql://user:password@localhost:5432/fuze
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=20
DB_POOL_RECYCLE=300
DB_POOL_PRE_PING=true
DB_ECHO=false
DB_CONNECT_TIMEOUT=30
DB_SSL_MODE=prefer

# ==============================================================================
# REDIS CONFIGURATION
# ==============================================================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_DEFAULT_TTL=3600
REDIS_MAX_CONNECTIONS=50

# ==============================================================================
# SECURITY CONFIGURATION
# ==============================================================================
SECRET_KEY=change-this-in-production-to-a-random-string
JWT_SECRET_KEY=change-this-in-production-to-a-random-string
JWT_ACCESS_TOKEN_EXPIRES_HOURS=1
JWT_REFRESH_TOKEN_EXPIRES_DAYS=30
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5

# ==============================================================================
# MACHINE LEARNING CONFIGURATION
# ==============================================================================
EMBEDDING_MODEL=all-MiniLM-L6-v2
SPACY_MODEL=en_core_web_sm
ML_LEARNING_RATE=0.05
ML_DECAY_RATE=0.95
TFIDF_MAX_FEATURES=5000
TFIDF_NGRAM_MIN=1
TFIDF_NGRAM_MAX=3
BM25_K1_INITIAL=1.5
BM25_B_INITIAL=0.75
INTERACTION_WEIGHT_DECAY=0.95
MIN_INTERACTIONS_FOR_PERSONALIZATION=5

# ==============================================================================
# RECOMMENDATION ENGINE CONFIGURATION
# ==============================================================================
MAX_RECOMMENDATIONS_DEFAULT=10
MAX_RECOMMENDATIONS_LIMIT=50
MIN_QUALITY_SCORE=0.0
MIN_RELEVANCE_SCORE=0.1
MIN_CONFIDENCE_SCORE=0.3
ENABLE_DIVERSITY=true
DIVERSITY_THRESHOLD=0.7
CACHE_RECOMMENDATIONS=true
CACHE_TTL_SECONDS=1800
MAX_CONTENT_ITEMS_TO_PROCESS=1000
CONTENT_TEXT_MAX_LENGTH=2000

# ==============================================================================
# AI SERVICES CONFIGURATION
# ==============================================================================
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-pro
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_TOKENS=1024
GEMINI_TIMEOUT=30
ENABLE_GEMINI=true

# ==============================================================================
# CORS CONFIGURATION
# ==============================================================================
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,chrome-extension://*
CORS_SUPPORTS_CREDENTIALS=true
CORS_MAX_AGE=86400

# ==============================================================================
# PERFORMANCE CONFIGURATION
# ==============================================================================
ENABLE_QUERY_CACHING=true
ENABLE_EMBEDDING_CACHING=true
ENABLE_PARALLEL_PROCESSING=true
MAX_WORKERS=4
REQUEST_TIMEOUT_SECONDS=30
SLOW_QUERY_THRESHOLD_MS=1000

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE_PATH=
LOG_MAX_FILE_SIZE_MB=10
LOG_BACKUP_COUNT=5
LOG_ENABLE_CONSOLE=true

# ==============================================================================
# PRODUCTION NOTES
# ==============================================================================
# For production deployment:
# 1. Set ENVIRONMENT=production
# 2. Set DEBUG=false
# 3. Generate strong SECRET_KEY and JWT_SECRET_KEY
# 4. Use SSL for database (DB_SSL_MODE=require)
# 5. Set proper CORS_ORIGINS (no wildcards)
# 6. Enable all caching options
# 7. Set appropriate LOG_FILE_PATH
# ==============================================================================
"""
    
    try:
        with open(output_file, 'w') as f:
            f.write(template)
        print(f"✅ Generated .env template file: {output_file}")
    except Exception as e:
        print(f"❌ Failed to generate template: {e}")

# ============================================================================
# TESTING
# ============================================================================

def test_config():
    """Test configuration system"""
    print("🧪 Testing Unified Configuration System")
    print("=" * 60)
    
    try:
        # Load configuration
        config = get_config()
        print(f"✅ Configuration loaded for environment: {config.environment}")
        
        # Test database config
        print(f"\n📊 Database Configuration:")
        print(f"   Pool Size: {config.database.pool_size}")
        print(f"   Max Overflow: {config.database.max_overflow}")
        print(f"   SSL Mode: {config.database.ssl_mode}")
        
        # Test ML config
        print(f"\n🤖 ML Configuration:")
        print(f"   Embedding Model: {config.ml.embedding_model}")
        print(f"   Learning Rate: {config.ml.learning_rate}")
        print(f"   TF-IDF Max Features: {config.ml.tfidf_max_features}")
        
        # Test recommendation config
        print(f"\n🎯 Recommendation Configuration:")
        print(f"   Max Recommendations: {config.recommendation.max_recommendations_default}")
        print(f"   Enable Diversity: {config.recommendation.enable_diversity}")
        print(f"   Cache TTL: {config.recommendation.cache_ttl_seconds}s")
        
        # Test Flask config export
        flask_config = config.get_flask_config()
        print(f"\n⚙️ Flask Configuration Keys: {len(flask_config)}")
        
        # Export to JSON
        json_config = config.to_json()
        print(f"\n📄 JSON Export Length: {len(json_config)} characters")
        
        print("\n🎉 Configuration system test completed successfully!")
        return True
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Generate .env template
    generate_env_template()
    
    # Test configuration
    test_config()


