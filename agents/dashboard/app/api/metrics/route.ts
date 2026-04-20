import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  try {
    const res = await fetch(`${CORE_URL}/api/v1/metrics`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`Metrics API ${res.status}`)
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({
      requestsPerMin:  0,
      avgResponseMs:   0,
      healsToday:      0,
      errorRatePct:    0,
      activeAgents:    0,
      redisQueueDepth: 0,
      celeryQueueDepths: {},
      dlqDepth: 0,
      alertFiring: 0,
      alertPending: 0,
      alertTopFiring: [],
      collectedAt:     new Date().toISOString(),
    })
  }
}
