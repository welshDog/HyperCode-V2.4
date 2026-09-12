// Skill discoverability — goal-in, ranked-skills-out search proxy.
// Server-side fetch to hypercode-core so the browser never needs CORS.
// Fail-soft: backend unreachable/erroring = empty matches + error, never a 5xx.
import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function POST(req: Request) {
  let goal: string
  try {
    const body = await req.json()
    goal = typeof body?.goal === 'string' ? body.goal : ''
  } catch {
    goal = ''
  }

  if (!goal.trim()) {
    return NextResponse.json(
      { matches: [], usedFallback: true, error: 'goal is required' },
      { status: 200 }
    )
  }

  try {
    const res = await fetch(`${CORE_URL}/api/v1/skills/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ goal }),
      cache: 'no-store',
      // an LLM round trip, not a status poll — longer than fleet/route.ts's 10s
      signal: AbortSignal.timeout(15000),
    })
    if (!res.ok) throw new Error(`hypercode-core HTTP ${res.status}`)
    const data = await res.json()
    return NextResponse.json({
      matches: Array.isArray(data?.matches) ? data.matches : [],
      usedFallback: Boolean(data?.usedFallback),
      error: data?.error ?? null,
    })
  } catch (err) {
    const raw = err instanceof Error ? err.name : String(err)
    const reason = /timeout|abort/i.test(raw)
      ? 'no response within 15s'
      : /fetch failed|ECONNREFUSED|ENOTFOUND|getaddrinfo/i.test(String(err))
        ? 'not reachable (is hypercode-core running?)'
        : String(err)
    return NextResponse.json(
      { matches: [], usedFallback: true, error: reason },
      { status: 200 }
    )
  }
}
