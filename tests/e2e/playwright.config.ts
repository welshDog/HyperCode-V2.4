import { defineConfig, devices } from '@playwright/test'
import path from 'path'

const repoRoot = path.resolve(__dirname, '..', '..')
const port = Number(process.env.DASHBOARD_PORT ?? 8088)
const baseURL = process.env.DASHBOARD_URL ?? `http://127.0.0.1:${port}`

export default defineConfig({
  testDir:   __dirname,
  // tests/e2e/dashboard has its own config (repo root) and workflow.
  testIgnore: '**/dashboard/**',
  timeout:   30_000,
  expect:    { timeout: 10_000 },
  retries:   process.env.CI ? 2 : 0,
  workers:   process.env.CI ? 1 : undefined,
  reporter:  [
    ['list'],
    ['html', { outputFolder: path.join(repoRoot, 'reports', 'e2e-html'), open: 'never' }],
    ['junit', { outputFile: path.join(repoRoot, 'reports', 'e2e-junit.xml') }],
  ],
  use: {
    baseURL,
    screenshot:      'only-on-failure',
    video:           'retain-on-failure',
    trace:           'retain-on-failure',
  },
  // CI serves a production build through the same starter the dashboard e2e
  // workflow uses: under "next dev" the pages did not hydrate in the test browser.
  webServer: process.env.CI && !process.env.DASHBOARD_URL
    ? {
        command: `node "${path.join(repoRoot, 'scripts', 'e2e', 'start-dashboard.mjs')}"`,
        url: baseURL,
        // The command's relative paths are repo-root relative.
        cwd: repoRoot,
        // "next build" runs before the server starts.
        timeout: 420_000,
        reuseExistingServer: false,
        env: { ...process.env, DASHBOARD_PORT: String(port) } as Record<string, string>,
      }
    : undefined,
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
