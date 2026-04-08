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
    return NextResponse.json(await res.json(), { status: 200 })
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
