'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { useToast } from '@/components/ui/ToastProvider'

export function MCPGatewayView(): React.JSX.Element {
  const [health, setHealth] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  const load = useCallback(async (isManual = false) => {
    if (isManual) toast({ type: 'info', message: '⏳ Checking MCP Gateway…' })
    setLoading(true)
    setError(null)
    let t: ReturnType<typeof setTimeout> | null = null
    try {
      const controller = new AbortController()
      t = setTimeout(() => controller.abort(), 15_000)
      const h = await fetch('/api/mcp/health', { signal: controller.signal })
      const hBody: unknown = await h.json().catch(() => null)
      setHealth(hBody)
      if (isManual) toast({ type: 'success', message: '✅ Gateway connected' })
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (isManual) toast({ type: 'error', message: '❌ Gateway unreachable' })
      if (msg.toLowerCase().includes('abort') || msg.toLowerCase().includes('signal')) {
        setError('MCP server did not respond in time. Check that hypercode-mcp-server is running: docker compose up -d hypercode-mcp-server')
      } else {
        setError(msg)
      }
    } finally {
      if (t) clearTimeout(t)
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  if (loading) return <div style={{ color: 'var(--text-secondary)', padding: 16 }}>⏳ Loading MCP status…</div>
  if (error) return (
    <div style={{ color: 'var(--status-error)', padding: 16, lineHeight: 1.6 }}>
      ⚠️ {error}
    </div>
  )
  const healthObj = (health && typeof health === 'object') ? (health as Record<string, unknown>) : {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{
        border: '1px solid var(--pane-border)',
        borderRadius: 6,
        background: 'rgba(255,255,255,0.03)',
        padding: '10px 12px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>HyperCode MCP Server</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700 }}>
            {(typeof healthObj.status === 'string' ? healthObj.status : null) ?? 'unknown'}
          </div>
        </div>
        <button className="btn" onClick={() => load(true)}>↻ Refresh</button>
      </div>

      <div style={{
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 6,
        padding: '10px 12px',
        background: 'rgba(255,255,255,0.02)',
        fontSize: 10,
        color: 'var(--text-secondary)',
        lineHeight: 1.6,
      }}>
        Tools are exposed over SSE (MCP transport). Use an MCP-capable client to list/call tools via{' '}
        <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>http://localhost:8823/sse</span>.
      </div>
    </div>
  )
}
