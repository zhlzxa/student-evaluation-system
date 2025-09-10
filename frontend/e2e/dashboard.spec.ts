import { test, expect } from '@playwright/test';

test.describe('Home/Assessments', () => {
  test('should display app title and navigation', async ({ page }) => {
    await page.goto('/');

    // Check if the main title is visible
    await expect(page.getByText('Student Evaluation System')).toBeVisible();
    await expect(page.getByText('Home')).toBeVisible();
  });

  test('should show navigation permanently', async ({ page }) => {
    await page.goto('/');

    // Navigation items are visible without clicking any menu
    await expect(page.getByText('Home')).toBeVisible();
    await expect(page.getByText('New Assessment')).toBeVisible();
    await expect(page.getByText('Runs')).toBeVisible();
    await expect(page.getByText('Rules')).toBeVisible();
  });

  test('should navigate to new assessment page', async ({ page }) => {
    await page.goto('/');
    
    // Click on New Assessment
    await page.getByText('New Assessment').click();

    // Should navigate to the new assessment page
    await expect(page).toHaveURL('/assessments/new');
  });

  test('should display assessments list page content', async ({ page }) => {
    await page.goto('/');

    // Should land on assessments page via redirect and see list elements
    await expect(page).toHaveURL('/assessments');
    await expect(page.getByText('Admission Reviews')).toBeVisible();
  });

  test('should navigate to assessments page from Home', async ({ page }) => {
    await page.goto('/');

    // Should already be redirected to /assessments
    await expect(page).toHaveURL('/assessments');
  });
});