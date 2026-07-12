// Mission Control — fleet status proxy.
// Server-side fetch to agent-registry (agents-net hostname) so the browser
// never needs CORS on :8077. Fail-soft: registry down = empty fleet + error.
import { NextResponse } from 'next/server'

const REGISTRY_URL = process.env.AGENT_REGISTRY_URL ?? 'http://agent-registry:8077'

export async function GET() {
  try {
    const res = await fetch(`${REGISTRY_URL}/agents/status`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) throw new Error(`Agent registry ${res.status}`)
    const data = await res.json()
    return NextResponse.json({
      summary: data?.summary ?? null,
      agents: Array.isArray(data?.agents) ? data.agents : [],
      updatedAt: new Date().toISOString(),
    })
  } catch (err) {
    return NextResponse.json(
      { summary: null, agents: [], updatedAt: new Date().toISOString(), error: String(err) },
      { status: 200 }
    )
  }
}
