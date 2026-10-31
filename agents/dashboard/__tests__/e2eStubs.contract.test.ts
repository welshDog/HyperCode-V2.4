// @vitest-environment node
// Guards the Playwright E2E mocks against drifting from the dashboard's real API paths.
// This drift left the "Playwright Dashboard E2E" check red for two days (2026-10-28 to 10-30):
// the UI moved to the same-origin proxy (/api/core/...) and the mocks still stubbed core's direct path.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { API_BASE_URL } from '../lib/api'
import { evaluateCoreRequest } from '../lib/coreProxyPolicy'

const E2E_DIR = resolve(__dirname, '..', '..', '..', 'tests', 'e2e')

function tsFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name)
    return statSync(full).isDirectory() ? tsFiles(full) : full.endsWith('.ts') ? [full] : []
  })
}

const stubs = tsFiles(E2E_DIR).flatMap((file) =>
  [...readFileSync(file, 'utf-8').matchAll(/method:\s*'(\w+)',\s*path:\s*'(\/api\/[^']*)'/g)].map((m) => ({
    file: file.slice(E2E_DIR.length + 1).replace(/\\/g, '/'),
    method: m[1],
    path: m[2],
  })),
)

describe('Playwright E2E API mocks stay in step with the dashboard', () => {
  it('finds the E2E stubs (so this guard cannot silently pass on nothing)', () => {
    expect(stubs.length).toBeGreaterThan(5)
  })

  it('mocks the proxy path the UI really requests for system health', () => {
    const wanted = `${API_BASE_URL}/orchestrator/system/health`
    expect(wanted).toBe('/api/core/api/v1/orchestrator/system/health')
    expect(stubs.some((s) => s.method === 'GET' && s.path === wanted)).toBe(true)
  })

  it('no longer stubs core\'s direct path, which the browser never calls', () => {
    expect(stubs.filter((s) => s.path.startsWith('/api/v1/'))).toEqual([])
  })

  it.each(stubs.filter((s) => s.path.startsWith('/api/core/')))(
    '$method $path ($file) is a call the proxy would actually forward',
    ({ method, path }) => {
      const segments = path.slice('/api/core/'.length).split('/')
      expect(evaluateCoreRequest(method, segments).allowed).toBe(true)
    },
  )
})
