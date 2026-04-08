import { NextRequest, NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET(req: NextRequest) {
  try {
    const token = req.headers.get('authorization') ?? ''
    const res = await fetch(`${CORE_URL}/api/v1/broski/pulse`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!res.ok) throw new Error(`BROski API ${res.status}`)
    return NextResponse.json(await res.json())
  } catch (err) {
    return NextResponse.json(
      { coins: 0, xp: 0, level: 1, level_name: 'Rookie', error: String(err) },
      { status: 200 }
    )
  }
}
