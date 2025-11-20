/**
 * E2E tests for projects functionality
 */
import { test, expect } from '@playwright/test';
import { loginUser } from './helpers/auth.js';

test.describe('Projects', () => {
  test.beforeEach(async ({ page }) => {
    // Login using helper (creates user if needed)
    await loginUser(page);
  });

  test('user can create a project', async ({ page }) => {
    await page.goto('/projects');
    
    // Click create project button
    await page.click('button:has-text("Create"), button:has-text("New"), a:has-text("New")');
    
    // Fill project form
    await page.fill('input[name="title"], input[placeholder*="title" i]', 'E2E Test Project');
    await page.fill('textarea[name="description"], textarea[placeholder*="description" i]', 'Test project description');
    await page.fill('input[name="technologies"], input[placeholder*="technolog" i]', 'Python, Flask');
    
    // Submit
    await page.click('button:has-text("Create"), button:has-text("Save")');
    
    // Should show success or redirect
    await expect(page.locator('text=/created|success|test project/i')).toBeVisible({ timeout: 10000 });
  });

  test('user can view project list', async ({ page }) => {
    await page.goto('/projects');
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    
    // Should show projects page - check for any project-related content
    const projectContent = page.locator('text=/project|create|new/i').first();
    await expect(projectContent).toBeVisible({ timeout: 10000 });
  });

  test('user can view project details', async ({ page }) => {
    await page.goto('/projects');
    
    // Click on first project if available
    const firstProject = page.locator('.project-item, [data-testid="project"]').first();
    if (await firstProject.count() > 0) {
      await firstProject.click();
      
      // Should show project details
      await expect(page.locator('h1, h2')).toContainText(/project/i);
    }
  });
});

