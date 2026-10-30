import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'
const ORCH_URL = process.env.CREW_ORCHESTRATOR_URL ?? 'http://crew-orchestrator:8080'
const STUDIO_URL = process.env.STUDIO_AGENT_URL ?? 'http://coder-studio:8087'

async function probe(url: string, required = false) {
  const started = performance.now()
  try {
    const res = await fetch(url, { headers: { Accept: 'application/json' }, cache: 'no-store', signal: AbortSignal.timeout(4000) })
    return { status: res.ok ? 'healthy' : 'degraded', latency_ms: Math.round(performance.now() - started), required, ...(res.ok ? {} : { error: `HTTP ${res.status}` }) }
  } catch (error) {
    return { status: 'down', latency_ms: Math.round(performance.now() - started), required, error: error instanceof Error ? error.message : 'Service unavailable' }
  }
}

export async function GET() {
  const [core, orchestrator, studio] = await Promise.all([
    probe(`${CORE_URL}/health`, true),
    probe(`${ORCH_URL}/health`, process.env.DASHBOARD_CHECK_ORCHESTRATOR === 'true'),
    probe(`${STUDIO_URL}/health`, process.env.DASHBOARD_CHECK_STUDIO === 'true'),
  ])
  const dependencies = { core, orchestrator, studio }
  const healthy = core.status === 'healthy'
  return NextResponse.json({ status: healthy ? 'healthy' : 'degraded', healthy, dependencies, timestamp: new Date().toISOString() }, {
    status: healthy ? 200 : 503,
    headers: { 'Cache-Control': 'no-store' },
  })
}
