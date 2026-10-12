// HyperCrew run events — read-only proxy to hypercode-core.
// GET /api/crew/{taskId}/events?after=N → /api/v1/operator/tasks/{taskId}/events?after=N
// Server-side so credentials never reach the browser. GET only: approving a plan is a human,
// plan_hash-bound action and is deliberately NOT exposed here.
import { NextRequest, NextResponse } from 'next/server'
import { serviceAuthHeader } from '@/lib/server-auth'

const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'
const TASK_ID = /^[A-Za-z0-9_-]{1,64}$/

export async function GET(req: NextRequest, ctx: { params: Promise<{ taskId: string }> }) {
  const { taskId } = await ctx.params
  if (!TASK_ID.test(taskId)) {
    return NextResponse.json({ error: 'invalid task id' }, { status: 400 })
  }
  const rawAfter = req.nextUrl.searchParams.get('after') ?? '-1'
  // Strict: parseInt would accept "1.5x" as 1.
  if (!/^-?\d{1,9}$/.test(rawAfter) || Number(rawAfter) < -1) {
    return NextResponse.json({ error: 'invalid after' }, { status: 400 })
  }
  const after = Number(rawAfter)

  const headers: Record<string, string> = { Accept: 'application/json' }
  const auth = serviceAuthHeader()
  if (auth) headers.Authorization = auth

  try {
    const res = await fetch(`${CORE_URL}/api/v1/operator/tasks/${taskId}/events?after=${after}`, {
      headers,
      cache: 'no-store',
      signal: AbortSignal.timeout(10_000),
    })
    if (res.status === 404) return NextResponse.json({ error: 'task not found' }, { status: 404 })
    if (!res.ok) return NextResponse.json({ error: 'crew events unavailable' }, { status: 502 })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'crew events unavailable' }, { status: 502 })
  }
}
