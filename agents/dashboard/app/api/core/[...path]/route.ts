import { NextRequest, NextResponse } from 'next/server'
import { serviceAuthHeader } from '@/lib/server-auth'
import { evaluateCoreRequest } from '@/lib/coreProxyPolicy'

export const dynamic = 'force-dynamic'
const CORE_URL = process.env.HYPERCODE_CORE_URL ?? 'http://hypercode-core:8000'

async function proxy(req: NextRequest, path: string[]) {
  const decision = evaluateCoreRequest(req.method, path)
  if (!decision.allowed) {
    const status = decision.reason === 'method' ? 405 : 404
    return NextResponse.json({ error: decision.reason === 'method' ? 'Method not allowed' : 'Not found' }, { status })
  }
  const callerAuth = req.headers.get('authorization')
  if (decision.requireCallerAuth && !callerAuth) {
    return NextResponse.json({ error: 'Authentication required' }, { status: 401 })
  }
  // Service identity is for reads only; writes act as the caller.
  const auth = callerAuth || (decision.useServiceAuth ? serviceAuthHeader() : '')
  const headers = new Headers()
  for (const name of ['accept', 'content-type']) {
    const value = req.headers.get(name)
    if (value) headers.set(name, value)
  }
  if (auth) headers.set('authorization', auth)
  const target = new URL(`${decision.upstreamPath}${req.nextUrl.search}`, CORE_URL)
  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : await req.text(),
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    })
    return new NextResponse(await upstream.text(), {
      status: upstream.status,
      headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json', 'cache-control': 'no-store' },
    })
  } catch {
    return NextResponse.json({ error: 'Core API unavailable' }, { status: 502 })
  }
}

async function handle(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path = [] } = await ctx.params
  return proxy(req, path)
}
export const GET = handle
export const POST = handle
export const HEAD = handle
