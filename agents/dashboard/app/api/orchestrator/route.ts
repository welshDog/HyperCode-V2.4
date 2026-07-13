import { NextRequest, NextResponse } from 'next/server'

const ORCH_URL = process.env.CREW_ORCHESTRATOR_URL ?? 'http://crew-orchestrator:8080'
const ORCH_API_KEY = process.env.ORCHESTRATOR_API_KEY ?? ''

/** GET /api/orchestrator — system health from crew-orchestrator */
export async function GET(req: NextRequest) {
  try {
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (ORCH_API_KEY) headers['X-API-Key'] = ORCH_API_KEY
    const res = await fetch(`${ORCH_URL}/system/health`, {
      headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) throw new Error(`Orchestrator API ${res.status}`)
    const data = await res.json()
    // system:health is a Redis cache the monitor loop fills — when it's empty
    // ({} or no status) the service may still be perfectly alive. Confirm via
    // the open /health probe instead of letting the UI claim "Unreachable".
    if (!data || typeof data.status !== 'string') {
      const live = await fetch(`${ORCH_URL}/health`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3000),
      }).then((r) => r.ok).catch(() => false)
      return NextResponse.json(
        live
          ? { status: 'ok', agents: data?.agents ?? {}, note: 'health cache empty — service alive' }
          : { status: 'degraded', error: 'health cache empty and /health unreachable' },
        { status: 200 }
      )
    }
    return NextResponse.json(data, { status: 200 })
  } catch (err) {
    return NextResponse.json({ status: 'degraded', error: String(err) }, { status: 200 })
  }
}

/** POST /api/orchestrator — proxy execute to crew-orchestrator */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (ORCH_API_KEY) headers['X-API-Key'] = ORCH_API_KEY
    const res = await fetch(`${ORCH_URL}/execute`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(30_000),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 })
  }
}
