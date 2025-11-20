/**
 * E2E tests for recommendations functionality
 */
import { test, expect } from '@playwright/test';
import { loginUser } from './helpers/auth.js';

test.describe('Recommendations', () => {
  test.beforeEach(async ({ page }) => {
    // Login using helper (creates user if needed)
    await loginUser(page);
  });

  test('user can view recommendations', async ({ page }) => {
    await page.goto('/recommendations');
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    
    // Should show recommendations page - check for any recommendation-related content
    const recommendationContent = page.locator('text=/recommendation|suggest|learn/i').first();
    await expect(recommendationContent).toBeVisible({ timeout: 10000 });
  });

  test('user can request recommendations for a project', async ({ page }) => {
    await page.goto('/recommendations');
    
    // Fill recommendation form
    const titleInput = page.locator('input[name="title"], input[placeholder*="project" i]');
    if (await titleInput.count() > 0) {
      await titleInput.fill('Learn Python');
      
      const techInput = page.locator('input[name="technologies"], input[placeholder*="technolog" i]');
      if (await techInput.count() > 0) {
        await techInput.fill('Python, Flask');
      }
      
      // Submit form
      const submitButton = page.locator('button:has-text("Get"), button:has-text("Recommend")');
      if (await submitButton.count() > 0) {
        await submitButton.click();
        
        // Wait for recommendations to load
        await page.waitForTimeout(3000);
        
        // Should show recommendations
        await expect(page.locator('.recommendation, [data-testid="recommendation"]').first()).toBeVisible({ timeout: 10000 });
      }
    }
  });
});

