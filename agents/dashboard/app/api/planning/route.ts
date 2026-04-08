import { NextRequest, NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

/** POST /api/planning — proxy to core planning/generate */
export async function POST(req: NextRequest) {
  try {
    const token = req.headers.get('authorization') ?? ''
    const body = await req.json()
    const res = await fetch(`${CORE_URL}/api/v1/planning/generate`, {
      method: 'POST',
      headers: {
        Authorization: token,
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 })
  }
}
