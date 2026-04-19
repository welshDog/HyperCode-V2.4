import { NextRequest, NextResponse } from 'next/server'

const CORE_URL_CANDIDATES = [
  process.env.HYPERCODE_CORE_URL,
  process.env.NEXT_PUBLIC_CORE_URL,
  'http://hypercode-core:8000',
  'http://host.docker.internal:8000',
  'http://127.0.0.1:8000',
  'http://localhost:8000',
].filter(Boolean) as string[]

async function fetchFromCore(path: string, init?: RequestInit) {
  let lastErr: unknown = null
  for (const base of CORE_URL_CANDIDATES) {
    try {
      return await fetch(`${base}${path}`, { cache: 'no-store', ...init })
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr ?? new Error('Failed to reach core')
}

export async function GET(req: NextRequest) {
  try {
    const token = req.headers.get('authorization') ?? ''
    const { searchParams } = new URL(req.url)
    const limit = searchParams.get('limit')
    const offset = searchParams.get('offset')
    const qs = new URLSearchParams()
    if (limit) qs.set('limit', limit)
    if (offset) qs.set('offset', offset)

    const res = await fetchFromCore(`/api/v1/ops/dlq?${qs.toString()}`, {
      headers: { Authorization: token, Accept: 'application/json' },
    })
    const text = await res.text()
    let data: unknown = null
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
    return NextResponse.json(data ?? { error: text }, { status: res.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 })
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const token = req.headers.get('authorization') ?? ''
    const res = await fetchFromCore('/api/v1/ops/dlq', {
      method: 'DELETE',
      headers: { Authorization: token, Accept: 'application/json' },
    })
    const text = await res.text()
    let data: unknown = null
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
    return NextResponse.json(data ?? { error: text }, { status: res.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 })
  }
}
