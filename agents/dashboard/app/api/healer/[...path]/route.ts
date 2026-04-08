// 🦅 HyperStation — Healer Agent API Proxy
// Forwards /api/healer/* → http://healer-agent:8008/*
// Runs server-side in Next.js so the browser never has a CORS issue
// Container name 'healer-agent' resolves inside the Docker bridge network

import { NextRequest, NextResponse } from 'next/server';

const HEALER_BASE =
  process.env.HEALER_AGENT_URL ?? 'http://healer-agent:8008';

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const upstreamPath = '/' + (path ?? []).join('/');
  const upstreamUrl  = `${HEALER_BASE}${upstreamPath}`;

  try {
    const upstream = await fetch(upstreamUrl, {
      headers: { 'Content-Type': 'application/json' },
      // Next.js edge cache: always fresh for live telemetry
      cache: 'no-store',
    });

    const body = await upstream.json();
    return NextResponse.json(body, { status: upstream.status });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Proxy error';
    return NextResponse.json(
      { error: 'Healer proxy failed', detail: message },
      { status: 502 }
    );
  }
}
