/**
 * E2E tests for authentication flows
 */
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  // Helper to wait for API response and check status
  const waitForApiResponse = async (page, urlPattern) => {
    try {
      const response = await page.waitForResponse(
        (response) => response.url().includes(urlPattern),
        { timeout: 30000 } // Increased timeout
      );
      const status = response.status();
      const body = await response.json().catch(() => ({}));
      
      // Log for debugging
      console.log(`API Response [${urlPattern}]: Status ${status}`, body);
      
      if (status >= 400) {
        throw new Error(`API returned error ${status}: ${JSON.stringify(body)}`);
      }
      
      return { response, status, body };
    } catch (error) {
      console.error(`API call failed for ${urlPattern}:`, error);
      // Log all network requests for debugging
      const requests = await page.evaluate(() => {
        return Array.from(window.performance.getEntriesByType('resource'))
          .filter(r => r.name.includes('/api/'))
          .map(r => ({ url: r.name, type: r.initiatorType }));
      }).catch(() => []);
      console.log('Network requests:', requests);
      throw error;
    }
  };

  test('user can register and login', async ({ page }) => {
    // Listen to console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('Browser console error:', msg.text());
      }
    });
    
    // Listen to all requests for debugging
    page.on('request', request => {
      if (request.url().includes('/api/auth/')) {
        console.log(`API Request: ${request.method()} ${request.url()}`);
      }
    });
    
    // Listen to failed requests
    page.on('response', response => {
      if (response.url().includes('/api/auth/')) {
        console.log(`API Response: ${response.status()} ${response.url()}`);
      }
    });
    
    await page.goto('/login');
    
    // Wait for page to be fully loaded
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('input[name="email"]', { timeout: 10000 });
    
    // Switch to signup tab - the actual text is "Sign up for free"
    const signUpLink = page.locator('button').filter({ hasText: /sign up for free/i }).first();
    await signUpLink.waitFor({ state: 'visible', timeout: 10000 });
    await signUpLink.click();
    await page.waitForTimeout(1000); // Wait for form switch animation
    
    // Generate unique credentials
    const timestamp = Date.now();
    const testEmail = `e2etest${timestamp}@example.com`;
    const testUsername = `e2etest${timestamp}`;
    
    // Fill registration form - wait for each field to be visible
    await page.waitForSelector('input[name="name"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="name"]', 'E2E Test User');
    
    await page.waitForSelector('input[name="username"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="username"]', testUsername);
    
    await page.waitForSelector('input[name="email"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="email"]', testEmail);
    
    await page.waitForSelector('input[name="password"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="password"]', 'SecurePass123!');
    
    // Wait for confirm password field
    await page.waitForSelector('input[name="confirmPassword"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="confirmPassword"]', 'SecurePass123!');
    
    // Wait for form validation to complete
    await page.waitForTimeout(2000);
    
    // Find submit button - the actual text is "Create Your Account"
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /create your account/i }).first();
    await submitButton.waitFor({ state: 'visible', timeout: 10000 });
    
    // Check if button is enabled
    const isEnabled = await submitButton.isEnabled();
    if (!isEnabled) {
      // Check for validation errors
      const errorText = await page.locator('text=/error|invalid|required/i').first().textContent().catch(() => '');
      throw new Error(`Submit button is disabled. Validation error: ${errorText}`);
    }
    
    // Submit form and wait for API response
    const [apiResponse] = await Promise.all([
      waitForApiResponse(page, '/api/auth/register'),
      submitButton.click(),
    ]);
    
    // Verify API response - registration returns success message (not tokens)
    if (apiResponse.status !== 201 || !apiResponse.body.message) {
      throw new Error(`Invalid API response: ${JSON.stringify(apiResponse.body)}`);
    }
    
    // After registration, frontend navigates to dashboard but user isn't logged in yet
    // So we need to wait and then log in with the credentials we just created
    await page.waitForTimeout(2000); // Wait for navigation attempt
    
    // Check if we're on dashboard or login (ProtectedRoute might redirect)
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      // User was redirected to login, so log in now
      await page.fill('input[name="email"]', testEmail);
      await page.fill('input[name="password"]', 'SecurePass123!');
      const loginButton = page.locator('button[type="submit"]').filter({ hasText: /sign in to fuze/i }).first();
      await loginButton.click();
      await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    } else {
      // Already on dashboard (shouldn't happen but handle it)
      await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    }
    
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('user can login with existing credentials', async ({ page }) => {
    // First create a user by registering (reuse registration logic)
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('input[name="email"]', { timeout: 10000 });
    
    // Switch to signup
    const signUpLink = page.locator('button').filter({ hasText: /sign up for free/i }).first();
    await signUpLink.waitFor({ state: 'visible', timeout: 10000 });
    await signUpLink.click();
    await page.waitForTimeout(1000);
    
    const timestamp = Date.now();
    const testEmail = `logintest${timestamp}@example.com`;
    const testUsername = `logintest${timestamp}`;
    
    await page.waitForSelector('input[name="name"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="name"]', 'Login Test User');
    await page.fill('input[name="username"]', testUsername);
    await page.fill('input[name="email"]', testEmail);
    await page.fill('input[name="password"]', 'SecurePass123!');
    
    await page.waitForSelector('input[name="confirmPassword"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="confirmPassword"]', 'SecurePass123!');
    await page.waitForTimeout(2000);
    
    const registerButton = page.locator('button[type="submit"]').filter({ hasText: /create your account/i }).first();
    await registerButton.waitFor({ state: 'visible', timeout: 10000 });
    
    const [registerResponse] = await Promise.all([
      waitForApiResponse(page, '/api/auth/register'),
      registerButton.click(),
    ]);
    
    // Registration returns success message, not tokens
    if (registerResponse.status !== 201 || !registerResponse.body.message) {
      throw new Error(`Registration failed: ${JSON.stringify(registerResponse.body)}`);
    }
    
    // After registration, frontend navigates but user needs to log in
    await page.waitForTimeout(2000);
    
    // If redirected to login, log in with the credentials we just created
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      await page.fill('input[name="email"]', testEmail);
      await page.fill('input[name="password"]', 'SecurePass123!');
      const loginButton = page.locator('button[type="submit"]').filter({ hasText: /sign in to fuze/i }).first();
      await loginButton.click();
    }
    
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    
    // Clear auth manually (more reliable than finding logout button)
    await page.evaluate(() => {
      localStorage.removeItem('token');
      window.location.href = '/login';
    });
    await page.waitForURL(/\/login/, { timeout: 10000 });
    await page.waitForLoadState('domcontentloaded');
    
    // Now login with the created account
    await page.waitForSelector('input[name="email"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="email"]', testEmail);
    await page.fill('input[name="password"]', 'SecurePass123!');
    await page.waitForTimeout(500);
    
    const loginButton = page.locator('button[type="submit"]').filter({ hasText: /sign in to fuze/i }).first();
    await loginButton.waitFor({ state: 'visible', timeout: 10000 });
    
    const [loginResponse] = await Promise.all([
      waitForApiResponse(page, '/api/auth/login'),
      loginButton.click(),
    ]);
    
    if (!loginResponse.body.access_token) {
      throw new Error(`Login failed: ${JSON.stringify(loginResponse.body)}`);
    }
    
    // Wait for navigation
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('user sees error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('input[name="email"]', { state: 'visible', timeout: 10000 });
    
    await page.fill('input[name="email"]', 'wrong@example.com');
    await page.fill('input[name="password"]', 'wrongpassword123!');
    await page.waitForTimeout(500);
    
    // Submit form and wait for API response (should be 401)
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /sign in to fuze/i }).first();
    await submitButton.waitFor({ state: 'visible', timeout: 10000 });
    
    // Wait for the API call - it should return an error
    const response = await page.waitForResponse(
      (response) => response.url().includes('/api/auth/login'),
      { timeout: 20000 }
    );
    
    const status = response.status();
    const body = await response.json().catch(() => ({}));
    
    // Should be 401 or 400 for invalid credentials
    if (status < 400) {
      throw new Error(`Expected error status but got ${status}: ${JSON.stringify(body)}`);
    }
    
    // Wait for error message to appear
    const errorSelectors = [
      'text=/invalid|error|incorrect|wrong|failed|unauthorized|credentials|incorrect/i',
      '[role="alert"]',
      '.error',
      '.error-message',
      '[class*="error"]',
      'text=/login failed|authentication failed/i',
    ];
    
    let errorFound = false;
    for (const selector of errorSelectors) {
      try {
        const errorElement = page.locator(selector).first();
        await errorElement.waitFor({ state: 'visible', timeout: 10000 });
        errorFound = true;
        break;
      } catch {
        // Try next selector
      }
    }
    
    if (!errorFound) {
      // Get page content for debugging
      const visibleText = await page.locator('body').textContent();
      throw new Error(`Error message not found. Status: ${status}, Response: ${JSON.stringify(body)}, Page text: ${visibleText?.substring(0, 500)}`);
    }
    
    // Verify we're still on login page
    await expect(page).toHaveURL(/\/login/);
  });
});

