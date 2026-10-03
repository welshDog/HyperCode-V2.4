// Morning Card — read-only proxy to hypercode-core ("Where was I?").
// GET /api/crew/morning → /api/v1/operator/morning. Fixed path: nothing the browser sends is forwarded.
import { NextResponse } from 'next/server'
import { serviceAuthHeader } from '@/lib/server-auth'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const auth = serviceAuthHeader()
  if (auth) headers.Authorization = auth
  try {
    const res = await fetch(`${CORE_URL}/api/v1/operator/morning`, {
      headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })
    if (!res.ok) return NextResponse.json({ error: 'crew unavailable' }, { status: 502 })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'crew unavailable' }, { status: 502 })
  }
}
