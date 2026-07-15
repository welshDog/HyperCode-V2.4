// Hands the browser a short-lived credential for the approvals WebSocket.
// The core WS endpoint requires ?token=<user JWT>; the dashboard has no
// login UI, so the service JWT (server env) is exposed to the local client.
// Empty when unconfigured — the client then behaves exactly as before.
import { NextResponse } from 'next/server'
import { serviceAuthHeader } from '@/lib/server-auth'

export async function GET() {
  const header = serviceAuthHeader() // "Bearer <jwt>" or ""
  const token = header.startsWith('Bearer ') ? header.slice(7) : ''
  return NextResponse.json(
    { token },
    { headers: { 'Cache-Control': 'no-store' } }
  )
}
