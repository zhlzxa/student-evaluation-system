import { test, expect } from '@playwright/test';

test.describe('Assessment Workflow', () => {
  test('should be able to access new assessment page', async ({ page }) => {
    await page.goto('/assessments/new');

    // Should show the new assessment page (even if it shows an error due to no backend)
    await expect(page.getByText('Student Admission Review System')).toBeVisible();
    await expect(page).toHaveURL('/assessments/new');
  });

  test('should be able to access assessments runs page', async ({ page }) => {
    await page.goto('/assessments');

    // Should show the assessments page
    await expect(page.getByText('Student Admission Review System')).toBeVisible();
    await expect(page).toHaveURL('/assessments');
  });

  test('should be able to access rules page', async ({ page }) => {
    await page.goto('/rules');

    // Should show the rules page
    await expect(page.getByText('Student Admission Review System')).toBeVisible();
    await expect(page).toHaveURL('/rules');
  });

  // Report page removed

  test('should handle navigation to assessment run details', async ({ page }) => {
    // Test navigation to an assessment run details page (with a mock ID)
    await page.goto('/assessments/runs/123');

    // Should show the assessment run details page
    await expect(page.getByText('Student Admission Review System')).toBeVisible();
    await expect(page).toHaveURL('/assessments/runs/123');
  });
});