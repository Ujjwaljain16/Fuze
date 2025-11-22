# Testing Guide

Complete testing documentation for Frontend, Backend, and E2E tests.

## Quick Start

```bash
# Backend (Python/Pytest)
cd backend && pytest

# Frontend (Vitest)
cd frontend && npm test

# E2E (Playwright)
cd e2e && npm test
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
```

**Test Files:**
- `test_auth.py` - Authentication (register, login, logout, token refresh)
- `test_bookmarks.py` - Bookmarks CRUD, search, pagination
- `test_projects.py` - Projects CRUD
- `test_recommendations.py` - Recommendation engine
- `test_services.py` - Background services
- `test_integration.py` - End-to-end API flows
- `conftest.py` - Fixtures (app, db, auth_headers)

**Key Features:**
- In-memory SQLite database for tests
- Mocked external services (Redis, Gemini)
- JWT authentication fixtures
- CSRF protection disabled in test mode

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

## E2E Tests

**Location:** `e2e/tests/`

**Run:**
```bash
cd e2e
npm test                  # All tests (parallel locally)
npm run test:ci          # Sequential (prevents rate limiting)
npm run test:ui          # Interactive UI
npm run test:headed      # See browser
npm run test:debug       # Debug mode
```

**Windows PowerShell:**
```powershell
$env:CI = "true"; npm test  # Sequential mode
```

**Test Files:**
- `auth.spec.js` - Registration, login, error handling
- `bookmarks.spec.js` - Bookmark operations
- `projects.spec.js` - Project management
- `recommendations.spec.js` - Recommendation flows
- `helpers/auth.js` - Shared login helper

**Key Features:**
- Cross-browser (Chrome, Firefox, Safari)
- Auto-starts frontend & backend servers
- Sequential execution in CI (prevents rate limiting)
- Automatic user creation for tests

## CI Configuration

**Sequential Execution (CI):**
- Set `CI=true` environment variable
- Tests run with 1 worker (sequential)
- Projects (browsers) run sequentially
- Prevents rate limiting issues

**GitHub Actions:**
```yaml
env:
  CI: true
run: npm test
```

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

### E2E Test Example
```javascript
test('user can login', async ({ page }) => {
  await page.goto('/login')
  await page.fill('input[name="email"]', 'test@example.com')
  await page.fill('input[name="password"]', 'password123')
  await page.click('button:has-text("Sign in")')
  await expect(page).toHaveURL(/\/dashboard/)
})
```

## Coverage Goals

- **Backend:** >80%
- **Frontend:** >70%
- **E2E:** All critical user flows

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
- Rate limiting: Tests disable CSRF protection

**Frontend:**
- localStorage issues: Check `setup.js` mock
- API mocking: Verify `api.get/post` mocks
- Timeouts: Increase `waitFor` timeouts

**E2E:**
- Rate limiting: Use `CI=true` for sequential execution
- Server startup: Check `webServer` config in `playwright.config.js`
- Button not found: Use exact button text ("Sign In to Fuze", "Create Your Account")

## Debugging

```bash
# Backend
pytest --pdb              # Debugger on failure

# Frontend
npm test -- --reporter=verbose

# E2E
npm run test:debug        # Step through
npm run test:headed       # See browser
```

