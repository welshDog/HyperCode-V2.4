// Mission Control — Safety Shepherd verdict feed proxy.
// The Shepherd has no CORS middleware (by design — it's an internal service),
// so the browser reads verdicts through this server-side hop.
import { NextRequest, NextResponse } from 'next/server'

const SHEPHERD_URL = process.env.SAFETY_SHEPHERD_URL ?? 'http://safety-shepherd:8096'

export async function GET(request: NextRequest) {
  const limit = request.nextUrl.searchParams.get('limit') ?? '50'
  try {
    const res = await fetch(`${SHEPHERD_URL}/safety/events?limit=${encodeURIComponent(limit)}`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) throw new Error(`Safety Shepherd ${res.status}`)
    const data = await res.json()
    return NextResponse.json({
      events: Array.isArray(data?.events) ? data.events : [],
      updatedAt: new Date().toISOString(),
    })
  } catch (err) {
    return NextResponse.json(
      { events: [], updatedAt: new Date().toISOString(), error: String(err) },
      { status: 200 }
    )
  }
}
