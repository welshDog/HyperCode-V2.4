import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  try {
    const res = await fetch(`${CORE_URL}/api/v1/orchestrator/agents`, {
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
    return NextResponse.json(
      { agents: [], updatedAt: new Date().toISOString(), error: String(err) },
      { status: 200 }
    )
  }
}
