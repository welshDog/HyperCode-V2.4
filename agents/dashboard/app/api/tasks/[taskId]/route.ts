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

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params
    const taskIdNum = Number(taskId)
    if (!Number.isFinite(taskIdNum) || taskIdNum <= 0) {
      return NextResponse.json({ error: 'Invalid task id' }, { status: 400 })
    }

    const token = req.headers.get('authorization') ?? ''
    const body = await req.json().catch(() => ({}))
    const res = await fetchFromCore(`/api/v1/tasks/${taskIdNum}`, {
      method: 'PUT',
      headers: {
        Authorization: token,
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(body),
    })
    const text = await res.text()
    let data: unknown = null
    try {
      data = JSON.parse(text) as unknown
    } catch {
      data = null
    }
    return NextResponse.json(data ?? { error: text }, { status: res.status })
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 })
  }
}
