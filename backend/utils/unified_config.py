#!/usr/bin/env python3
"""
Unified Configuration System for Fuze
=====================================

Single source of truth for all configuration values.
NO hardcoded values in code - everything comes from here.
Supports environment variables, defaults, and runtime updates.
Date: November 2025
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

def _default_ssl_mode() -> str:
    from core.app_env import is_production
    return 'require' if is_production() else 'prefer'


WEB_ROLE = 'web'
WORKER_ROLE = 'worker'

# Every process has its own connection pool, and all of them share the database pooler's
# connection limit (docs/OPERATIONS.md, "Database connections"). Web workers serve concurrent
# requests; RQ workers run one job at a time plus the reconciler, so they need few connections.
# (env var for pool_size, default), (env var for max_overflow, default)
_POOL_SETTINGS = {
    WEB_ROLE: (('DB_POOL_SIZE', 5), ('DB_MAX_OVERFLOW', 5)),
    WORKER_ROLE: (('DB_WORKER_POOL_SIZE', 2), ('DB_WORKER_MAX_OVERFLOW', 1)),
}


def process_role() -> str:
    """'worker' in RQ worker processes (backend/worker.py sets FUZE_PROCESS_ROLE), else 'web'."""
    role = os.getenv('FUZE_PROCESS_ROLE', '').strip().lower()
    return role if role in _POOL_SETTINGS else WEB_ROLE


def _pool_setting(index: int) -> int:
    name, default = _POOL_SETTINGS[process_role()][index]
    return int(os.getenv(name) or default)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', ''))
    pool_size: int = field(default_factory=lambda: _pool_setting(0))
    max_overflow: int = field(default_factory=lambda: _pool_setting(1))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv('DB_POOL_TIMEOUT', '20')))
    pool_recycle: int = field(default_factory=lambda: int(os.getenv('DB_POOL_RECYCLE', '300')))
    pool_pre_ping: bool = field(default_factory=lambda: os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true')
    # With pre-ping on, ping a pooled connection only after it has been idle this many seconds (every
    # request otherwise pays a `SELECT 1` round trip). 0 pings on every checkout, as plain pre-ping does.
    ping_idle_seconds: int = field(default_factory=lambda: int(os.getenv('DB_PING_IDLE_SECONDS', '15')))
    echo: bool = field(default_factory=lambda: os.getenv('DB_ECHO', 'false').lower() == 'true')
    # A request must never wait 30 s for a connection or hang on one query: fail fast instead.
    connect_timeout: int = field(default_factory=lambda: int(os.getenv('DB_CONNECT_TIMEOUT', '5')))
    statement_timeout_ms: int = field(default_factory=lambda: int(os.getenv('DB_STATEMENT_TIMEOUT_MS', '15000')))
    # Deployed environments only talk to Postgres over TLS; local Postgres usually has none.
    ssl_mode: str = field(default_factory=lambda: os.getenv('DB_SSL_MODE') or _default_ssl_mode())

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = field(default_factory=lambda: os.getenv('REDIS_HOST', 'localhost'))
    port: int = field(default_factory=lambda: int(os.getenv('REDIS_PORT', '6379')))
    db: int = field(default_factory=lambda: int(os.getenv('REDIS_DB', '0')))
    password: Optional[str] = field(default_factory=lambda: os.getenv('REDIS_PASSWORD'))

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = field(default_factory=lambda: os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'))
    jwt_secret_key: str = field(default_factory=lambda: os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-change-in-production'))
    jwt_access_token_expires_hours: int = field(default_factory=lambda: int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_HOURS', '1')))
    jwt_refresh_token_expires_days: int = field(default_factory=lambda: int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES_DAYS', '30')))

@dataclass
class AIConfig:
    """AI services configuration"""
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY'))
    gemini_model: str = field(default_factory=lambda: os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'))
    gemini_fallback_model: str = field(default_factory=lambda: os.getenv('GEMINI_FALLBACK_MODEL', 'gemini-2.5-flash-lite'))
    gemini_temperature: float = field(default_factory=lambda: float(os.getenv('GEMINI_TEMPERATURE', '0.7')))
    gemini_max_tokens: int = field(default_factory=lambda: int(os.getenv('GEMINI_MAX_TOKENS', '1024')))
    gemini_timeout: int = field(default_factory=lambda: int(os.getenv('GEMINI_TIMEOUT', '30')))
    enable_gemini: bool = field(default_factory=lambda: os.getenv('ENABLE_GEMINI', 'true').lower() == 'true')
    # An OpenAI-compatible provider (CloseRouter, OpenRouter...) instead of Gemini for the whole
    # deployment. Off unless LLM_PROVIDER=openai_compat; see utils/llm_provider.py.
    llm_provider: str = field(default_factory=lambda: os.getenv('LLM_PROVIDER', 'gemini').strip().lower())
    llm_base_url: Optional[str] = field(default_factory=lambda: (os.getenv('LLM_BASE_URL') or '').strip() or None)
    llm_api_key: Optional[str] = field(default_factory=lambda: (os.getenv('LLM_API_KEY') or '').strip() or None)
    llm_model: Optional[str] = field(default_factory=lambda: (os.getenv('LLM_MODEL') or '').strip() or None)
    llm_fallback_model: Optional[str] = field(default_factory=lambda: (os.getenv('LLM_FALLBACK_MODEL') or '').strip() or None)
    # Ask the provider for JSON-only output. Off by default: not every routed model accepts it,
    # and the prompts already demand JSON and the parser copes with fenced or chatty replies.
    llm_json_mode: bool = field(default_factory=lambda: os.getenv('LLM_JSON_MODE', 'false').lower() == 'true')
    # Output budget per call. Much larger than GEMINI_MAX_TOKENS: models behind a router often "think"
    # first and that hidden reasoning (500-700 tokens for a short page) counts against the limit, so
    # 1024 cut the JSON off mid-reply for about four bookmarks in five. Only tokens used are billed.
    llm_max_tokens: int = field(default_factory=lambda: int(os.getenv('LLM_MAX_TOKENS', '4096')))

@dataclass
class CORSConfig:
    """CORS configuration"""
    origins: list = field(default_factory=lambda: [
        origin.strip() 
        for origin in os.getenv('CORS_ORIGINS', '').split(',')
        if origin.strip()
    ])
    supports_credentials: bool = field(default_factory=lambda: os.getenv('CORS_SUPPORTS_CREDENTIALS', 'true').lower() == 'true')
    max_age: int = field(default_factory=lambda: int(os.getenv('CORS_MAX_AGE', '86400')))

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
        self.ai = AIConfig()
        self.cors = CORSConfig()
        
        # Environment name
        from core.app_env import app_env
        self.environment = app_env()
        self.debug = os.getenv('DEBUG', 'true' if self.environment == 'development' else 'false').lower() == 'true'
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"Unified configuration loaded for environment: {self.environment}")
    
    def _validate_config(self):
        """Validate configuration values"""
        warnings = []
        errors = []
        
        # Check database URL
        if not self.database.url:
            errors.append("DATABASE_URL is not set")
        
        # Deployed environments must not run on missing or published default secrets
        if self.environment == 'production':
            from core.app_env import secret_problems
            errors.extend(secret_problems())
            if self.debug:
                warnings.append("DEBUG mode should be disabled in production")
        
        # Check AI configuration
        from utils.llm_provider import config_problems, is_active as llm_provider_active
        errors.extend(config_problems(self.ai))
        if self.ai.enable_gemini and not self.ai.gemini_api_key and not llm_provider_active(self.ai):
            warnings.append("GEMINI_API_KEY is not set, Gemini features will be disabled")
        
        # Log warnings and errors
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
        
        for error in errors:
            logger.error(f"Configuration error: {error}")
        
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
            'ai': {k: v for k, v in asdict(self.ai).items() if 'key' not in k.lower()},  # Exclude API keys
            'cors': asdict(self.cors),
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export configuration as JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration"""
        # Check if using SQLite (SQLite doesn't support pool parameters)
        is_sqlite = 'sqlite' in self.database.url.lower()
        
        # Base engine options
        engine_options = {
            'echo': self.database.echo,
        }
        
        # Add pool options only for non-SQLite databases
        if not is_sqlite:
            engine_options.update({
                'pool_size': self.database.pool_size,
                'pool_timeout': self.database.pool_timeout,
                'pool_recycle': self.database.pool_recycle,
                # Idle-only pinging (utils/db_pool.py) replaces per-checkout pre-ping when enabled.
                'pool_pre_ping': self.database.pool_pre_ping and self.database.ping_idle_seconds <= 0,
                'max_overflow': self.database.max_overflow,
                'connect_args': {
                    'connect_timeout': self.database.connect_timeout,
                    'sslmode': self.database.ssl_mode,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5,
                    'application_name': f'fuze_{self.environment}',
                }
            })
        else:
            # SQLite-specific options
            engine_options['connect_args'] = {'check_same_thread': False}
        
        return {
            # Application
            'SECRET_KEY': self.security.secret_key,
            'DEBUG': self.debug,
            'ENV': self.environment,
            
            # JWT
            'JWT_SECRET_KEY': self.security.jwt_secret_key,
            'JWT_ACCESS_TOKEN_EXPIRES': timedelta(hours=self.security.jwt_access_token_expires_hours),
            'JWT_REFRESH_TOKEN_EXPIRES': timedelta(days=self.security.jwt_refresh_token_expires_days),
            'JWT_TOKEN_LOCATION': ['headers', 'cookies'],
            # JWT Cookie Security (Production-grade)
            'JWT_COOKIE_SECURE': not self.is_development(),  # HTTPS only in production
            'JWT_COOKIE_HTTPONLY': True,  # Prevent XSS attacks
            'JWT_COOKIE_SAMESITE': 'Lax',  # CSRF protection
            'JWT_COOKIE_CSRF_PROTECT': True,  # Enable CSRF protection for cookies
            'JWT_ACCESS_CSRF_HEADER_NAME': 'X-CSRF-TOKEN',
            # Session cookie security for Flask sessions (keep in sync with JWT cookie settings)
            'SESSION_COOKIE_SECURE': not self.is_development(),
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            
            # Database
            'SQLALCHEMY_DATABASE_URI': self.database.url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': engine_options,
            
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
