// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GET } from '../app/api/resources/route'

const MB = 1024 * 1024
const ok = (result: unknown[]) => ({ ok: true, status: 200, json: async () => ({ status: 'success', data: { result } }) })
const row = (name: string, v: number) => ({ metric: { name }, value: [0, String(v)] })
const one = (v: number) => ({ metric: {}, value: [0, String(v)] })

describe('GET /api/resources', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('queries Prometheus read-only with fixed queries and returns a snapshot', async () => {
    const f = vi.fn().mockImplementation(async (url: URL) => {
      const q = url.searchParams.get('query') ?? ''
      if (q.startsWith('container_memory_working_set')) return ok([row('core', 150 * MB)])
      if (q.startsWith('node_memory_MemAvailable')) return ok([one(1600 * MB)])
      if (q.startsWith('node_memory_MemTotal')) return ok([one(4000 * MB)])
      return ok([])
    })
    vi.stubGlobal('fetch', f)
    const body = await (await GET()).json()
    expect(body.available).toBe(true)
    expect(body.containers[0].name).toBe('core')
    expect(body.wsl.verdict).toBe('GREEN')
    expect(f).toHaveBeenCalledTimes(6)
    for (const [url] of f.mock.calls) {
      expect(String(url)).toMatch(/^http:\/\/prometheus:9090\/api\/v1\/query\?query=/)
    }
  })

  it('still answers (with a reason) when Prometheus is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    const res = await GET()
    expect(res.status).toBe(200)
    expect(await res.json()).toMatchObject({ available: false, reason: 'Prometheus is unreachable' })
  })

  it('degrades to "no container data" when the container queries come back empty', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok([])))
    expect(await (await GET()).json()).toMatchObject({ available: false })
  })
})
