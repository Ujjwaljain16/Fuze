# Repository Structure

This document describes the clean, production-ready repository structure.

## Directory Structure

```
fuze/
├── blueprints/              # Flask blueprints (API routes)
│   ├── auth.py
│   ├── bookmarks.py
│   ├── feedback.py
│   ├── linkedin.py
│   ├── profile.py
│   ├── projects.py
│   ├── recommendations.py   # Main recommendations blueprint
│   ├── search.py
│   ├── tasks.py
│   └── user_api_key.py
│
├── middleware/              # Middleware components
│   ├── __init__.py
│   ├── rate_limiting.py    # Rate limiting middleware
│   └── validation.py       # Input validation middleware
│
├── scripts/                 # Utility scripts (not imported by app)
│   ├── database/           # Database-related scripts
│   ├── migrations/         # Migration scripts
│   ├── utils/              # General utilities
│   └── README.md
│
├── docs/                   # Documentation
│   ├── archive/            # Archived/outdated docs
│   └── README.md
│
├── deprecated/             # Deprecated code (not used)
│   ├── blueprints/         # Old blueprint versions
│   ├── engines/            # Deprecated engine files
│   └── support/            # Deprecated support modules
│
├── frontend/               # React frontend application
│   └── ...
│
├── BookmarkExtension/      # Chrome extension
│   └── ...
│
├── migrations/             # Database migrations (Alembic)
│   └── ...
│
├── static/                # Static files
│   └── ...
│
├── templates/             # HTML templates
│   └── ...
│
├── public/                # Public assets
│   └── ...
│
├── certs/                 # SSL certificates (not in git)
│   └── ...
│
├── instance/             # Instance-specific files
│   └── ...
│
├── ml_engines/           # ML/Recommendation engines
│   └── ...
│
# Core application files (in root for direct imports)
# Entry Points:
├── run_production.py     # Main production entry point
├── app.py                # Development entry point
├── wsgi.py               # WSGI entry point
│
# Core Configuration & Utilities:
├── config.py             # Application configuration
├── unified_config.py     # Unified configuration system
├── recommendation_config.py  # Recommendation configuration
│
# Database & Models:
├── models.py             # Database models
├── database_utils.py     # Database utilities
├── database_connection_manager.py  # Connection manager
├── init_db.py            # Database initialization
│
# Core Services:
├── redis_utils.py        # Redis caching
├── embedding_utils.py    # Embedding generation
├── gemini_utils.py       # Gemini AI utilities
├── utils_web_scraper.py  # Web scraping utilities
│
# ML & Recommendation System:
├── unified_recommendation_orchestrator.py  # Main orchestrator
├── intent_analysis_engine.py  # Intent analysis
├── explainability_engine.py   # Explainability
├── skill_gap_analyzer.py      # Skill gap analysis
├── project_embedding_manager.py  # Project embeddings
├── simple_ml_enhancer.py  # ML enhancer
├── universal_semantic_matcher.py  # Semantic matching
│
# Services & Utilities:
├── background_analysis_service.py  # Background service
├── cache_invalidation_service.py   # Cache management
├── multi_user_api_manager.py      # API management
├── rate_limit_handler.py          # Rate limiting
├── logging_config.py              # Logging configuration
│
# LinkedIn Scrapers:
├── easy_linkedin_scraper.py  # Main LinkedIn scraper (used by blueprints)
├── enhanced_web_scraper.py  # General web scraper
│
├── engines/              # Recommendation engines (if separate)
│   └── ...
│
├── .env.example          # Environment variables template
├── requirements.txt      # Python dependencies
├── README.md            # Main project README
└── REPOSITORY_STRUCTURE.md  # This file
```

## File Organization Rules

### Blueprints (`blueprints/`)
- One blueprint per feature area
- No duplicate blueprints
- All routes properly organized

### Middleware (`middleware/`)
- Reusable middleware components
- Rate limiting, validation, etc.

### Scripts (`scripts/`)
- Utility scripts that are NOT imported by the main app
- Organized by category (database, migrations, utils)
- For maintenance and development only

### Deprecated (`deprecated/`)
- Old code that's no longer used
- Kept for reference but not imported
- Can be safely deleted after verification

### Documentation (`docs/`)
- Current documentation in root of `docs/`
- Archived/outdated docs in `docs/archive/`

## Production Files

### Main Entry Points
- `run_production.py` - Production server (USE THIS)
- `app.py` - Development server

### Configuration
- `config.py` - Application configuration
- `.env` - Environment variables (not in git)
- `.env.example` - Template for environment variables

### Core Utilities
- `models.py` - Database models
- `database_utils.py` - Database helper functions
- `redis_utils.py` - Redis caching
- `embedding_utils.py` - Embedding generation

## Current Status

### Test Files
- ✅ **All test files deleted** - All `test_*.py` and `test_*.js` files have been removed from root
- A proper test suite will be developed later in a `tests/` directory

### Documentation Files
- Essential docs kept in root: `README.md`, `REPOSITORY_STRUCTURE.md`, `SETUP_INSTRUCTIONS.md`, `SECURITY_SETUP.md`
- Feature-specific docs: `ANALYSIS_CACHING_SYSTEM.md`, `INTELLIGENT_FILTERING_SYSTEM.md`, `SCALABLE_ARCHITECTURE.md`, `LINKEDIN_SCRAPER_README.md`, `PROJECTS_SETUP.md`
- Cleanup/status docs moved to `docs/archive/`

### Utility Scripts
- ✅ All utility scripts organized in `scripts/` directory
- Scripts organized by category: `database/`, `debug/`, `utils/`
- Scripts are NOT imported by main application (as per design)

## Import Rules

1. **Main Application** (`run_production.py`, `app.py`)
   - Only imports from: `blueprints/`, `middleware/`, core files
   - Does NOT import from: `scripts/`, `deprecated/`

2. **Blueprints**
   - Import from: core utilities, models, engines
   - Do NOT import from: `scripts/`, `deprecated/`

3. **Scripts**
   - Can import from: core utilities, models
   - Should NOT be imported by main application

## Best Practices

1. Keep root directory clean - only essential files
2. Organize by function, not by file type
3. Use clear, descriptive names
4. Document in appropriate README files
5. Keep deprecated code separate
6. Don't mix production code with utility scripts

