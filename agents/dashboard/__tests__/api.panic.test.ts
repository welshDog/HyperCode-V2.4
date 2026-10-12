// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as panicRoute from '../app/api/crew/panic/route'
import * as resumeRoute from '../app/api/crew/panic/resume/route'

describe('panic proxies', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('GET and POST go to the fixed core panic path with the right methods', async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ saved: true }) })
    vi.stubGlobal('fetch', f)
    expect((await panicRoute.GET()).status).toBe(200)
    expect((await panicRoute.POST()).status).toBe(200)
    expect(f.mock.calls[0][0]).toBe('http://hypercode-core:8000/api/v1/operator/panic')
    expect(f.mock.calls[0][1].method).toBe('GET')
    expect(f.mock.calls[1][1].method).toBe('POST')
  })

  it('resume goes to the fixed resume path', async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ resumed: [] }) })
    vi.stubGlobal('fetch', f)
    expect((await resumeRoute.POST()).status).toBe(200)
    expect(f.mock.calls[0][0]).toBe('http://hypercode-core:8000/api/v1/operator/panic/resume')
    expect(f.mock.calls[0][1].method).toBe('POST')
  })

  it('forwards nothing the browser sends: handlers take no request at all', () => {
    expect(panicRoute.GET.length).toBe(0)
    expect(panicRoute.POST.length).toBe(0)
    expect(resumeRoute.POST.length).toBe(0)
  })

  it.each([
    ['upstream refuses', () => ({ ok: false, status: 401, json: async () => ({ detail: 'secret detail' }) })],
    ['upstream unreachable', () => { throw new Error('connect ECONNREFUSED 10.0.0.5:8000') }],
  ])('%s → 502 without leaking anything', async (_name, reply) => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => reply()))
    for (const call of [panicRoute.GET, panicRoute.POST, resumeRoute.POST]) {
      const res = await call()
      expect(res.status).toBe(502)
      const text = JSON.stringify(await res.json())
      expect(text).not.toContain('secret detail')
      expect(text).not.toContain('10.0.0.5')
    }
  })

  it('exports only the expected methods', () => {
    const verbs = (m: object) => Object.keys(m).filter((k) => /^(GET|POST|PUT|PATCH|DELETE)$/.test(k)).sort()
    expect(verbs(panicRoute)).toEqual(['GET', 'POST'])
    expect(verbs(resumeRoute)).toEqual(['POST'])
  })
})
