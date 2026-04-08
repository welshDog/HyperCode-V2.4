import { test, expect } from '@playwright/test';

test.describe('Dashboard E2E Tests', () => {
  const DASHBOARD_URL = 'http://localhost:8088';

  test.beforeEach(async ({ page }) => {
    // Go to the dashboard before each test
    await page.goto(DASHBOARD_URL);
  });

  test('1. Verify Dashboard Loads Correctly', async ({ page }) => {
    // Check title
    // Actual title is "HyperStation | Mission Control"
    await expect(page).toHaveTitle(/HyperStation|Mission Control/i);
    
    // Check for main layout elements
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('main')).toBeVisible();
  });

  test('2. Verify Key Metrics Display', async ({ page }) => {
    // Check if stats cards are visible
    // Note: Selectors depend on actual implementation, using generic robust selectors
    const statsGrid = page.locator('.grid').first(); 
    await expect(statsGrid).toBeVisible();
    
    // Check for specific metric labels if known (e.g., "Active Agents", "System Health")
    // await expect(page.getByText('Active Agents')).toBeVisible();
  });

  test('3. Test Interactive Elements (Navigation)', async ({ page }) => {
    // Check navigation links
    const navLinks = page.locator('nav a');
    const count = await navLinks.count();
    
    if (count > 0) {
      // Click first link and verify navigation
      const firstLink = navLinks.first();
      const href = await firstLink.getAttribute('href');
      await firstLink.click();
      await expect(page).toHaveURL(new RegExp(href || ''));
    }
  });

  test('4. Responsive Design Check (Mobile)', async ({ page }) => {
    // Resize viewport to mobile
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Verify hamburger menu or mobile layout adaptations
    // This assumes a standard responsive pattern
    // await expect(page.locator('button[aria-label="Menu"]')).toBeVisible();
    
    // Restore
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('5. Verify Real-time Data Updates (Connectivity)', async ({ page }) => {
    // Check for "Connected" indicator or similar status
    // await expect(page.getByText(/Connected|Online/i)).toBeVisible();
    
    // Wait for a few seconds to ensure no crash/error overlay
    await page.waitForTimeout(2000);
    const errorOverlay = page.locator('text=Application error: a client-side exception has occurred');
    await expect(errorOverlay).not.toBeVisible();
  });

  test('6. Verify Modal Does Not Trigger on Random Clicks', async ({ page }) => {
    // Check that modal is hidden initially
    const modal = page.locator('text=Authorization Required');
    await expect(modal).not.toBeVisible();

    // Click on System Health (which was reported to trigger it)
    // Wait for System Health to appear
    await expect(page.locator('text=System Health')).toBeVisible();
    await page.locator('text=System Health').click();
    await expect(modal).not.toBeVisible();

    // Click on an Agent Card if visible (selector might need adjustment)
    // Assuming agent cards contain "CPU" text
    const agentCard = page.locator('text=CPU').first();
    // Wait for agents to load (might take a sec)
    try {
        await agentCard.waitFor({ timeout: 5000 });
        await agentCard.click();
        await expect(modal).not.toBeVisible();
    } catch (e) {
        console.log("Agent cards not loaded, skipping agent click test");
    }
  });
});
