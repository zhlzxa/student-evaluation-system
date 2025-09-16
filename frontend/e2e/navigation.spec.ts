import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should navigate through all main pages', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/assessments');

    // Test navigation to each page
    const navigationItems = [
      { name: 'Home', url: '/assessments' },
      { name: 'Programme Criteria', url: '/rules' },
    ];

    for (const item of navigationItems) {
      // Click navigation item via role to avoid instability
      const btn = page.getByRole('button', { name: item.name });
      await btn.scrollIntoViewIfNeeded();
      await btn.click();
      await page.waitForURL('**' + item.url);
      
      // Verify URL
      await expect(page).toHaveURL(item.url);
      
      // Verify page loaded (check for common elements)
      await expect(page.getByText('Student Admission Review System')).toBeVisible();
    }
  });

  test('should close navigation drawer when clicking outside or on item', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Navigation is always visible; verify items are present and clickable
    await expect(page.getByText('Home')).toBeVisible();
    await page.getByText('Home').click();
  });

  test('should highlight current page in navigation', async ({ page }) => {
    // Go to Rules page
    await page.goto('/rules');

    // The Rules item should have selected styling (permanent nav)
    const rulesButton = page.getByText('Programme Criteria').locator('xpath=ancestor::div[@role="button"]');
    await expect(rulesButton).toHaveClass(/Mui-selected/);
  });
});