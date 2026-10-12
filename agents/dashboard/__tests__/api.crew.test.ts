// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'
import { GET } from '../app/api/crew/[taskId]/events/route'

const call = (taskId: string, query = '') =>
  GET(new NextRequest(`http://localhost/api/crew/${taskId}/events${query}`), { params: Promise.resolve({ taskId }) })

describe('GET /api/crew/[taskId]/events', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  it('forwards to core and passes the payload through', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ taskId: 't1', events: [] }) })
    vi.stubGlobal('fetch', fetchMock)
    const res = await call('t1', '?after=4')
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual({ taskId: 't1', events: [] })
    expect(fetchMock.mock.calls[0][0]).toBe('http://hypercode-core:8000/api/v1/operator/tasks/t1/events?after=4')
    expect(fetchMock.mock.calls[0][1].method).toBeUndefined() // a plain GET
  })

  it('defaults after to -1', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) })
    vi.stubGlobal('fetch', fetchMock)
    await call('t1')
    expect(fetchMock.mock.calls[0][0]).toMatch(/events\?after=-1$/)
  })

  it.each(['../etc/passwd', 'a b', 'x'.repeat(65), 'a/b', 'a%2Fb'])('rejects a bad task id %s before any request', async (id) => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    expect((await call(id)).status).toBe(400)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it.each(['?after=-2', '?after=abc', '?after=1.5x', '?after=', '?after=99999999999'])('rejects a bad after %s', async (q) => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    expect((await call('t1', q)).status).toBe(400)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('passes a 404 through and hides every other upstream failure as 502', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }))
    expect((await call('t1')).status).toBe(404)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'secret detail' }) }))
    const res = await call('t1')
    expect(res.status).toBe(502)
    expect(JSON.stringify(await res.json())).not.toContain('secret detail')
  })

  it('returns 502 when core is unreachable, without leaking the error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('connect ECONNREFUSED 10.0.0.5:8000')))
    const res = await call('t1')
    expect(res.status).toBe(502)
    expect(JSON.stringify(await res.json())).not.toContain('10.0.0.5')
  })

  it('exports GET only (approving is not exposed here)', async () => {
    const mod = await import('../app/api/crew/[taskId]/events/route')
    expect(Object.keys(mod).filter((k) => /^(GET|POST|PUT|PATCH|DELETE)$/.test(k))).toEqual(['GET'])
  })
})
