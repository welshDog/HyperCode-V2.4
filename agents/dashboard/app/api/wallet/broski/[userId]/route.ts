import { NextRequest, NextResponse } from 'next/server'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  await params
  try {
    const token = req.headers.get('authorization') ?? ''
    // Core wallet endpoint is user-scoped via JWT — userId param is informational
    const res = await fetch(`${CORE_URL}/api/v1/broski/wallet`, {
      headers: { Authorization: token, Accept: 'application/json' },
      cache: 'no-store',
    })
    if (!res.ok) throw new Error(`Wallet API ${res.status}`)
    const data = await res.json()
    return NextResponse.json({
      balance: data.coins ?? 0,
      level:   data.level ?? 1,
      xp:      data.xp ?? 0,
      achievements: [],
    })
  } catch (err) {
    return NextResponse.json(
      { balance: 0, level: 1, xp: 0, achievements: [], error: String(err) },
      { status: 200 }
    )
  }
}
