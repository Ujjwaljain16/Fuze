import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: './tests',
  // In CI, run tests sequentially to avoid rate limiting
  // Locally, run in parallel for faster feedback
  fullyParallel: !process.env.CI,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // In CI: 1 worker = sequential execution (prevents rate limiting)
  // Locally: undefined = use all CPU cores for parallel execution
  workers: process.env.CI ? 1 : undefined,
  // In CI, run projects (browsers) sequentially too
  maxFailures: process.env.CI ? 10 : undefined,
  reporter: 'html',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: [
    {
      command: 'npm run dev',
      cwd: path.join(__dirname, '..', 'frontend'),
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
    },
    {
      command: process.platform === 'win32' ? 'python run_production.py' : 'python3 run_production.py',
      cwd: path.join(__dirname, '..', 'backend'),
      url: 'http://127.0.0.1:5000/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});

