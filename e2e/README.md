# E2E Tests with Playwright

## Running Tests

### Locally (Parallel - Fast)
```bash
cd e2e
npm test
```

### In CI (Sequential - Prevents Rate Limiting)
Tests automatically run sequentially when `CI=true` environment variable is set.

**Linux/Mac (Bash):**
```bash
# Set CI environment variable
export CI=true
npm test

# Or run directly with CI flag
CI=true npm test
```

**Windows (PowerShell):**
```powershell
# Set CI environment variable for current session
$env:CI = "true"
npm test

# Or run in one line
$env:CI = "true"; npm test

# Or use the npm script (if cross-env is installed)
npm run test:ci
```

**Windows (Command Prompt):**
```cmd
set CI=true
npm test

# Or use the npm script (if cross-env is installed)
npm run test:ci
```

## Configuration

The Playwright config (`playwright.config.js`) is configured to:
- **Locally**: Run tests in parallel across all CPU cores for faster feedback
- **In CI**: Run tests sequentially (1 worker) to prevent rate limiting issues

### Key Settings:
- `fullyParallel: !process.env.CI` - Parallel locally, sequential in CI
- `workers: process.env.CI ? 1 : undefined` - 1 worker in CI, all cores locally
- Projects (browsers) run sequentially in CI to avoid overwhelming the backend

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/e2e.yml`:

```yaml
name: E2E Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: e2e/package-lock.json
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install Node dependencies
        working-directory: e2e
        run: npm ci
      
      - name: Install Python dependencies
        working-directory: backend
        run: |
          pip install -r requirements.txt
      
      - name: Install Playwright browsers
        working-directory: e2e
        run: npx playwright install --with-deps
      
      - name: Run E2E tests
        working-directory: e2e
        env:
          CI: true  # This triggers sequential execution
        run: npm test
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: e2e/playwright-report/
          retention-days: 30
```

### Other CI Platforms

For other CI platforms, set the `CI` environment variable:

**GitLab CI** (`.gitlab-ci.yml`):
```yaml
e2e-tests:
  script:
    - cd e2e
    - CI=true npm test
```

**Jenkins**:
```groovy
stage('E2E Tests') {
    steps {
        sh 'cd e2e && CI=true npm test'
    }
}
```

**CircleCI** (`.circleci/config.yml`):
```yaml
jobs:
  e2e-tests:
    steps:
      - run:
          name: Run E2E tests
          command: |
            cd e2e
            CI=true npm test
```

**Azure DevOps** (`.azure-pipelines.yml`):
```yaml
steps:
  - script: |
      cd e2e
      npm test
    env:
      CI: 'true'
```

## Rate Limiting

The backend has rate limits to prevent abuse:
- **CSRF Token**: 50 requests per minute
- **Registration**: 5 requests per 15 minutes
- **Login**: 5 requests per 15 minutes

Running tests sequentially in CI prevents hitting these limits. If you still encounter rate limiting:

1. **Increase delays between tests** (not recommended - slows tests)
2. **Disable rate limiting in test environment** (recommended - modify backend config)
3. **Use test-specific rate limits** (best - configure backend to detect test mode)

### Disable Rate Limiting for Tests

In `backend/blueprints/auth.py`, you can add:

```python
import os

# In register/login functions, check for test mode
if os.getenv('TESTING') == 'true':
    # Skip rate limiting in test mode
    pass
else:
    apply_rate_limit()
```

Then set `TESTING=true` in your CI environment.

## Debugging

### Run tests in headed mode (see browser):
```bash
npm run test:headed
```

### Run tests with UI mode:
```bash
npm run test:ui
```

### Run specific test file:
```bash
npx playwright test tests/auth.spec.js
```

### Run tests in specific browser:
```bash
npx playwright test --project=chromium
```

## Troubleshooting

### Tests timing out
- Check that both frontend and backend servers are running
- Verify `webServer` configuration in `playwright.config.js`
- Increase timeouts if needed

### Rate limiting errors
- Ensure `CI=true` is set in CI environment
- Check that tests are running sequentially (not parallel)
- Consider disabling rate limits for test environment

### Port conflicts
- Frontend: Default port 5173
- Backend: Default port 5000
- Change ports in config if needed

