// Panic — pause everything the operator is running (proxy to hypercode-core).
// GET  /api/crew/panic → what is currently held;  POST /api/crew/panic → pause everything now.
// Fixed paths only: nothing the browser sends is forwarded, so there is no id or URL to tamper with.
import { NextResponse } from 'next/server'
import { serviceAuthHeader } from '@/lib/server-auth'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

async function forward(method: 'GET' | 'POST', path: string): Promise<NextResponse> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const auth = serviceAuthHeader()
  if (auth) headers.Authorization = auth
  try {
    const res = await fetch(`${CORE_URL}/api/v1/operator${path}`, {
      method,
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

export const GET = () => forward('GET', '/panic')
export const POST = () => forward('POST', '/panic')
