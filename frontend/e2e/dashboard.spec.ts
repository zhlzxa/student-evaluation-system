import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('should display dashboard title and navigation', async ({ page }) => {
    await page.goto('/');

    // Check if the main title is visible
    await expect(page.getByText('Student Evaluation System')).toBeVisible();
    await expect(page.getByText('Dashboard')).toBeVisible();
  });

  test('should open navigation drawer when menu button is clicked', async ({ page }) => {
    await page.goto('/');

    // Click the menu button
    await page.getByTestId('MenuIcon').click();

    // Check if navigation items are visible
    await expect(page.getByText('Dashboard')).toBeVisible();
    await expect(page.getByText('New Assessment')).toBeVisible();
    await expect(page.getByText('Runs')).toBeVisible();
    await expect(page.getByText('Rules')).toBeVisible();
  });

  test('should navigate to new assessment page', async ({ page }) => {
    await page.goto('/');

    // Open navigation
    await page.getByTestId('MenuIcon').click();
    
    // Click on New Assessment
    await page.getByText('New Assessment').click();

    // Should navigate to the new assessment page
    await expect(page).toHaveURL('/assessments/new');
  });

  test('should display quick actions and recent runs cards', async ({ page }) => {
    await page.goto('/');

    // Check for quick actions card
    await expect(page.getByText('Quick Actions')).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Assessment' })).toBeVisible();

    // Check for recent runs card
    await expect(page.getByText('Recent Runs')).toBeVisible();
    await expect(page.getByText(/Count:/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'View all' })).toBeVisible();
  });

  test('should navigate to assessments page from view all button', async ({ page }) => {
    await page.goto('/');

    // Click the view all button
    await page.getByRole('button', { name: 'View all' }).click();

    // Should navigate to the assessments page
    await expect(page).toHaveURL('/assessments');
  });
});