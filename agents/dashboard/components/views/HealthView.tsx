'use client'

import React, { useCallback, useEffect, useState } from 'react'
import { useToast } from '@/components/ui/ToastProvider'

type Status = 'healthy' | 'degraded' | 'down' | 'unknown'

function toStatus(v: unknown): Status {
  if (!v) return 'unknown'
  if (v === true) return 'healthy'
  if (v === false) return 'down'
  if (typeof v === 'string') {
    const s = v.toLowerCase()
    if (s.includes('healthy') || s === 'ok') return 'healthy'
    if (s.includes('degraded') || s.includes('warn')) return 'degraded'
    if (s.includes('down') || s.includes('fail') || s.includes('error')) return 'down'
  }
  return 'unknown'
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === 'object' ? (v as Record<string, unknown>) : null
}

function badge(status: Status) {
  const map: Record<Status, { label: string; color: string; bg: string }> = {
    healthy:  { label: 'healthy',  color: 'var(--status-healthy)', bg: 'rgba(0,255,136,0.12)' },
    degraded: { label: 'degraded', color: 'var(--status-warning)', bg: 'rgba(255,170,0,0.12)' },
    down:     { label: 'down',     color: 'var(--status-error)',   bg: 'rgba(255,68,102,0.12)' },
    unknown:  { label: 'unknown',  color: 'var(--text-secondary)', bg: 'rgba(255,255,255,0.04)' },
  }
  const s = map[status]
  return (
    <span style={{
      border: `1px solid ${s.color}`,
      background: s.bg,
      color: s.color,
      borderRadius: 999,
      padding: '2px 8px',
      fontSize: 10,
      fontWeight: 800,
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
    }}>
      {s.label}
    </span>
  )
}

export function HealthView(): React.JSX.Element {
  const [core, setCore] = useState<unknown>(null)
  const [orchestrator, setOrchestrator] = useState<unknown>(null)
  const [healer, setHealer] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  const load = useCallback(async (isManual = false) => {
    if (isManual) toast({ type: 'info', message: '⏳ Sweeping health endpoints…' })
    setLoading(true)
    try {
      const coreRes = await fetch('/api/health')
      setCore(await coreRes.json().catch(() => null))

      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const orchRes = await fetch('/api/orchestrator', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      setOrchestrator(await orchRes.json().catch(() => null))

      const healerRes = await fetch('/api/healer/health')
      setHealer(await healerRes.json().catch(() => null))
      if (isManual) toast({ type: 'success', message: '✅ Sweep complete' })
    } catch {
      if (isManual) toast({ type: 'error', message: '❌ Sweep failed' })
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    load(false)
    const t = setInterval(() => load(false), 20_000)
    return () => clearInterval(t)
  }, [load])

  if (loading && !core && !orchestrator && !healer) {
    return <div style={{ color: 'var(--text-secondary)', padding: 16 }}>⏳ Loading health…</div>
  }

  const coreObj = asRecord(core) ?? {}
  const orchObj = asRecord(orchestrator) ?? {}
  const healerObj = asRecord(healer) ?? {}
  const orchStatus = toStatus(orchObj.status ?? orchObj.healthy)
  const orchDetail = orchStatus === 'unknown'
    ? `Unreachable — start crew-orchestrator${orchObj.error ? ` (${String(orchObj.error).slice(0, 60)})` : ''}`
    : (orchObj.error ? String(orchObj.error).slice(0, 80) : '—')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Live checks via <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>/api/*</span>
        </div>
        <button className="btn" onClick={() => load(true)}>↻ Refresh</button>
      </div>

      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: '10px 12px', background: 'rgba(255,255,255,0.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 800, fontSize: 12 }}>Core</div>
            {badge(toStatus(coreObj.healthy ?? coreObj.status))}
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {(typeof coreObj.timestamp === 'string' ? coreObj.timestamp : null) ?? '—'}
          </div>
        </div>

        <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: '10px 12px', background: 'rgba(255,255,255,0.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 800, fontSize: 12 }}>Crew Orchestrator</div>
            {badge(orchStatus)}
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {orchDetail}
          </div>
        </div>

        <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: '10px 12px', background: 'rgba(255,255,255,0.03)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 800, fontSize: 12 }}>Healer</div>
            {badge(toStatus(healerObj.status ?? healerObj.healer ?? healerObj.healthy))}
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {(typeof healerObj.timestamp === 'string' ? healerObj.timestamp : null) ?? '—'}
          </div>
        </div>
      </div>

      {!!orchestrator && typeof orchestrator === 'object' && !Array.isArray(orchestrator) && (
        <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: '10px 12px', background: 'rgba(255,255,255,0.02)' }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 6 }}>
            Services
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(orchestrator as Record<string, unknown>).slice(0, 50).map(([name, info]) => (
              <div key={name} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)' }}>{name}</span>
                {badge(toStatus((asRecord(info)?.status ?? info)))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
