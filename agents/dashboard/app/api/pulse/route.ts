import { NextResponse } from 'next/server'
import { serviceAuthHeader } from '@/lib/server-auth'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

const num = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0)

// BROski Pulse — aggregates XP, BROski$, healthy count, top agent.
//
// Two bugs fixed 2026-10-03 (found by the IDE health check):
//  1. core's /broski/pulse returns { coins, xp, ... }, but this route read { broski_coins, total_xp } -> always 0.
//     Both shapes are accepted now.
//  2. /orchestrator/agents is auth-gated (401 without a credential) and this route sent none, so it silently reported
//     0 agents. It now sends the dashboard's service JWT like every other proxy, and says which upstream failed
//     (`degraded`) instead of quietly returning zeros.
export async function GET() {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const auth = serviceAuthHeader()
  if (auth) headers.Authorization = auth

  try {
    const [pulseRes, agentsRes] = await Promise.allSettled([
      fetch(`${CORE_URL}/api/v1/broski/pulse`, { headers, cache: 'no-store', signal: AbortSignal.timeout(4000) }),
      fetch(`${CORE_URL}/api/v1/orchestrator/agents`, { headers, cache: 'no-store', signal: AbortSignal.timeout(4000) }),
    ])
    const degraded: string[] = []

    let coins = 0
    let xp = 0
    if (pulseRes.status === 'fulfilled' && pulseRes.value.ok) {
      const j = await pulseRes.value.json().catch(() => null)
      coins = num(j?.broski_coins ?? j?.coins)
      xp = num(j?.total_xp ?? j?.xp)
    } else {
      degraded.push('pulse')
    }

    let agents: unknown[] = []
    if (agentsRes.status === 'fulfilled' && agentsRes.value.ok) {
      const data = await agentsRes.value.json().catch(() => null)
      agents = Array.isArray(data?.agents) ? data.agents : Array.isArray(data) ? data : []
    } else {
      degraded.push('agents')
    }

    const healthy = agents.filter((a: unknown) => {
      const rec = a as Record<string, unknown>
      const s = String(rec?.status ?? '').toLowerCase()
      return s === 'healthy' || s === 'online' || s === 'ok' || s === 'up'
    }).length

    const topAgent = agents.length > 0
      ? String((agents[0] as Record<string, unknown>)?.name ?? '')
      : undefined

    return NextResponse.json({
      broski_coins: coins,
      total_xp: xp,
      healthy_agents: healthy,
      total_agents: agents.length,
      top_agent: topAgent,
      updatedAt: new Date().toISOString(),
      ...(degraded.length ? { degraded } : {}),
    })
  } catch (err) {
    return NextResponse.json(
      { broski_coins: 0, total_xp: 0, healthy_agents: 0, total_agents: 0, error: String(err) },
      { status: 200 }
    )
  }
}
