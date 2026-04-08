import { NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET() {
  try {
    const res = await fetch(`${CORE_URL}/api/v1/agents/status`, {
      headers: { 'Accept': 'application/json' },
      cache:   'no-store',
    })
    if (!res.ok) throw new Error(`Core API ${res.status}`)
    const data = await res.json()
    return NextResponse.json(data)
  } catch (err) {
    // Return degraded stub so the UI never hard-crashes
    return NextResponse.json(
      { agents: [], updatedAt: new Date().toISOString(), error: String(err) },
      { status: 200 }
    )
  }
}
