import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  try {
    const res = await fetch(`${CORE_URL}/health`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal: AbortSignal.timeout(5000),
    })
    if (!res.ok) throw new Error(`Core API ${res.status}`)
    return NextResponse.json(await res.json(), { status: 200 })
  } catch (err) {
    return NextResponse.json({ status: 'degraded', error: String(err) }, { status: 200 })
  }
}
