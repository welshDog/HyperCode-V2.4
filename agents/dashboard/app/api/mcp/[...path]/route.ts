import { NextRequest, NextResponse } from 'next/server'
import { readFileSync } from 'fs'

const MCP_REST_BASE_CANDIDATES = [process.env.MCP_REST_ADAPTER_URL, 'http://mcp-rest-adapter:8821', 'http://host.docker.internal:8821', 'http://127.0.0.1:8821', 'http://localhost:8821'].filter(Boolean) as string[]
const MCP_SSE_URL_CANDIDATES = [process.env.HYPERCODE_MCP_SSE_URL, 'http://hypercode-mcp-server:8823/sse', 'http://host.docker.internal:8823/sse', 'http://127.0.0.1:8823/sse', 'http://localhost:8823/sse'].filter(Boolean) as string[]

let cachedAuthToken: string | null = null
function authHeader(): Record<string, string> {
  if (cachedAuthToken === null) {
    cachedAuthToken = process.env.MCP_REST_ADAPTER_AUTH_TOKEN ?? ''
    if (!cachedAuthToken && process.env.MCP_REST_ADAPTER_AUTH_TOKEN_FILE) {
      try { cachedAuthToken = readFileSync(process.env.MCP_REST_ADAPTER_AUTH_TOKEN_FILE, 'utf8').trim() } catch { cachedAuthToken = '' }
    }
  }
  return cachedAuthToken ? { Authorization: `Bearer ${cachedAuthToken}` } : {}
}
async function proxy(upstreamUrl: string, init?: RequestInit) {
  const upstream = await fetch(upstreamUrl, { cache: 'no-store', signal: AbortSignal.timeout(5000), ...init })
  return new NextResponse(await upstream.text(), { status: upstream.status, headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' } })
}
async function tryProxyFromBases(bases: string[], path: string, init?: RequestInit) {
  let lastErr: unknown = null
  for (const base of bases) {
    try { return await proxy(`${base}${path}`, init) } catch (err) { lastErr = err }
  }
  throw lastErr ?? new Error('Upstream unreachable')
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const upstreamPath = `/${(path ?? []).map(encodeURIComponent).join('/')}`
  try {
    if (upstreamPath === '/health') {
      try { return await tryProxyFromBases(MCP_REST_BASE_CANDIDATES, '/health', { method: 'GET', headers: { Accept: 'application/json' } }) }
      catch {
        let lastErr: unknown = null
        for (const sseUrl of MCP_SSE_URL_CANDIDATES) {
          try {
            const sse = await fetch(sseUrl, { cache: 'no-store', method: 'GET', signal: AbortSignal.timeout(5000) })
            return NextResponse.json({ status: sse.ok ? 'ok' : 'down', transport: 'sse' }, { status: sse.ok ? 200 : 503 })
          } catch (err) { lastErr = err }
        }
        throw lastErr ?? new Error('SSE unreachable')
      }
    }
    return await tryProxyFromBases(MCP_REST_BASE_CANDIDATES, `${upstreamPath}${req.nextUrl.search}`, { method: 'GET', headers: { Accept: 'application/json', ...authHeader() } })
  } catch (err) {
    return NextResponse.json({ error: 'MCP proxy failed', detail: err instanceof Error ? err.message : String(err) }, { status: 502 })
  }
}
export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params
  const upstreamPath = `/${(path ?? []).map(encodeURIComponent).join('/')}`
  try {
    return await tryProxyFromBases(MCP_REST_BASE_CANDIDATES, upstreamPath, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json', ...authHeader() }, body: await req.text() })
  } catch (err) {
    return NextResponse.json({ error: 'MCP proxy failed', detail: err instanceof Error ? err.message : String(err), hint: 'Check that the MCP REST adapter service is running.' }, { status: 502 })
  }
}
