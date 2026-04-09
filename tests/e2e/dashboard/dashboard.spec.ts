import { test, expect } from '@playwright/test'
import { installDeterministicRouting, seedLocalStorage } from './_support/apiStubs'

test.describe('HyperCode dashboard e2e', () => {
  test('AppShell renders + sidebar nav works', async ({ page }) => {
    await seedLocalStorage(page)
    const api = await installDeterministicRouting(page, [
      { method: 'GET', path: '/api/metrics', json: {} },
      { method: 'GET', path: '/api/agents', json: { agents: [] } },
      { method: 'GET', path: '/api/tasks', json: { tasks: [] } },
      { method: 'GET', path: '/api/broski', json: { coins: 0 } },
      { method: 'GET', path: '/api/health', json: { healthy: true, timestamp: '2026-01-01T00:00:00Z' } },
      { method: 'GET', path: '/api/orchestrator', json: { status: 'healthy' } },
      { method: 'GET', path: '/api/healer/health', json: { status: 'healthy', timestamp: '2026-01-01T00:00:00Z' } },
    ])

    await page.goto('/')

    await expect(page.locator('.hc-topbar')).toBeVisible()
    await expect(page.locator('.hc-sidebar')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Notification history' })).toBeVisible()

    await page.getByRole('link', { name: 'Health' }).click()
    await expect(page).toHaveURL(/\/health$/)

    await page.getByRole('link', { name: 'Docker Zone' }).click()
    await expect(page).toHaveURL(/\/docker-zone$/)

    api.assertNoUnhandledApi()
  })

  test('Docker Zone page renders native + Send triggers toast', async ({ page }) => {
    await seedLocalStorage(page)
    const api = await installDeterministicRouting(page, [
      {
        method: 'GET',
        path: '/api/agents',
        json: {
          agents: [
            { name: 'devops-engineer', status: 'online' },
            { name: 'coder-agent', status: 'busy' },
          ],
        },
      },
      {
        method: 'POST',
        path: '/api/orchestrator',
        json: { status: 'queued' },
      },
    ])

    await page.goto('/docker-zone')

    const frameEl = page.locator('iframe[title="Docker Command Centre"]')
    await expect(frameEl).toBeVisible()

    const frame = await (await frameEl.elementHandle())?.contentFrame()
    expect(frame).toBeTruthy()

    await expect(frame!.locator('.topbar')).toHaveCount(0)
    await expect(frame!.locator('.sidebar')).toHaveCount(0)

    const sendBtn = frame!.getByRole('button', { name: 'Send' }).first()
    await sendBtn.click()

    await expect(page.locator('.hc-toast-title').filter({ hasText: 'Dispatching to devops-engineer' })).toBeVisible()
    await expect(page.locator('.hc-toast-title').filter({ hasText: 'Orchestrator: queued' })).toBeVisible()

    api.assertNoUnhandledApi()
  })

  test('Create task -> toast + unread badge increments + notification panel works', async ({ page }) => {
    await seedLocalStorage(page)

    const tasks: Array<{ id: number; title: string; description?: string; status: string; progress?: number }> = [
      { id: 1, title: 'Seed task', description: 'hello', status: 'todo', progress: 0 },
    ]

    const api = await installDeterministicRouting(page, [
      { method: 'GET', path: '/api/metrics', json: {} },
      { method: 'GET', path: '/api/agents', json: { agents: [] } },
      {
        method: 'GET',
        path: '/api/tasks',
        handler: async (route) => {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tasks }) })
        },
      },
      {
        method: 'POST',
        path: '/api/tasks',
        handler: async (route, request) => {
          const body = JSON.parse(request.postData() ?? '{}') as { description?: string }
          const title = typeof body.description === 'string' && body.description.trim() ? body.description.trim() : 'New task'
          const created = { id: 2, title, status: 'todo', progress: 0 }
          tasks.unshift(created)
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) })
        },
      },
      { method: 'GET', path: '/api/broski', json: { coins: 0 } },
    ])

    await page.goto('/')
    await expect(page.getByTestId('pane-tasks')).toBeVisible()

    const input = page.getByPlaceholder('New task… (Enter to submit)')
    await input.fill('Write Playwright tests')
    await input.press('Enter')

    await expect(page.locator('.hc-toast-title').filter({ hasText: 'Task created' })).toBeVisible()
    await expect(page.locator('.hc-notify-badge')).toBeVisible()

    await page.getByRole('button', { name: 'Notification history' }).click()
    await expect(page.locator('.hc-notify-panel')).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.locator('.hc-notify-panel')).toBeHidden()

    api.assertNoUnhandledApi()
  })

  test('Mobile viewport: no horizontal overflow + chrome present', async ({ page }) => {
    await seedLocalStorage(page)
    const api = await installDeterministicRouting(page, [
      { method: 'GET', path: '/api/metrics', json: {} },
      { method: 'GET', path: '/api/agents', json: { agents: [] } },
      { method: 'GET', path: '/api/tasks', json: { tasks: [] } },
      { method: 'GET', path: '/api/broski', json: { coins: 0 } },
    ])

    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')

    await expect(page.locator('.hc-topbar')).toBeVisible()
    await expect(page.locator('.hc-sidebar')).toBeVisible()

    const ok = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    expect(ok).toBeTruthy()

    api.assertNoUnhandledApi()
  })

  test('Health sweep shows toast sequence', async ({ page }) => {
    await seedLocalStorage(page)
    const api = await installDeterministicRouting(page, [
      { method: 'GET', path: '/api/health', json: { healthy: true, timestamp: '2026-01-01T00:00:00Z' } },
      { method: 'GET', path: '/api/orchestrator', json: { status: 'healthy' } },
      { method: 'GET', path: '/api/healer/health', json: { status: 'healthy', timestamp: '2026-01-01T00:00:00Z' } },
    ])

    await page.goto('/health')
    await page.getByRole('button', { name: '↻ Refresh' }).click()

    await expect(page.locator('.hc-toast-title').filter({ hasText: '⏳ Sweeping health endpoints…' })).toBeVisible()
    await expect(page.locator('.hc-toast-title').filter({ hasText: '✅ Sweep complete' })).toBeVisible()

    api.assertNoUnhandledApi()
  })
})
