# Production Fixes - Detailed Action Plan

## Priority 1: Critical Security Fixes (Do First)

### Fix 1.1: Remove Debug Mode from app.py
**File**: `app.py`
**Line**: 108
**Current**:
```python
app.run(
    host='0.0.0.0',
    port=5000,
    debug=True,  # ❌ REMOVE THIS
    threaded=True
)
```
**Fix**:
```python
app.run(
    host='0.0.0.0',
    port=5000,
    debug=False,  # ✅ Always False in production
    threaded=True
)
```

### Fix 1.2: Replace All print() Statements with Logging
**Files**: All blueprint files
**Pattern**: Find all `print()` calls, replace with `logger.info()`, `logger.error()`, etc.

**Example Fix**:
```python
# ❌ BAD
print(f"✅ Intent analysis generated for new project: {intent.primary_goal}")

# ✅ GOOD
logger.info(f"Intent analysis generated for new project: {intent.primary_goal}")
```

**Files to Fix**:
- `blueprints/recommendations.py` - Multiple print statements
- `blueprints/projects.py` - Lines 92, 95, 199, 202
- `blueprints/bookmarks.py` - Lines 199, 205, 450, 466
- `blueprints/search.py` - Lines 14, 15, 23, 25, 28, 145, 153, 210, 234, 244, 319
- `blueprints/backup.py` - Many print statements
- All other blueprint files

### Fix 1.3: Implement Rate Limiting
**File**: `app.py` or new `middleware/rate_limit.py`

**Add**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.environ.get('REDIS_URL', 'memory://')
)

# Apply to specific endpoints
@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
@limiter.limit("10 per minute")
@jwt_required()
def unified_orchestrator():
    ...
```

### Fix 1.4: Tighten CORS Configuration
**File**: `app.py` and `run_production.py`

**Current** (too permissive):
```python
CORS(app, 
     origins=['http://localhost:3000', 'http://localhost:5173', ...],
     ...
)
```

**Fix** (production):
```python
# Development
if app.config.get('DEBUG'):
    CORS(app, origins=['http://localhost:3000', 'http://localhost:5173'])
else:
    # Production - only allow specific domains
    allowed_origins = os.environ.get('CORS_ORIGINS', '').split(',')
    CORS(app, 
         origins=allowed_origins,
         supports_credentials=True,
         max_age=86400
    )
```

### Fix 1.5: Add Input Validation
**Create**: `middleware/validation.py`

```python
from functools import wraps
from flask import request, jsonify

def validate_json(schema):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON'}), 400
            
            # Validate against schema
            errors = validate_schema(data, schema)
            if errors:
                return jsonify({'error': 'Validation failed', 'details': errors}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage in blueprints:
@recommendations_bp.route('/unified-orchestrator', methods=['POST'])
@validate_json({
    'title': {'type': 'string', 'required': True, 'maxlength': 200},
    'description': {'type': 'string', 'maxlength': 2000},
    'technologies': {'type': 'string', 'maxlength': 500}
})
```

---

## Priority 2: Code Duplication Removal

### Fix 2.1: Consolidate Recommendation Blueprints
**Action**: 
1. Keep only `blueprints/recommendations.py`
2. Move `enhanced_recommendations.py` to `deprecated/`
3. Move `recommendations_clean.py` to `deprecated/`
4. Move `backup.py` to `deprecated/`
5. Update `app.py` to only import `recommendations_bp`

### Fix 2.2: Remove Duplicate Engine Files
**Action**: Move to `deprecated/engines/`:
- `phase3_enhanced_engine.py`
- `enhanced_recommendation_engine.py`
- `ensemble_recommendation_engine.py` (if duplicate)
- `fast_gemini_engine.py` (if duplicate)
- All other duplicate engines

**Keep Only**:
- `unified_recommendation_orchestrator.py`
- `advanced_nlp_engine.py`
- `adaptive_scoring_engine.py`
- `advanced_tech_detection.py`
- `universal_semantic_matcher.py`

### Fix 2.3: Remove Duplicate Database Utilities
**Files**: Check for duplicate functions in:
- `database_utils.py`
- `database_connection_manager.py`

**Action**: Consolidate into single utility module

---

## Priority 3: Configuration Management

### Fix 3.1: Replace Hardcoded Values
**File**: `unified_recommendation_orchestrator.py`

**Pattern to Find**:
```python
# ❌ BAD - Hardcoded values
relevance_score += tech_score * 0.60
if similarity > 0.8:
    boost_factor = 1.5
min_score_threshold = 25
```

**Fix**:
```python
# ✅ GOOD - Use config
from recommendation_config import get_scoring_weight, get_threshold, get_boost_factor

relevance_score += tech_score * get_scoring_weight('tech_priority_weight', 0.60)
if similarity > get_threshold('high_similarity', 0.8):
    boost_factor = get_boost_factor('high_similarity_boost', 1.5)
min_score_threshold = get_threshold('score_minimum', 25)
```

**Estimated Occurrences**: 100+ instances to fix

### Fix 3.2: Consolidate Environment Files
**Action**:
1. Create single `.env.example` with all variables
2. Document each variable
3. Remove duplicate env files:
   - `env_template.txt`
   - `env_production_template.txt`
   - `orchestrator_config.env.example`
   - `tech_config.env.example`

---

## Priority 4: Test Organization

### Fix 4.1: Create Test Structure
**Action**:
```bash
mkdir -p tests/unit tests/integration tests/e2e tests/fixtures
```

### Fix 4.2: Move Test Files
**Action**: Move all `test_*.py` files from root to appropriate test directories:
- Unit tests → `tests/unit/`
- Integration tests → `tests/integration/`
- E2E tests → `tests/e2e/`
- Debug scripts → `scripts/debug/` or delete

### Fix 4.3: Create Test Configuration
**Create**: `tests/conftest.py`
```python
import pytest
import os
from app import create_app
from models import db

@pytest.fixture
def app():
    os.environ['TESTING'] = 'True'
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
```

---

## Priority 5: Performance Optimizations

### Fix 5.1: Add Database Indexes
**Check**: `models.py` for missing indexes

**Add indexes for**:
- `saved_content.user_id` (if not exists)
- `saved_content.created_at` (for sorting)
- `content_analysis.content_id` (foreign key)
- `projects.user_id` (foreign key)
- `feedback.user_id` (foreign key)

### Fix 5.2: Optimize Queries
**Pattern to Find**: N+1 queries
```python
# ❌ BAD - N+1 query
for project in projects:
    user = User.query.get(project.user_id)  # Query in loop
```

**Fix**:
```python
# ✅ GOOD - Eager loading
projects = Project.query.options(joinedload(Project.user)).all()
```

### Fix 5.3: Split Large Files
**File**: `unified_recommendation_orchestrator.py` (8000+ lines)

**Action**: Split into:
- `engines/orchestrator.py` (main orchestrator)
- `engines/fast_semantic_engine.py`
- `engines/context_aware_engine.py`
- `engines/intelligent_engine.py`
- `engines/data_layer.py`

---

## Priority 6: Code Quality

### Fix 6.1: Remove Commented Code
**Action**: Search for commented code blocks and remove them

### Fix 6.2: Resolve TODOs
**Action**: 
1. Create GitHub issues for each TODO
2. Remove TODO comments, replace with issue references
3. Or implement the TODO if quick fix

### Fix 6.3: Standardize Error Handling
**Create**: `utils/errors.py`
```python
class APIError(Exception):
    def __init__(self, message, status_code=400, error_code=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

@app.errorhandler(APIError)
def handle_api_error(error):
    response = {
        'error': error.message,
        'status_code': error.status_code
    }
    if error.error_code:
        response['error_code'] = error.error_code
    return jsonify(response), error.status_code
```

---

## Priority 7: Documentation Cleanup

### Fix 7.1: Consolidate Documentation
**Action**: 
1. Create `docs/` directory
2. Move relevant docs:
   - `docs/API.md` - API documentation
   - `docs/DEPLOYMENT.md` - Deployment guide
   - `docs/ARCHITECTURE.md` - System architecture
   - `docs/DEVELOPMENT.md` - Development guide
3. Archive old docs to `docs/archive/`
4. Update `README.md` with current info

### Fix 7.2: Remove Redundant Docs
**Action**: Move to `docs/archive/`:
- All `*_SUMMARY.md` files (keep only latest)
- All `*_GUIDE.md` files (consolidate)
- All `*_ANALYSIS.md` files (archive)

---

## Implementation Order

### Week 1: Security & Critical Fixes
1. Day 1-2: Remove debug mode, replace print() with logging
2. Day 3: Implement rate limiting
3. Day 4: Fix CORS, add input validation
4. Day 5: Sanitize error messages, security audit

### Week 2: Code Organization
1. Day 1-2: Consolidate engines and blueprints
2. Day 3: Organize test files
3. Day 4: Clean up configuration files
4. Day 5: Remove commented code, resolve TODOs

### Week 3: Performance & Polish
1. Day 1-2: Replace hardcoded values
2. Day 3: Optimize database queries
3. Day 4: Split large files
4. Day 5: Documentation cleanup

### Week 4: Testing & Validation
1. Day 1-2: Write proper tests
2. Day 3: Performance testing
3. Day 4: Security testing
4. Day 5: Final review and deployment prep

---

## Quick Wins (Can Do Immediately)

1. **Remove print() statements** - 2-3 hours
2. **Fix debug mode** - 5 minutes
3. **Remove duplicate blueprint imports** - 1 hour
4. **Create test directory structure** - 30 minutes
5. **Consolidate .env files** - 1-2 hours

---

## Validation Checklist

After each fix, verify:
- [ ] Application still runs
- [ ] Tests pass (if applicable)
- [ ] No new errors in logs
- [ ] Performance not degraded
- [ ] Security improvements verified

---

## Notes

- Always test in development before applying to production
- Use feature branches for all changes
- Review code before merging
- Keep backups of working state
- Document changes as you go

