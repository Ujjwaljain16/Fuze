#!/usr/bin/env python3
"""
Centralized Logging Configuration
Controls logging levels for SQLAlchemy and other components
"""

import logging
import os

def configure_logging(level='INFO', sqlalchemy_level='WARNING'):
    """
    Configure logging for the application
    
    Args:
        level: General logging level (DEBUG, INFO, WARNING, ERROR)
        sqlalchemy_level: SQLAlchemy logging level (WARNING, ERROR, CRITICAL)
    """
    
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure SQLAlchemy logging to reduce verbosity
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(getattr(logging, sqlalchemy_level.upper()))
    
    # Configure other noisy loggers
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Configure urllib3 (used by requests)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Configure requests
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Configure sentence_transformers
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    
    # Configure transformers
    logging.getLogger('transformers').setLevel(logging.WARNING)
    
    # Configure torch
    logging.getLogger('torch').setLevel(logging.WARNING)
    
    # Configure PIL
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    print(f"✅ Logging configured: General={level}, SQLAlchemy={sqlalchemy_level}")

def set_test_logging():
    """Configure logging for testing (minimal output)"""
    configure_logging(level='WARNING', sqlalchemy_level='ERROR')

def set_development_logging():
    """Configure logging for development (moderate output)"""
    configure_logging(level='INFO', sqlalchemy_level='WARNING')

def set_production_logging():
    """Configure logging for production (minimal output)"""
    configure_logging(level='WARNING', sqlalchemy_level='ERROR')

# Auto-configure based on environment
if os.environ.get('FLASK_ENV') == 'production':
    set_production_logging()
elif os.environ.get('FLASK_ENV') == 'development':
    set_development_logging()
else:
    # Default to development logging
    set_development_logging()
