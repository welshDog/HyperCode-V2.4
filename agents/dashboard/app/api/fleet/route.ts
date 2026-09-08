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
      // registry scans ~45 agents on a 30s cycle; 5s was too tight and showed
      // as "TimeoutError" on a registry that was merely slow (or not started).
      signal: AbortSignal.timeout(10000),
    })
    if (!res.ok) throw new Error(`Agent registry HTTP ${res.status}`)
    const data = await res.json()
    return NextResponse.json({
      summary: data?.summary ?? null,
      agents: Array.isArray(data?.agents) ? data.agents : [],
      updatedAt: new Date().toISOString(),
    })
  } catch (err) {
    const raw = err instanceof Error ? err.name : String(err)
    const reason = /timeout|abort/i.test(raw)
      ? 'no response within 10s'
      : /fetch failed|ECONNREFUSED|ENOTFOUND|getaddrinfo/i.test(String(err))
        ? 'not reachable (is agent-registry running?)'
        : String(err)
    return NextResponse.json(
      {
        summary: null,
        agents: [],
        updatedAt: new Date().toISOString(),
        error: reason,
        recovery: 'docker compose up -d agent-registry',
      },
      { status: 200 }
    )
  }
}
