import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

// BROski Pulse — aggregates XP, BROski$, healthy count, top agent
export async function GET() {
  try {
    const [pulseRes, agentsRes] = await Promise.allSettled([
      fetch(`${CORE_URL}/api/v1/broski/pulse`, {
        headers: { 'Accept': 'application/json' },
        cache: 'no-store',
        signal: AbortSignal.timeout(4000),
      }),
      fetch(`${CORE_URL}/api/v1/orchestrator/agents`, {
        headers: { 'Accept': 'application/json' },
        cache: 'no-store',
        signal: AbortSignal.timeout(4000),
      }),
    ])

    let broski = { broski_coins: 0, total_xp: 0 }
    if (pulseRes.status === 'fulfilled' && pulseRes.value.ok) {
      broski = await pulseRes.value.json().catch(() => broski)
    }

    let agents: unknown[] = []
    if (agentsRes.status === 'fulfilled' && agentsRes.value.ok) {
      const data = await agentsRes.value.json().catch(() => null)
      agents = Array.isArray(data?.agents) ? data.agents : Array.isArray(data) ? data : []
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
      broski_coins: broski.broski_coins ?? 0,
      total_xp: broski.total_xp ?? 0,
      healthy_agents: healthy,
      total_agents: agents.length,
      top_agent: topAgent,
      updatedAt: new Date().toISOString(),
    })
  } catch (err) {
    return NextResponse.json(
      { broski_coins: 0, total_xp: 0, healthy_agents: 0, total_agents: 0, error: String(err) },
      { status: 200 }
    )
  }
}
