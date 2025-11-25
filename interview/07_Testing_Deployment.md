# Part 7: Testing, Deployment & DevOps

## 📋 Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Backend Testing](#backend-testing)
3. [Frontend Testing](#frontend-testing)
4. [E2E Testing](#e2e-testing)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Deployment Architecture](#deployment-architecture)
7. [Docker Configuration](#docker-configuration)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Q&A Section](#qa-section)

---

## Testing Strategy

### Testing Pyramid

```
        /\
       /  \      E2E Tests (Few)
      /____\     Integration Tests (Some)
     /      \    Unit Tests (Many)
    /________\
```

**Distribution:**
- **Unit Tests**: 70% (fast, isolated)
- **Integration Tests**: 20% (moderate speed, test interactions)
- **E2E Tests**: 10% (slow, test full flows)

### Test Coverage Goals

- **Backend**: >80% coverage
- **Frontend**: >70% coverage
- **E2E**: All critical user flows

---

## Backend Testing

### Test Framework

**Framework**: pytest

**File**: `backend/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

### Test Structure

**Location**: `backend/tests/`

**Files:**
- `test_auth.py` - Authentication tests
- `test_bookmarks.py` - Bookmark CRUD tests
- `test_projects.py` - Project management tests
- `test_recommendations.py` - Recommendation engine tests
- `test_search.py` - Search functionality tests
- `test_services.py` - Background services tests
- `test_integration.py` - End-to-end API flows
- `conftest.py` - Shared fixtures

### Test Fixtures

**File**: `backend/tests/conftest.py`

```python
@pytest.fixture
def app():
    """Create test Flask app"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client"""
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    """Get auth headers for authenticated requests"""
    # Create test user
    user = User(username='testuser', email='test@example.com',
                password_hash=generate_password_hash('password123'))
    db.session.add(user)
    db.session.commit()
    
    # Login and get token
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    token = response.json['access_token']
    
    return {'Authorization': f'Bearer {token}'}
```

### Example Test

**File**: `backend/tests/test_auth.py`

```python
def test_login_success(client):
    """Test successful login"""
    # Create user
    user = User(username='testuser', email='test@example.com',
                password_hash=generate_password_hash('password123'))
    db.session.add(user)
    db.session.commit()
    
    # Login
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'password123'
    })
    
    assert response.status_code == 200
    assert 'access_token' in response.json
    assert response.json['user']['username'] == 'testuser'

def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post('/api/auth/login', json={
        'username': 'nonexistent',
        'password': 'wrongpassword'
    })
    
    assert response.status_code == 401
    assert 'Invalid credentials' in response.json['message']
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific file
pytest tests/test_auth.py

# Verbose
pytest -v

# Show prints
pytest -s
```

---

## Frontend Testing

### Test Framework

**Framework**: Vitest + React Testing Library

**File**: `frontend/vitest.config.js`

```javascript
export default {
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html']
    }
  }
}
```

### Test Structure

**Location**: `frontend/src/tests/`

**Files:**
- `pages/Login.test.jsx` - Login page tests
- `pages/Dashboard.test.jsx` - Dashboard tests
- `contexts/AuthContext.test.jsx` - Auth context tests
- `components/Button.test.jsx` - Component tests
- `hooks/useErrorHandler.test.js` - Hook tests
- `setup.js` - Test setup (mocks)

### Test Setup

**File**: `frontend/src/tests/setup.js`

```javascript
import { vi } from 'vitest'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.localStorage = localStorageMock

// Mock API
vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))
```

### Example Test

**File**: `frontend/src/tests/pages/Login.test.jsx`

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Login from '../../pages/Login'
import api from '../../services/api'

test('renders login form', () => {
  render(
    <BrowserRouter>
      <Login />
    </BrowserRouter>
  )
  
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
})

test('handles login success', async () => {
  api.post.mockResolvedValue({
    data: {
      access_token: 'test-token',
      user: { id: 1, username: 'testuser' }
    }
  })
  
  render(
    <BrowserRouter>
      <Login />
    </BrowserRouter>
  )
  
  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'test@example.com' }
  })
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: 'password123' }
  })
  fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
  
  await waitFor(() => {
    expect(api.post).toHaveBeenCalledWith('/api/auth/login', {
      email: 'test@example.com',
      password: 'password123'
    })
  })
})
```

### Running Tests

```bash
# All tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm run test:coverage

# UI mode
npm run test:ui
```

---

## E2E Testing

### Test Framework

**Framework**: Playwright

**File**: `e2e/playwright.config.js`

```javascript
export default {
  testDir: './tests',
  use: {
    baseURL: 'http://localhost:5173',
    headless: true
  },
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: !process.env.CI
  }
}
```

### Test Structure

**Location**: `e2e/tests/`

**Files:**
- `auth.spec.js` - Authentication flows
- `bookmarks.spec.js` - Bookmark operations
- `projects.spec.js` - Project management
- `recommendations.spec.js` - Recommendation flows
- `helpers/auth.js` - Shared login helper

### Example Test

**File**: `e2e/tests/auth.spec.js`

```javascript
import { test, expect } from '@playwright/test'
import { login } from '../helpers/auth'

test('user can login', async ({ page }) => {
  await page.goto('/login')
  
  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('button:has-text("Sign In")')
  
  await expect(page).toHaveURL(/\/dashboard/)
  await expect(page.locator('text=Dashboard')).toBeVisible()
})

test('user can register', async ({ page }) => {
  await page.goto('/login')
  await page.click('text=Create Account')
  
  await page.fill('input[name="username"]', 'newuser')
  await page.fill('input[name="email"]', 'newuser@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('button:has-text("Create Account")')
  
  await expect(page).toHaveURL(/\/dashboard/)
})
```

### Running E2E Tests

```bash
# All tests
npm test

# Sequential (prevents rate limiting)
CI=true npm test

# UI mode
npm run test:ui

# Headed mode (see browser)
npm run test:headed
```

---

## CI/CD Pipeline

### GitHub Actions

**File**: `.github/workflows/sync-to-hf-space.yml`

```yaml
name: Sync to Hugging Face Space

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          cd backend
          pytest
      
      - name: Deploy to Hugging Face
        run: |
          # Deployment steps
```

### Test Pipeline

**Stages:**
1. **Lint**: Code quality checks
2. **Unit Tests**: Fast unit tests
3. **Integration Tests**: API integration tests
4. **E2E Tests**: Full user flow tests
5. **Deploy**: Deploy to production

---

## Deployment Architecture

### Current Production Stack

```
┌─────────────────────────────────────┐
│    Hugging Face Spaces              │
│    (Handles Routing & SSL)           │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      Application Container          │
│  ┌──────────┐  ┌──────────┐        │
│  │ Gunicorn │  │   RQ     │        │
│  │ (1 worker│  │  Worker  │        │
│  │  gevent) │  │          │        │
│  └──────────┘  └──────────┘        │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      External Services              │
│  ┌──────────┐  ┌──────────┐        │
│  │  Redis   │  │PostgreSQL│        │
│  │ (Upstash)│  │(Supabase)│        │
│  └──────────┘  └──────────┘        │
└─────────────────────────────────────┘
```

**Current Setup:**
- Single container on Hugging Face Spaces
- 1 Gunicorn worker (gevent async - handles 1000+ connections)
- 1 RQ worker for background jobs
- External PostgreSQL (Supabase)
- External Redis (Upstash)

**Scalable Design (Future):**
- Can add load balancer (Nginx/Cloudflare)
- Can add more Gunicorn workers
- Can add database replicas
- Can scale Redis to cluster

### Deployment Platforms

**Backend**: Hugging Face Spaces
- Docker-based deployment
- Automatic builds on push
- Environment variable management

**Frontend**: Vercel
- Automatic deployments
- CDN distribution
- Preview deployments for PRs

### Environment Configuration

**File**: `.env.example`

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fuze

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# AI Services
GEMINI_API_KEY=your-gemini-api-key

# Application
FLASK_ENV=production
DEBUG=false
CORS_ORIGINS=https://yourdomain.com
```

---

## Docker Configuration

### Dockerfile

**File**: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Start application via start.sh
# start.sh runs:
# - RQ worker (background)
# - Gunicorn with 1 worker (gevent async)
CMD ["./start.sh"]
```

**Current Configuration:**
- 1 Gunicorn worker (gevent async - handles 1000+ connections)
- 1 RQ worker for background jobs
- Can scale by modifying `start.sh` to use more workers

### Docker Compose (Development)

**File**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: fuze
      POSTGRES_USER: fuze
      POSTGRES_PASSWORD: fuze
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://fuze:fuze@db:5432/fuze
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
```

---

## Monitoring and Logging

### Logging Configuration

**File**: `backend/utils/logging_config.py`

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    if not app.debug:
        # Production logging
        file_handler = RotatingFileHandler(
            'production.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
```

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

### Health Check Endpoint

**File**: `backend/blueprints/health.py`

```python
@health_bp.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    status = {
        'status': 'healthy',
        'database': 'connected' if check_database() else 'disconnected',
        'redis': 'connected' if check_redis() else 'disconnected',
        'timestamp': datetime.now().isoformat()
    }
    
    status_code = 200 if all([
        status['database'] == 'connected',
        status['redis'] == 'connected'
    ]) else 503
    
    return jsonify(status), status_code
```

---

## Q&A Section

### Q1: How do you handle database migrations in production?

**Answer:**
Currently using manual migrations. For production, we'd use Alembic:

1. **Create Migration**: `alembic revision --autogenerate -m "description"`
2. **Review Migration**: Check generated SQL
3. **Test Migration**: Run on staging first
4. **Apply Migration**: `alembic upgrade head`

**Current Approach:**
- Manual schema updates via `init_db.py`
- Index creation via `database_indexes.py`
- Column additions in model initialization

**Future**: Migrate to Alembic for version control

### Q2: How do you handle zero-downtime deployments?

**Answer:**
Multiple strategies:

1. **Blue-Green Deployment**: Deploy to new environment, switch traffic
2. **Rolling Updates**: Update workers one at a time
3. **Health Checks**: Verify new deployment before switching
4. **Database Migrations**: Backward-compatible migrations first

**Current Setup:**
- Stateless workers (easy to replace)
- Database migrations backward-compatible
- Health check endpoint for verification

### Q3: How do you monitor application performance?

**Answer:**
Multiple monitoring approaches:

1. **Application Logs**: Track operation durations
2. **Redis Monitoring**: Cache hit rates, memory usage
3. **Database Monitoring**: Slow query logs, connection pool stats
4. **Performance Dashboards**: Real-time metrics

**Metrics Tracked:**
- Response times (p50, p95, p99)
- Cache hit rates
- Database query times
- Error rates
- Throughput

### Q4: How do you handle secrets in production?

**Answer:**
Environment variables (never in code):

1. **Local Development**: `.env` file (gitignored)
2. **Production**: Environment variables in deployment platform
3. **Secrets Management**: Use platform's secrets manager
4. **Rotation**: Regular rotation of secrets

**Best Practices:**
- ✅ Never commit secrets to git
- ✅ Use different secrets for dev/staging/prod
- ✅ Rotate secrets regularly
- ✅ Use secrets manager for production

### Q5: How do you handle rollbacks?

**Answer:**
Multiple strategies:

1. **Git Revert**: Revert to previous commit
2. **Database Rollback**: Alembic downgrade (if needed)
3. **Docker Tags**: Keep previous image tags
4. **Health Checks**: Verify before full rollout

**Rollback Process:**
1. Identify issue
2. Revert code changes
3. Deploy previous version
4. Verify health
5. Monitor for issues

---

## Summary

Testing and deployment focus on:
- ✅ **Comprehensive testing** (Unit, Integration, E2E)
- ✅ **CI/CD pipeline** with automated tests
- ✅ **Docker containerization** for consistent deployments
- ✅ **Monitoring and logging** for production visibility
- ✅ **Health checks** for deployment verification
- ✅ **Zero-downtime deployments** with stateless architecture

**Key Files:**
- `backend/tests/` - Backend tests
- `frontend/src/tests/` - Frontend tests
- `e2e/tests/` - E2E tests
- `Dockerfile` - Docker configuration
- `.github/workflows/` - CI/CD pipelines

---

**End of Guide**: Return to [Overview](./README.md)

