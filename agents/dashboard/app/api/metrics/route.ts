import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  try {
    const res = await fetch(`${CORE_URL}/api/v1/metrics`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`Metrics API ${res.status}`)
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({
      requestsPerMin:  '—',
      avgResponseMs:   '—',
      healsToday:      '—',
      errorRatePct:    '—',
      activeAgents:    '—',
      redisQueueDepth: '—',
      collectedAt:     new Date().toISOString(),
    })
  }
}
