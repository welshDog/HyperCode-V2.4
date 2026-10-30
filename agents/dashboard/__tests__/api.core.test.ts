// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'
import { evaluateCoreRequest } from '../lib/coreProxyPolicy'

vi.mock('../lib/server-auth', () => ({ serviceAuthHeader: () => 'Bearer service-jwt' }))

import { GET, POST, HEAD } from '../app/api/core/[...path]/route'

const url = (p: string) => `http://localhost/api/core/${p}`
const ctx = (p: string) => ({ params: Promise.resolve({ path: p.split('/') }) })
const okFetch = () => vi.fn().mockResolvedValue(new Response('{"ok":true}', { status: 200, headers: { 'content-type': 'application/json' } }))
const sentAuth = (f: ReturnType<typeof vi.fn>) => (f.mock.calls[0][1].headers as Headers).get('authorization')

describe('evaluateCoreRequest', () => {
  it.each([
    ['GET', 'agents/status'],
    ['GET', 'tasks'],
    ['GET', 'tasks/42'],
    ['GET', 'flows/runs/abc-123/events'],
    ['GET', 'api/v1/orchestrator/agents'],
    ['HEAD', 'logs'],
    ['POST', 'execute'],
    ['POST', 'auth/login/access-token'],
  ])('allows %s %s', (m, p) => {
    expect(evaluateCoreRequest(m, p.split('/')).allowed).toBe(true)
  })

  it.each([
    'users/me', 'admin/secrets', 'governance/ledger', 'operator/panic', 'tasks/1/cancel', 'flows/runs/a/b/events',
  ])('hides unlisted path %s', (p) => {
    expect(evaluateCoreRequest('GET', p.split('/'))).toEqual({ allowed: false, reason: 'path' })
  })

  it.each([['..', 'agents', 'status'], ['agents', '..', 'status'], ['.'], [''], ['tasks', 'a%2Fb'], ['tasks', 'a\b'], []])(
    'rejects unsafe segments %j',
    (...segs) => {
      expect(evaluateCoreRequest('GET', segs).allowed).toBe(false)
    },
  )

  it.each(['PUT', 'PATCH', 'DELETE'])('rejects %s on a listed path', (m) => {
    expect(evaluateCoreRequest(m, ['tasks'])).toEqual({ allowed: false, reason: 'method' })
  })

  it('refuses a write on a read-only path and a read on a write-only path', () => {
    expect(evaluateCoreRequest('POST', ['agents', 'status'])).toEqual({ allowed: false, reason: 'method' })
    expect(evaluateCoreRequest('GET', ['execute'])).toEqual({ allowed: false, reason: 'method' })
  })

  it('uses the service identity for reads only, and the caller for writes', () => {
    expect(evaluateCoreRequest('GET', ['tasks'])).toMatchObject({ useServiceAuth: true, requireCallerAuth: false })
    expect(evaluateCoreRequest('POST', ['execute'])).toMatchObject({ useServiceAuth: false, requireCallerAuth: true })
    expect(evaluateCoreRequest('POST', ['auth', 'login', 'access-token'])).toMatchObject({ useServiceAuth: false, requireCallerAuth: false })
  })
})

describe('/api/core proxy', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('forwards an allowed read with the service JWT', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    const res = await GET(new NextRequest(url('api/v1/agents/status?x=1')), ctx('api/v1/agents/status'))
    expect(res.status).toBe(200)
    expect(String(f.mock.calls[0][0])).toBe('http://hypercode-core:8000/api/v1/agents/status?x=1')
    expect(sentAuth(f)).toBe('Bearer service-jwt')
  })

  it('prefers the caller token over the service JWT on a read', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    await GET(new NextRequest(url('tasks'), { headers: { authorization: 'Bearer user-jwt' } }), ctx('tasks'))
    expect(sentAuth(f)).toBe('Bearer user-jwt')
  })

  it('does not forward a write without a caller token (401, no upstream call)', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    const res = await POST(new NextRequest(url('execute'), { method: 'POST', body: '{}' }), ctx('execute'))
    expect(res.status).toBe(401)
    expect(f).not.toHaveBeenCalled()
  })

  it('forwards a write that carries the caller token, never the service JWT', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    const res = await POST(
      new NextRequest(url('execute'), { method: 'POST', body: '{"a":1}', headers: { authorization: 'Bearer user-jwt', 'content-type': 'application/json' } }),
      ctx('execute'),
    )
    expect(res.status).toBe(200)
    expect(sentAuth(f)).toBe('Bearer user-jwt')
    expect(f.mock.calls[0][1].body).toBe('{"a":1}')
  })

  it('lets login through without any token and without the service JWT', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    await POST(new NextRequest(url('auth/login/access-token'), { method: 'POST', body: 'username=a&password=b' }), ctx('auth/login/access-token'))
    expect(f).toHaveBeenCalledOnce()
    expect(sentAuth(f)).toBeNull()
  })

  it('404s an unlisted path and 405s a wrong method, without calling core', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    expect((await GET(new NextRequest(url('users/me')), ctx('users/me'))).status).toBe(404)
    expect((await POST(new NextRequest(url('agents/status'), { method: 'POST', headers: { authorization: 'Bearer u' } }), ctx('agents/status'))).status).toBe(405)
    expect(f).not.toHaveBeenCalled()
  })

  it('answers HEAD like GET (service identity allowed)', async () => {
    const f = okFetch()
    vi.stubGlobal('fetch', f)
    await HEAD(new NextRequest(url('logs'), { method: 'HEAD' }), ctx('logs'))
    expect(sentAuth(f)).toBe('Bearer service-jwt')
  })

  it('returns 502 when core is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    const res = await GET(new NextRequest(url('logs')), ctx('logs'))
    expect(res.status).toBe(502)
  })
})
