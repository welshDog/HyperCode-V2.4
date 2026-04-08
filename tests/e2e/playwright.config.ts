import { defineConfig, devices } from '@playwright/test'
import path from 'path'

const repoRoot = path.resolve(__dirname, '..', '..')

export default defineConfig({
  testDir:   __dirname,
  timeout:   30_000,
  retries:   process.env.CI ? 2 : 0,
  workers:   process.env.CI ? 1 : undefined,
  reporter:  [
    ['list'],
    ['html', { outputFolder: path.join(repoRoot, 'reports', 'e2e-html'), open: 'never' }],
    ['junit', { outputFile: path.join(repoRoot, 'reports', 'e2e-junit.xml') }],
  ],
  use: {
    baseURL:         process.env.DASHBOARD_URL ?? 'http://localhost:8088',
    screenshot:      'only-on-failure',
    video:           'retain-on-failure',
    trace:           'retain-on-failure',
  },
  webServer: process.env.CI
    ? {
        command: 'npm --prefix agents/dashboard run dev -- -p 8088',
        url: 'http://localhost:8088',
        reuseExistingServer: false,
      }
    : undefined,
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
  ],
})
