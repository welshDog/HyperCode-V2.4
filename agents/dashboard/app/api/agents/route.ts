import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

// /api/v1/agents/status is the OPEN heartbeat roster. The previous target
// (/api/v1/orchestrator/agents) is auth-gated and 401s, which this proxy
// used to swallow into a fake-empty roster ("No agents reporting" bug).
export async function GET() {
  try {
    const res = await fetch(`${CORE_URL}/api/v1/agents/status`, {
      headers: { 'Accept': 'application/json' },
      cache:   'no-store',
      signal:  AbortSignal.timeout(5000),
    })
    if (!res.ok) throw new Error(`Core API ${res.status}`)
    const data = await res.json()
    const agents = Array.isArray(data?.agents)
      ? data.agents
      : Array.isArray(data)
        ? data
        : []
    return NextResponse.json({ agents, updatedAt: new Date().toISOString() })
  } catch (err) {
    // Surface the failure — a 502 lets the UI distinguish "core unreachable"
    // from a genuinely empty roster instead of rendering a misleading zero.
    return NextResponse.json(
      { agents: [], updatedAt: new Date().toISOString(), error: String(err) },
      { status: 502 }
    )
  }
}
