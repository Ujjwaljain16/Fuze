/**
 * Shared authentication helpers for E2E tests
 */
import { expect } from '@playwright/test';

/**
 * Login helper - creates a user if needed and logs in
 */
export async function loginUser(page, email = null, password = 'SecurePass123!') {
  // If no email provided, create a new user
  if (!email) {
    const timestamp = Date.now();
    email = `e2euser${timestamp}@example.com`;
    const username = `e2euser${timestamp}`;
    
    // Register first
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('input[name="email"]', { state: 'visible', timeout: 10000 });
    
    // Switch to signup
    const signUpLink = page.locator('button').filter({ hasText: /sign up for free/i }).first();
    if (await signUpLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await signUpLink.click();
      await page.waitForTimeout(500);
    }
    
    // Fill registration form
    await page.waitForSelector('input[name="name"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="name"]', 'E2E Test User');
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.waitForSelector('input[name="confirmPassword"]', { state: 'visible', timeout: 5000 });
    await page.fill('input[name="confirmPassword"]', password);
    await page.waitForTimeout(1000);
    
    // Submit registration
    const registerButton = page.locator('button[type="submit"]').filter({ hasText: /create your account/i }).first();
    await registerButton.waitFor({ state: 'visible', timeout: 10000 });
    
    // Wait for API response and click button
    const registerResponse = await Promise.all([
      page.waitForResponse(
        (response) => response.url().includes('/api/auth/register'),
        { timeout: 30000 }
      ),
      registerButton.click(),
    ]).then(([response]) => response);
    
    if (registerResponse.status() >= 400) {
      const body = await registerResponse.json().catch(() => ({}));
      throw new Error(`Registration failed: ${registerResponse.status()} - ${JSON.stringify(body)}`);
    }
    
    // Registration returns success message, but no tokens - need to log in
    await page.waitForTimeout(2000);
    
    // Check if we're on login page (ProtectedRoute redirect) and log in
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      await page.fill('input[name="email"]', email);
      await page.fill('input[name="password"]', password);
      const loginButton = page.locator('button[type="submit"]').filter({ hasText: /sign in to fuze/i }).first();
      await loginButton.waitFor({ state: 'visible', timeout: 10000 });
      
      const loginResponse = await Promise.all([
        page.waitForResponse(
          (response) => response.url().includes('/api/auth/login'),
          { timeout: 30000 }
        ),
        loginButton.click(),
      ]).then(([response]) => response);
      
      if (loginResponse.status() >= 400) {
        const body = await loginResponse.json().catch(() => ({}));
        throw new Error(`Login after registration failed: ${loginResponse.status()} - ${JSON.stringify(body)}`);
      }
    }
    
    // Wait for dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    return { email, password };
  } else {
    // Just login with existing credentials
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForSelector('input[name="email"]', { state: 'visible', timeout: 10000 });
    
    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', password);
    await page.waitForTimeout(500);
    
    // Submit login
    const loginButton = page.locator('button[type="submit"]').filter({ hasText: /sign in to fuze/i }).first();
    await loginButton.waitFor({ state: 'visible', timeout: 10000 });
    
    // Wait for API response and click button
    const loginResponse = await Promise.all([
      page.waitForResponse(
        (response) => response.url().includes('/api/auth/login'),
        { timeout: 30000 }
      ),
      loginButton.click(),
    ]).then(([response]) => response);
    
    if (loginResponse.status() >= 400) {
      const body = await loginResponse.json().catch(() => ({}));
      throw new Error(`Login failed: ${loginResponse.status()} - ${JSON.stringify(body)}`);
    }
    
    // Wait for dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 20000 });
    return { email, password };
  }
}

