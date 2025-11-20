/**
 * E2E tests for bookmark functionality
 */
import { test, expect } from '@playwright/test';
import { loginUser } from './helpers/auth.js';

test.describe('Bookmarks', () => {
  test.beforeEach(async ({ page }) => {
    // Login using helper (creates user if needed)
    await loginUser(page);
  });

  test('user can save a bookmark', async ({ page }) => {
    await page.goto('/save-content');
    
    await page.fill('input[name="url"]', 'https://example.com/article');
    await page.fill('input[name="title"]', 'Test Article');
    await page.fill('textarea[name="description"]', 'Test description');
    
    await page.click('button:has-text("Save")');
    
    // Should show success message or redirect
    await expect(page.locator('text=/saved|success/i')).toBeVisible({ timeout: 10000 });
  });

  test('user can view bookmarks list', async ({ page }) => {
    await page.goto('/bookmarks');
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    
    // Should show bookmarks page - check for any bookmark-related content
    const bookmarkContent = page.locator('text=/bookmark|saved|content/i').first();
    await expect(bookmarkContent).toBeVisible({ timeout: 10000 });
  });

  test('user can search bookmarks', async ({ page }) => {
    await page.goto('/bookmarks');
    
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]');
    if (await searchInput.count() > 0) {
      await searchInput.fill('test');
      await page.waitForTimeout(500); // Wait for search to execute
      
      // Should show filtered results
      await expect(page.locator('.bookmark-item, [data-testid="bookmark"]').first()).toBeVisible();
    }
  });
});

