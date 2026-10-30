import { NextResponse } from 'next/server'
import { buildSnapshot, type PromVector } from '@/lib/resourceSnapshot'

export const dynamic = 'force-dynamic'

const PROMETHEUS_URL = process.env.PROMETHEUS_URL ?? 'http://prometheus:9090'

// Fixed, read-only queries: nothing from the request ever reaches Prometheus.
const QUERIES = {
  workingSet: 'container_memory_working_set_bytes{name!=""}',
  limit: 'container_spec_memory_limit_bytes{name!=""}',
  cpu: 'sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[2m]))',
  wslAvailable: 'node_memory_MemAvailable_bytes',
  wslTotal: 'node_memory_MemTotal_bytes',
  swapUsed: 'node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes',
} as const

async function query(expr: string): Promise<PromVector> {
  const url = new URL('/api/v1/query', PROMETHEUS_URL)
  url.searchParams.set('query', expr)
  const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(5_000) })
  if (!res.ok) throw new Error(`Prometheus ${res.status}`)
  const body = await res.json()
  return body?.status === 'success' && Array.isArray(body.data?.result) ? body.data.result : []
}

export async function GET() {
  const keys = Object.keys(QUERIES) as Array<keyof typeof QUERIES>
  const settled = await Promise.allSettled(keys.map((k) => query(QUERIES[k])))
  const results = Object.fromEntries(
    keys.map((k, i) => [k, settled[i].status === 'fulfilled' ? settled[i].value : []]),
  ) as Record<keyof typeof QUERIES, PromVector>

  // Every query failing means Prometheus itself is unreachable.
  if (settled.every((s) => s.status === 'rejected')) {
    return NextResponse.json(
      { available: false, reason: 'Prometheus is unreachable', collectedAt: new Date().toISOString() },
      { status: 200, headers: { 'cache-control': 'no-store' } },
    )
  }
  return NextResponse.json(buildSnapshot(results), { headers: { 'cache-control': 'no-store' } })
}
