// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as route from '../app/api/crew/morning/route'

describe('morning proxy', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('GET goes to the fixed core path and passes the card through', async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ calmCard: {}, light: 'green' }) })
    vi.stubGlobal('fetch', f)
    const res = await route.GET()
    expect(res.status).toBe(200)
    expect(f.mock.calls[0][0]).toBe('http://hypercode-core:8000/api/v1/operator/morning')
    expect(f.mock.calls[0][1].method).toBeUndefined() // a plain read
  })

  it('is read-only and forwards nothing from the browser', () => {
    expect(Object.keys(route).filter((k) => /^(POST|PUT|PATCH|DELETE)$/.test(k))).toEqual([])
    expect(route.GET.length).toBe(0)
  })

  it('maps any core failure to a quiet 502', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }))
    expect((await route.GET()).status).toBe(502)
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    expect((await route.GET()).status).toBe(502)
  })
})
