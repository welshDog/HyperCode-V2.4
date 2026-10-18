import { test, expect } from '@playwright/test'
import { installDeterministicRouting } from './dashboard/_support/apiStubs'

test.describe('HyperShell Full-Screen Layout', () => {
  test.beforeEach(async ({ page }) => {
    await installDeterministicRouting(page, [])
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

  test('all 5 panes are visible', async ({ page }) => {
    await expect(page.getByTestId('pane-metrics')).toBeVisible()
    await expect(page.getByTestId('pane-agents')).toBeVisible()
    await expect(page.getByTestId('pane-services')).toBeVisible()
    await expect(page.getByTestId('pane-tasks')).toBeVisible()
    await expect(page.getByTestId('pane-pulse')).toBeVisible()
  })

  test('focus toggle works', async ({ page }) => {
    const focusBtns = page.getByRole('button', { name: /Focus this pane/i })
    await focusBtns.first().click()
    await expect(page.getByRole('button', { name: /Exit focus mode/i })).toBeVisible()
  })

  test('a focus session can be started and ended', async ({ page }) => {
    // The header's focus control swaps Start focus for End focus (and a timer);
    // it is not an aria-pressed toggle, so assert the visible states.
    await page.getByRole('button', { name: 'Start focus' }).click()
    await expect(page.getByTestId('focus-active')).toBeVisible()
    await page.getByRole('button', { name: 'End focus' }).click()
    await expect(page.getByRole('button', { name: 'Start focus' })).toBeVisible()
  })
})
