# Testing Guide

Complete testing documentation for Backend and Frontend tests, plus the smoke test
against a running instance.

## Quick Start

```bash
# Test tools live in requirements-dev.txt (requirements.txt + pytest etc.);
# they are not installed in the production image.
pip install -r requirements-dev.txt

# Backend (Python/Pytest)
cd backend && pytest

# Frontend (Vitest)
cd frontend && npm test

# Smoke test against a real running instance
python scripts/e2e_smoke_test.py --base-url http://localhost:5000
```

## Backend Tests

**Location:** `backend/tests/`

**Run:**
```bash
cd backend
pytest                    # All tests
pytest --cov=.            # With coverage
pytest tests/test_auth.py # Specific file
pytest -v                 # Verbose
pytest -s                 # Show prints

# Postgres + pgvector lane (pgvector queries, SELECT ... FOR UPDATE, real concurrency)
docker run -d --name fuze-test-pg -e POSTGRES_PASSWORD=test -p 55432:5432 pgvector/pgvector:pg15
TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/postgres pytest
```

**Test Files:**
- `test_auth.py` - Authentication (register, login, logout, token refresh)
- `test_bookmarks.py` - Bookmarks CRUD, search, pagination
- `test_projects.py` - Projects CRUD
- `test_recommendations.py` / `test_intent_engine.py` - Intent x content recommendations
- `test_services.py` - Background services
- `test_pipeline_recovery.py` - Pipeline reconciler and failed-fetch handling
- `test_safe_http.py` - SSRF-safe fetching
- `test_oauth_account_linking.py` - Google sign-in never joins an account by email; `/api/auth/link-oauth`
- `test_postgres_concurrency.py` - Concurrent saves and refreshes (Postgres lane only)
- `test_integration.py` - End-to-end API flows
- `conftest.py` - Fixtures (app, db, auth_headers)

**Key Features:**
- In-memory SQLite by default; `TEST_DATABASE_URL` runs the same suite on a local
  Postgres + pgvector. `conftest.py` refuses any database that isn't SQLite or on
  localhost, so the suite can never touch production
- `APP_ENV=testing` is forced (unset would mean production)
- Redis is pointed at a local DB 15 (`TEST_REDIS_URL` overrides); tests that need a
  real Redis use `LIVE_REDIS_URL`
- Mocked Gemini
- JWT authentication fixtures; bcrypt at 4 rounds for speed

## Quality Checks

CI runs each of these and fails on any finding. Run them locally before pushing:

```bash
cd backend
ruff check .                                  # lint: pyflakes + import placement (backend/ruff.toml)
mypy                                          # types for core/ and utils/ (backend/mypy.ini)
pytest --cov=. --cov-fail-under=74            # suite plus the coverage floor CI enforces

cd frontend
npm run lint -- --max-warnings=0              # ESLint; warnings fail CI too
```

ruff and mypy are pinned in `requirements-dev.txt`. There is no `ruff format` step, and
import sorting (ruff's `I` rules) is not enabled yet. When coverage rises, raise
`--cov-fail-under` in `backend-ci.yml` to a few points under the new total.

## Frontend Tests

**Location:** `frontend/src/tests/`

**Run:**
```bash
cd frontend
npm test                  # All tests
npm run test:ui          # Interactive UI
npm run test:coverage    # Coverage report
npm test -- --watch      # Watch mode
```

**Test Files:**
- `pages/Login.test.jsx` - Login page integration
- `pages/Dashboard.test.jsx` - Dashboard page
- `contexts/AuthContext.test.jsx` - Auth context
- `components/ProtectedRoute.test.jsx` - Route protection
- `hooks/useErrorHandler.test.jsx` - Error handling
- `setup.js` - Global test setup (localStorage mock)

**Key Features:**
- Vitest + React Testing Library
- Mocked API calls
- localStorage mocking
- BrowserRouter/MemoryRouter support

## Smoke Test

There is no browser E2E suite (the Playwright `e2e/` folder was removed).
`scripts/e2e_smoke_test.py` exercises real user journeys over HTTP against a running
instance with real Postgres + pgvector, Redis and RQ workers:

```bash
python scripts/e2e_smoke_test.py --base-url http://localhost:5000
```

## CI Configuration

**Backend CI** (`.github/workflows/backend-ci.yml`), with Postgres (pgvector) and Redis services:
1. Install `requirements-dev.txt`
2. `ruff check` and `mypy` (see Quality Checks)
3. `pip-audit` over `requirements.lock` and `requirements.txt`: known vulnerabilities fail the build
4. `alembic upgrade head`, `alembic check`, then `downgrade 0001` → `upgrade head` → `check`
   (every downgrade must work and land on the same schema)
5. Full suite on SQLite with coverage; total coverage under 74% fails the build
6. Full suite again on Postgres + pgvector (`TEST_DATABASE_URL`)

A successful Backend CI run on `main` is what triggers the Hugging Face deploy.

**Frontend CI** (`.github/workflows/frontend-ci.yml`): Node 20; fails on high-severity
advisories in production dependencies, on any ESLint error or warning, on failing unit
tests, and on a broken production build.

All actions are pinned to commit SHAs and workflows get a read-only token by default.

## Test Structure

### Backend Test Example
```python
def test_login_success(client, auth_headers):
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert 'access_token' in response.json
```

### Frontend Test Example
```javascript
test('renders login form', () => {
  render(<Login />)
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
})
```

## Coverage Goals

- **Backend:** >80%
- **Frontend:** >70%
- **Smoke test:** All critical user flows

## Best Practices

1. **Isolation:** Each test is independent
2. **Fixtures:** Use reusable test data
3. **Mocking:** Mock external services
4. **Naming:** Descriptive test names
5. **AAA Pattern:** Arrange-Act-Assert
6. **Fast Tests:** Unit tests <100ms

## Troubleshooting

**Backend:**
- Database timeout: Check `conftest.py` teardown
- Import errors: Ensure virtual environment activated
- Rate limiting: disabled in `APP_ENV=testing` unless a test enables it
- `TEST_DATABASE_URL must be SQLite or a local Postgres`: point it at localhost

**Frontend:**
- localStorage issues: Check `setup.js` mock
- API mocking: Verify `api.get/post` mocks
- Timeouts: Increase `waitFor` timeouts

## Debugging

```bash
# Backend
pytest --pdb              # Debugger on failure

# Frontend
npm test -- --reporter=verbose

```

