import { test, expect } from '@playwright/test'

test.describe('HyperShell Full-Screen Layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('[data-testid="hyper-shell"]')
  })

  test('renders full-screen — no scrollbars', async ({ page }) => {
    const overflow = await page.evaluate(() => {
      const b = document.body
      return { x: b.scrollWidth <= b.clientWidth, y: b.scrollHeight <= b.clientHeight }
    })
    expect(overflow.x).toBe(true)
    expect(overflow.y).toBe(true)
  })

  test('all 4 panes are visible', async ({ page }) => {
    await expect(page.getByTestId('pane-agents')).toBeVisible()
    await expect(page.getByTestId('pane-timeline')).toBeVisible()
    await expect(page.getByTestId('pane-metrics')).toBeVisible()
    await expect(page.getByTestId('pane-pulse')).toBeVisible()
  })

  test('focus toggle works', async ({ page }) => {
    const focusBtns = page.getByRole('button', { name: /Focus this pane/i })
    await focusBtns.first().click()
    await expect(page.getByRole('button', { name: /Exit focus mode/i })).toBeVisible()
  })

  test('view mode toggle cycles correctly', async ({ page }) => {
    await page.getByRole('button', { name: /Focus/i }).first().click()
    // after clicking Focus mode, check aria-pressed
    const focusModeBtn = page.getByRole('button', { name: /Focus/i })
    await expect(focusModeBtn.first()).toHaveAttribute('aria-pressed', 'true')
  })
})
