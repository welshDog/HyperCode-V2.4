'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useToast } from '@/components/ui/ToastProvider'
import { useDockerServices } from '@/hooks/useDockerServices'
import { OfflineAgentsPanel } from '@/components/panels/OfflineAgentsPanel'
import { KNOWN_SERVICES } from '@/data/knownServices'

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
  const { services, loading: servicesLoading, error: servicesError, refetch: refetchServices } = useDockerServices(15_000)

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

  const coreObj = asRecord(core) ?? {}
  const orchObj = asRecord(orchestrator) ?? {}
  const healerObj = asRecord(healer) ?? {}
  const orchStatus = toStatus(orchObj.status ?? orchObj.healthy)
  const orchDetail = orchStatus === 'unknown'
    ? `Unreachable — start crew-orchestrator${orchObj.error ? ` (${String(orchObj.error).slice(0, 60)})` : ''}`
    : (orchObj.error ? String(orchObj.error).slice(0, 80) : '—')

  const knownRows = useMemo(() => {
    return KNOWN_SERVICES.map((svc) => {
      const direct = services[svc.name]
      const alt = services[svc.name.replace(/_/g, '-')] ?? services[svc.name.replace(/-/g, '_')]
      const h = direct ?? alt
      const s = toStatus(h?.status)
      return {
        name: svc.name,
        label: svc.label,
        group: svc.group,
        status: s,
        latency_ms: typeof h?.latency_ms === 'number' ? h?.latency_ms : null,
        last_checked: typeof h?.last_checked === 'string' ? h?.last_checked : null,
        color: svc.color,
      }
    })
  }, [services])

  const groups = useMemo(() => {
    const order: Array<(typeof KNOWN_SERVICES)[number]['group']> = ['infra', 'core', 'observability', 'proxy', 'agent']
    const by = knownRows.reduce<Record<string, typeof knownRows>>((acc, row) => {
      const k = row.group
      if (!acc[k]) acc[k] = []
      acc[k].push(row)
      return acc
    }, {})
    return order.map((g) => ({ group: g, rows: by[g] ?? [] }))
  }, [knownRows])

  const initialLoading = loading && !core && !orchestrator && !healer

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {initialLoading && (
        <div style={{ color: 'var(--text-secondary)', padding: 16 }}>⏳ Loading health…</div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Live checks via <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>/api/*</span>
          {' '}+ Docker feed via <span style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>/api/v1/orchestrator/system/health</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={() => load(true)}>↻ Refresh</button>
          <button className="btn" onClick={() => refetchServices()}>↻ Services</button>
        </div>
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

      <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: '10px 12px', background: 'rgba(255,255,255,0.02)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
            Services (Docker)
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {servicesError && (
              <span style={{ fontSize: 10, color: 'var(--status-error)', fontFamily: 'var(--font-mono)' }}>
                {servicesError.slice(0, 80)}
              </span>
            )}
            <span style={{ fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              {servicesLoading ? 'polling…' : `${Object.keys(services).length} containers`}
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {groups.map(({ group, rows }) => (
                <div key={group} style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: 10, background: 'rgba(255,255,255,0.02)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                      {group}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      {rows.length}
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {rows.map((row) => (
                      <div key={row.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {row.name}
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {row.label}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                          {row.latency_ms != null && (
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
                              {Math.round(row.latency_ms)}ms
                            </span>
                          )}
                          {badge(row.status)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: 10, background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>
                Offline Agents (compose vs live)
              </div>
              <OfflineAgentsPanel services={services} loading={servicesLoading} />
            </div>
            <div style={{ border: '1px solid var(--pane-border)', borderRadius: 8, padding: 10, background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 6 }}>
                Last Checked
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-secondary)' }}>
                {knownRows.find((r) => r.last_checked)?.last_checked ?? '—'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
