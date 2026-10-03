// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/server-auth', () => ({ serviceAuthHeader: () => 'Bearer test-service-jwt' }))
import * as route from '../app/api/pulse/route'

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })
const bad = (status: number) => ({ ok: false, status, json: async () => ({}) })

function stubCore(pulse: unknown, agents: unknown) {
  const f = vi.fn((url: string) => Promise.resolve(String(url).endsWith('/broski/pulse') ? pulse : agents))
  vi.stubGlobal('fetch', f)
  return f
}

describe('pulse proxy', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it("maps core's real shape { coins, xp } (the bug: it read broski_coins/total_xp and always showed 0)", async () => {
    stubCore(ok({ coins: 25, xp: 6705, level: 7 }), ok([]))
    const body = await (await route.GET()).json()
    expect([body.broski_coins, body.total_xp]).toEqual([25, 6705])
  })

  it('still accepts the older shape { broski_coins, total_xp }', async () => {
    stubCore(ok({ broski_coins: 3, total_xp: 40 }), ok([]))
    const body = await (await route.GET()).json()
    expect([body.broski_coins, body.total_xp]).toEqual([3, 40])
  })

  it("sends the dashboard's service credential to BOTH core calls (the bug: none was sent, /orchestrator/agents 401'd)", async () => {
    const f = stubCore(ok({ coins: 1, xp: 1 }), ok([]))
    await route.GET()
    expect(f).toHaveBeenCalledTimes(2)
    for (const call of f.mock.calls) expect((call[1] as { headers: Record<string, string> }).headers.Authorization).toBe('Bearer test-service-jwt')
    expect(f.mock.calls.map((c) => c[0])).toEqual([
      'http://hypercode-core:8000/api/v1/broski/pulse',
      'http://hypercode-core:8000/api/v1/orchestrator/agents',
    ])
  })

  it('counts healthy/online agents and names the first one', async () => {
    stubCore(ok({ coins: 0, xp: 0 }), ok([{ name: 'a', status: 'online' }, { name: 'b', status: 'healthy' }, { name: 'c', status: 'down' }]))
    const body = await (await route.GET()).json()
    expect([body.healthy_agents, body.total_agents, body.top_agent]).toEqual([2, 3, 'a'])
    expect(body.degraded).toBeUndefined()
  })

  it('also reads { agents: [...] }', async () => {
    stubCore(ok({ coins: 0, xp: 0 }), ok({ agents: [{ name: 'x', status: 'ok' }] }))
    expect((await (await route.GET()).json()).total_agents).toBe(1)
  })

  it('says WHICH upstream failed instead of quietly returning zeros', async () => {
    stubCore(ok({ coins: 25, xp: 6705 }), bad(401))
    const body = await (await route.GET()).json()
    expect(body.degraded).toEqual(['agents'])
    expect([body.broski_coins, body.total_xp, body.total_agents]).toEqual([25, 6705, 0]) // the good half is kept
    stubCore(bad(500), ok([]))
    expect((await (await route.GET()).json()).degraded).toEqual(['pulse'])
  })

  it('ignores non-numeric garbage and never throws', async () => {
    stubCore(ok({ coins: 'lots', xp: null }), ok({ agents: 'nope' }))
    const body = await (await route.GET()).json()
    expect([body.broski_coins, body.total_xp, body.total_agents]).toEqual([0, 0, 0])
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
    const res = await route.GET()
    expect(res.status).toBe(200)
    expect((await res.json()).degraded).toEqual(['pulse', 'agents'])
  })

  it('is read-only', () => {
    expect(Object.keys(route).filter((k) => /^(POST|PUT|PATCH|DELETE)$/.test(k))).toEqual([])
  })
})
