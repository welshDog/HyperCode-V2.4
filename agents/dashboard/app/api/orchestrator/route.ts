import { NextRequest, NextResponse } from 'next/server'
import { readFileSync } from 'fs'

const ORCH_URL = process.env.CREW_ORCHESTRATOR_URL ?? 'http://crew-orchestrator:8080'
let cachedApiKey: string | null = null
function orchestratorApiKey(): string {
  if (cachedApiKey !== null) return cachedApiKey
  let key = process.env.ORCHESTRATOR_API_KEY ?? ''
  if (!key && process.env.ORCHESTRATOR_API_KEY_FILE) {
    try { key = readFileSync(process.env.ORCHESTRATOR_API_KEY_FILE, 'utf8').trim() } catch { key = '' }
  }
  cachedApiKey = key
  return key
}

export async function GET(_req: NextRequest) {
  try {
    const key = orchestratorApiKey()
    const res = await fetch(`${ORCH_URL}/system/health`, {
      headers: { Accept: 'application/json', ...(key ? { 'X-API-Key': key } : {}) },
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) throw new Error(`Orchestrator API ${res.status}`)
    const data = await res.json()
    if (!data || typeof data.status !== 'string') {
      const live = await fetch(`${ORCH_URL}/health`, { cache: 'no-store', signal: AbortSignal.timeout(3000) }).then((r) => r.ok).catch(() => false)
      return NextResponse.json(live ? { status: 'ok', agents: data?.agents ?? {}, note: 'health cache empty — service alive' } : { status: 'degraded', error: 'health cache empty and /health unreachable' })
    }
    return NextResponse.json(data)
  } catch (err) {
    return NextResponse.json({ status: 'degraded', error: err instanceof Error ? err.message : String(err) })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const key = orchestratorApiKey()
    const res = await fetch(`${ORCH_URL}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(key ? { 'X-API-Key': key } : {}) },
      body: JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(30_000),
    })
    const text = await res.text()
    return new NextResponse(text, { status: res.status, headers: { 'content-type': res.headers.get('content-type') ?? 'application/json' } })
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : String(err) }, { status: 502 })
  }
}
