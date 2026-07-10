// 🏗️ HyperStudio — coder-studio API proxy
// Forwards /api/studio/* → http://coder-studio:8087/*
// Runs server-side so the X-Agent-Key never reaches the browser and there is
// no CORS hop. The /events path streams Server-Sent Events straight through;
// everything else is JSON.

import { NextRequest, NextResponse } from 'next/server'

const STUDIO_URL = process.env.STUDIO_AGENT_URL ?? 'http://coder-studio:8087'
const STUDIO_KEY = process.env.HYPERCODE_API_KEY ?? process.env.API_KEY ?? ''

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra }
  if (STUDIO_KEY) headers['X-Agent-Key'] = STUDIO_KEY
  return headers
}

function upstreamUrl(path: string[] | undefined, req: NextRequest): string {
  const suffix = '/' + (path ?? []).join('/')
  const qs = req.nextUrl.search
  return `${STUDIO_URL}${suffix}${qs}`
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params
  const url = upstreamUrl(path, req)
  const isStream = (path ?? []).at(-1) === 'events'

  try {
    // SSE has no fixed end, so it must not share the JSON path's timeout.
    const res = await fetch(url, {
      headers: authHeaders({ Accept: isStream ? 'text/event-stream' : 'application/json' }),
      cache: 'no-store',
      signal: isStream ? undefined : AbortSignal.timeout(10_000),
    })

    if (isStream && res.body) {
      // Pipe the event stream through unbuffered.
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          Connection: 'keep-alive',
        },
      })
    }

    return NextResponse.json(await res.json(), { status: res.status })
  } catch (err) {
    return NextResponse.json(
      { error: 'Studio proxy failed', detail: err instanceof Error ? err.message : String(err) },
      { status: 502 },
    )
  }
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params
  const url = upstreamUrl(path, req)

  try {
    const body = await req.text()
    // Forward the idempotency key on merge so a double-click never double-applies.
    const idem = req.headers.get('idempotency-key')
    const headers = authHeaders({ 'Content-Type': 'application/json' })
    if (idem) headers['Idempotency-Key'] = idem

    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: body || undefined,
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch (err) {
    return NextResponse.json(
      { error: 'Studio proxy failed', detail: err instanceof Error ? err.message : String(err) },
      { status: 502 },
    )
  }
}
