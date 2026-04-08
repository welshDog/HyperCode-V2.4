import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  const checks: Record<string, boolean> = {}

  try {
    const r = await fetch(`${CORE_URL}/health`, { cache: 'no-store', signal: AbortSignal.timeout(3000) })
    checks.core = r.ok
  } catch { checks.core = false }

  const allHealthy = Object.values(checks).every(Boolean)
  return NextResponse.json(
    { healthy: allHealthy, checks, timestamp: new Date().toISOString() },
    { status: allHealthy ? 200 : 503 }
  )
}
