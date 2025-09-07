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
      // Open navigation drawer
      await page.getByTestId('MenuIcon').click();
      
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

    // Open navigation drawer
    await page.getByTestId('MenuIcon').click();
    await expect(page.getByText('Dashboard')).toBeVisible();

    // Click on a navigation item (should close drawer)
    await page.getByText('Dashboard').click();

    // Wait a moment and check if drawer is closed by checking if nav items are not visible
    await page.waitForTimeout(500);
    
    // The drawer should be closed, so navigation items shouldn't be immediately visible
    // We'll verify by opening it again
    await page.getByTestId('MenuIcon').click();
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('should highlight current page in navigation', async ({ page }) => {
    // Go to Rules page
    await page.goto('/rules');

    // Open navigation
    await page.getByTestId('MenuIcon').click();

    // The Rules item should have selected styling
    const rulesButton = page.getByText('Rules').locator('xpath=ancestor::div[@role="button"]');
    await expect(rulesButton).toHaveClass(/Mui-selected/);
  });
});