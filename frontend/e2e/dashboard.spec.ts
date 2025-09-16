import { test, expect } from '@playwright/test';

test.describe('Home/Assessments', () => {
  test('should display app title and navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/assessments');

    // Check if the assessments title is visible
    await expect(page.getByRole('heading', { level: 1, name: 'Admission Reviews' })).toBeVisible();
  });

  test('should show navigation permanently', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/assessments');

    // Verify key UI elements indicate the shell is present
    await expect(page.getByRole('button', { name: 'Create' })).toBeVisible();
  });

  test('should navigate to new assessment page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForURL('**/assessments');
    
    // Click on Create
    await page.getByRole('button', { name: 'Create' }).click();

    // Should navigate to the new assessment page
    await expect(page).toHaveURL('/assessments/new');
  });

  test('should display assessments list page content', async ({ page }) => {
    await page.goto('/');
    await page.waitForURL('**/assessments');

    // Should land on assessments page via redirect and see list elements
    await expect(page).toHaveURL('/assessments');
    await expect(page.getByRole('heading', { level: 1, name: 'Admission Reviews' })).toBeVisible();
  });

  test('should navigate to assessments page from Home', async ({ page }) => {
    await page.goto('/');

    // Should already be redirected to /assessments
    await expect(page).toHaveURL('/assessments');
  });
});