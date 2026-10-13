# Testing Guide

Testing documentation for the backend, frontend and browser extension suites, plus the
smoke test against a running instance.

## Quick Start

```bash
# Test tools live in requirements-dev.txt at the repository root
# (requirements.txt + pytest etc.); they are not installed in the production image.
pip install -r requirements-dev.txt

# Backend (Python/Pytest)
cd backend && pytest

# Frontend (Vitest; watch mode, add "-- --run" for a single run as CI does)
cd frontend && npm test

# Browser extension (Node's built-in test runner, no dependencies to install)
cd BookmarkExtension && npm test

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
docker run -d --name fuze-test-pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=fuze_test \
  -p 55432:5432 pgvector/pgvector:pg15
TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/fuze_test pytest
```

**Test Files:** `backend/tests/` holds one `test_*.py` module per area. The main groups:
- Auth and sessions: `test_auth.py`, `test_auth_refresh_flow.py`, `test_auth_fork_session.py`,
  `test_session_lifecycle.py`, `test_oauth_account_linking.py` (Google sign-in never joins
  an account by email), `test_account.py` (export and deletion)
- Bookmarks and pipeline: `test_bookmarks.py`, `test_bookmark_lookup.py`,
  `test_pipeline_recovery.py`, `test_pipeline_journeys.py`, `test_content_acquisition_engine.py`,
  `test_safe_http.py` (SSRF-safe fetching)
- Projects and tasks: `test_projects.py`, `test_tasks.py`
- Recommendations, search and ask: `test_recommendations.py`, `test_intent_engine.py`,
  `test_feedback.py`, `test_feedback_project.py`, `test_search.py`, `test_ask.py`
- Infrastructure: `test_rate_limiting.py`, `test_redis_utils.py`, `test_events.py`,
  `test_live_events.py`, `test_run_production.py`, `test_schema_version.py`
- `test_tenant_isolation.py` - one user cannot read or change another user's data
- `test_integration.py` - end-to-end API flows
- `test_postgres_concurrency.py` - concurrent saves and refreshes (skipped unless the
  suite runs on Postgres)
- `conftest.py` - fixtures (`app`, `client`, `test_user`, `auth_headers`, `login_headers`)

Markers (`unit`, `integration`, `slow`, `requires_db`, `requires_redis`, `requires_ml`) are
declared in `backend/pytest.ini` with `--strict-markers`; select with `pytest -m unit`.
Few tests carry a marker, so `-m` is not a way to run the whole suite in parts.

**Key Features:**
- In-memory SQLite by default; `TEST_DATABASE_URL` runs the same suite on a local
  Postgres + pgvector. `conftest.py` refuses any database that isn't SQLite or on
  localhost, so the suite can never touch production
- `APP_ENV=testing` is forced (unset would mean production)
- `DATABASE_URL`, `REDIS_URL` and `SENTRY_DSN` from a local `.env` are overridden before
  anything is imported, so the suite cannot reach production services. Redis defaults to
  `redis://127.0.0.1:6379/15` (`TEST_REDIS_URL` overrides); `test_live_events.py` uses
  `LIVE_REDIS_URL` (default `redis://localhost:56379/14`)
- No real LLM is reachable: the `LLM_*` variables are forced to empty/`gemini`, and the
  reader and archive acquisition tiers are switched off
- Rate limiting is off except in tests that enable it
- JWT fixtures mint tokens directly (`auth_headers`); bcrypt runs at 4 rounds for speed
- The `app` fixture runs `create_all()` at session start and `drop_all()` at the end, so
  `TEST_DATABASE_URL` must name a database used only for tests

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

**Test Files:** `frontend/src/tests/` mirrors the source tree:
- `pages/` - `Login.test.jsx`, `Dashboard.test.jsx`, `DashboardRealtime.test.jsx`
- `components/` - `AccountData.test.jsx`, `AskBookmarks.test.jsx`, `Button.test.jsx`,
  `ProtectedRoute.test.jsx`
- `contexts/` - `AuthContext.test.jsx`
- `hooks/` - `useErrorHandler.test.jsx`
- `services/` - `apiErrors.test.js`, `oauth.test.js`, `tokenRefresh.test.js`
- `utils/` - `feedbackContext.test.js`, `urlSafety.test.js`
- `setup.js` - global setup (jest-dom matchers, `matchMedia`, `innerWidth` and
  `localStorage` mocks, cleanup after each test)

**Key Features:**
- Vitest (jsdom) + React Testing Library
- Mocked API calls
- localStorage mocking
- BrowserRouter/MemoryRouter support

## Extension Tests

**Location:** `BookmarkExtension/tests/` (the extension is a git submodule)

```bash
cd BookmarkExtension
npm test        # node --test; Node 20 or newer, no dependencies
```

The 52 tests cover `auth`, `capture`, `config`, `fuze-bridge`, `manifest`, `messaging` and
the dev-build script (`build-dev`). Extension CI (`.github/workflows/extension-ci.yml`)
runs them and checks that the committed extension zip was built from the pinned commit.

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
tests (`npm test -- --run`), and on a broken production build.

**Extension CI** (`.github/workflows/extension-ci.yml`): Node 20, `npm test` in
`BookmarkExtension`, then `scripts/build_extension_zip.py --check`.

All actions are pinned to commit SHAs and workflows get a read-only token by default.

## Test Structure

### Backend Test Example
```python
def test_login_success(client, test_user):
    response = client.post('/api/auth/login', json={
        'email': test_user['email'],
        'password': test_user['password']
    })
    assert response.status_code == 200
    assert 'access_token' in response.json
```

### Frontend Test Example
```javascript
test('renders the login form', () => {
  render(<BrowserRouter><ToastProvider><AuthProvider><Login /></AuthProvider></ToastProvider></BrowserRouter>)
  expect(screen.getByPlaceholderText(/email/i)).toBeInTheDocument()
})
```

## Coverage Goals

- **Backend:** CI fails under 74% total coverage (the floor sits a few points under the measured total)
- **Frontend:** no coverage threshold is configured; `npm run test:coverage` prints a report
- **Smoke test:** the critical user journeys over HTTP

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
- Rate limiting: disabled by the `app` fixture unless a test enables it
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

# Extension
node --test --test-reporter=spec
```
