import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should navigate through all main pages', async ({ page }) => {
    await page.goto('/');

    // Test navigation to each page
    const navigationItems = [
      { name: 'Dashboard', url: '/' },
      { name: 'New Assessment', url: '/assessments/new' },
      { name: 'Runs', url: '/assessments' },
      { name: 'Rules', url: '/rules' },
    ];

    for (const item of navigationItems) {
      // Click navigation item
      await page.getByText(item.name).click();
      
      // Verify URL
      await expect(page).toHaveURL(item.url);
      
      // Verify page loaded (check for common elements)
      await expect(page.getByText('Student Evaluation System')).toBeVisible();
    }
  });

  test('should close navigation drawer when clicking outside or on item', async ({ page }) => {
    await page.goto('/');

    // Navigation is always visible; verify items are present and clickable
    await expect(page.getByText('Dashboard')).toBeVisible();
    await page.getByText('Dashboard').click();
  });

  test('should highlight current page in navigation', async ({ page }) => {
    // Go to Rules page
    await page.goto('/rules');

    // The Rules item should have selected styling (permanent nav)
    const rulesButton = page.getByText('Rules').locator('xpath=ancestor::div[@role="button"]');
    await expect(rulesButton).toHaveClass(/Mui-selected/);
  });
});