import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'

const port = Number(process.env.DASHBOARD_PORT ?? 3010)
const baseURL = process.env.DASHBOARD_URL ?? `http://127.0.0.1:${port}`

export default defineConfig({
  testDir: path.join(__dirname, 'tests', 'e2e', 'dashboard'),
  fullyParallel: true,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    locale: 'en-GB',
    timezoneId: 'UTC',
    colorScheme: 'dark',
    reducedMotion: 'reduce',
  },
  webServer: process.env.DASHBOARD_URL
    ? undefined
    : {
        command: `node "${path.join(__dirname, 'scripts', 'e2e', 'start-dashboard.mjs')}"`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        env: {
          ...process.env,
          DASHBOARD_PORT: String(port),
        },
      },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})

