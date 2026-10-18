import { expect, type Page, type Route, type Request } from '@playwright/test'

export type ApiStub =
  | {
      method: string
      path: string | RegExp
      status?: number
      json?: unknown
      headers?: Record<string, string>
    }
  | {
      method: string
      path: string | RegExp
      handler: (route: Route, request: Request, url: URL) => Promise<void>
    }

function isLocalHttp(url: URL): boolean {
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return false
  return url.hostname === '127.0.0.1' || url.hostname === 'localhost'
}

function matchStub(stub: ApiStub, method: string, pathname: string): boolean {
  if (stub.method.toUpperCase() !== method.toUpperCase()) return false
  if (typeof stub.path === 'string') return stub.path === pathname
  return stub.path.test(pathname)
}

// Endpoints the shell polls on every page. A test's own stub for the same
// method + path wins, because stubs.find() returns the first match.
const DEFAULT_STUBS: ApiStub[] = [
  { method: 'GET', path: '/api/crew/panic', json: { paused: [] } },
  { method: 'GET', path: '/api/ops/dlq/stats', json: {} },
  { method: 'GET', path: '/api/ops/dlq', json: { items: [] } },
  { method: 'GET', path: '/api/v1/orchestrator/system/health', json: {} },
]

export async function installDeterministicRouting(page: Page, testStubs: ApiStub[]) {
  const stubs = [...testStubs, ...DEFAULT_STUBS]
  const unhandledApi: string[] = []

  await page.route('**/*', async (route) => {
    const raw = route.request().url()
    let url: URL | null = null
    try {
      url = new URL(raw)
    } catch {
      url = null
    }

    if (url && (url.protocol === 'http:' || url.protocol === 'https:') && !isLocalHttp(url)) {
      return route.abort()
    }

    return route.fallback()
  })

  await page.route('**/api/**', async (route, request) => {
    const url = new URL(request.url())
    const method = request.method().toUpperCase()
    const pathname = url.pathname

    const stub = stubs.find((s) => matchStub(s, method, pathname))
    if (!stub) {
      unhandledApi.push(`${method} ${pathname}`)
      return route.fulfill({
        status: 501,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Unhandled API call in E2E (add stub)',
          request: { method, pathname },
        }),
      })
    }

    if ('handler' in stub) return stub.handler(route, request, url)

    return route.fulfill({
      status: stub.status ?? 200,
      contentType: 'application/json',
      headers: stub.headers,
      body: JSON.stringify(stub.json ?? {}),
    })
  })

  return {
    assertNoUnhandledApi: () => {
      expect(
        unhandledApi,
        `Unhandled /api/* calls detected:\n${unhandledApi.map((x) => `- ${x}`).join('\n')}`,
      ).toEqual([])
    },
  }
}

export async function seedLocalStorage(page: Page, seed?: { token?: string; projectId?: number }) {
  const token = seed?.token ?? 'e2e-token'
  const projectId = seed?.projectId ?? 1
  await page.addInitScript(([t, pid]) => {
    localStorage.setItem('token', t)
    localStorage.setItem('project_id', String(pid))
  }, [token, projectId])
}

