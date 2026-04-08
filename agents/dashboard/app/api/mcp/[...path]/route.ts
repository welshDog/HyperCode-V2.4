import { NextRequest, NextResponse } from 'next/server'

const MCP_REST_BASE_CANDIDATES = [
  process.env.MCP_REST_ADAPTER_URL,
  'http://mcp-rest-adapter:8821',
  'http://host.docker.internal:8821',
  'http://127.0.0.1:8821',
  'http://localhost:8821',
].filter(Boolean) as string[]

const MCP_SSE_URL_CANDIDATES = [
  process.env.HYPERCODE_MCP_SSE_URL,
  'http://hypercode-mcp-server:8823/sse',
  'http://host.docker.internal:8823/sse',
  'http://127.0.0.1:8823/sse',
  'http://localhost:8823/sse',
].filter(Boolean) as string[]

async function proxy(upstreamUrl: string, init?: RequestInit) {
  const upstream = await fetch(upstreamUrl, { cache: 'no-store', signal: AbortSignal.timeout(5000), ...init })
  const text = await upstream.text()
  const contentType = upstream.headers.get('content-type') ?? 'application/json'
  return new NextResponse(text, { status: upstream.status, headers: { 'content-type': contentType } })
}

async function tryProxyFromBases(
  bases: string[],
  path: string,
  init?: RequestInit
): Promise<NextResponse> {
  let lastErr: unknown = null
  for (const base of bases) {
    try {
      return await proxy(`${base}${path}`, init)
    } catch (err) {
      lastErr = err
    }
  }
  throw lastErr ?? new Error('Upstream unreachable')
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const upstreamPath = '/' + (path ?? []).join('/')
  try {
    if (upstreamPath === '/health') {
      try {
        return await tryProxyFromBases(MCP_REST_BASE_CANDIDATES, '/health', { method: 'GET', headers: { Accept: 'application/json' } })
      } catch {
        let lastErr: unknown = null
        for (const sseUrl of MCP_SSE_URL_CANDIDATES) {
          try {
            const sse = await fetch(sseUrl, { cache: 'no-store', method: 'GET', signal: AbortSignal.timeout(5000) })
            return NextResponse.json(
              {
                status: sse.ok ? 'ok' : 'down',
                transport: 'sse',
                sse_url: sseUrl,
              },
              { status: sse.ok ? 200 : 503 }
            )
          } catch (err) {
            lastErr = err
          }
        }
        throw lastErr ?? new Error('SSE unreachable')
      }
    }
    return await tryProxyFromBases(
      MCP_REST_BASE_CANDIDATES,
      `${upstreamPath}${req.nextUrl.search}`,
      { method: 'GET', headers: { Accept: 'application/json' } }
    )
  } catch (err) {
    return NextResponse.json(
      { error: 'MCP proxy failed', detail: err instanceof Error ? err.message : String(err) },
      { status: 502 }
    )
  }
}

export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const upstreamPath = '/' + (path ?? []).join('/')
  try {
    const body = await req.text()
    return await tryProxyFromBases(MCP_REST_BASE_CANDIDATES, upstreamPath, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body,
    })
  } catch (err) {
    return NextResponse.json(
      {
        error: 'MCP proxy failed',
        detail: err instanceof Error ? err.message : String(err),
        hint: 'If tools/call is failing, the MCP REST adapter service may not be running in Docker.',
      },
      { status: 502 }
    )
  }
}
