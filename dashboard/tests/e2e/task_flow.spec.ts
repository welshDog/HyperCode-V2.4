import { test, expect } from '@playwright/test';

test.describe('Task Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard root
    // Assuming the base URL is configured in playwright.config.ts, otherwise using localhost:3000
    await page.goto('http://localhost:3000/');
  });

  test('should create a new task and verify it appears in the list', async ({ page }) => {
    // 1. Locate the "New Task" button or input area
    // We'll look for a button that likely opens a modal or an input field directly
    const newTaskButton = page.locator('button', { hasText: 'New Task' });
    
    // Check if the button is visible, if so click it
    if (await newTaskButton.isVisible()) {
      await newTaskButton.click();
    }

    // 2. Fill in the task description
    // Targeting common selectors for task inputs
    const taskInput = page.locator('input[placeholder*="task"], input[name="title"], textarea[name="description"]');
    await expect(taskInput).toBeVisible();
    
    const taskDescription = `Test Task ${Date.now()}`;
    await taskInput.fill(taskDescription);

    // 3. Submit the task
    // Looking for a submit button or pressing Enter
    const submitButton = page.locator('button[type="submit"], button:has-text("Add"), button:has-text("Create")');
    
    if (await submitButton.isVisible()) {
      await submitButton.click();
    } else {
      await taskInput.press('Enter');
    }

    // 4. Verify the task appears in the task list
    // We expect the text to be visible in the list container
    const taskItem = page.locator(`text=${taskDescription}`);
    await expect(taskItem).toBeVisible();
  });
});
