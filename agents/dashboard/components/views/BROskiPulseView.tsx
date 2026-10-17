'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { useAgentSwarm } from '@/hooks/useAgentSwarm'

type BroskiPulse = {
  coins?: number
  xp?: number
  level?: number
  level_name?: string
  error?: string
}

export function BROskiPulseView(): React.JSX.Element {
  const { agents } = useAgentSwarm()

  const [pulse, setPulse] = useState<BroskiPulse | null>(null)
  const [pulseError, setPulseError] = useState<string | null>(null)

  // /api/broski can 503 while core is busy (first load of the Mission page). One failed attempt used to leave the panel at 0 forever,
  // so retry a few times with a growing delay and refresh every 30s afterwards.
  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let attempt = 0
    const load = async () => {
      const controller = new AbortController()
      const t = setTimeout(() => controller.abort(), 8_000)
      let ok = false
      try {
        const r = await fetch('/api/broski', { signal: controller.signal })
        const data: BroskiPulse = await r.json()
        if (cancelled) return
        ok = r.ok && !data?.error
        setPulse(data)
        setPulseError(data?.error ? String(data.error) : r.ok ? null : `HTTP ${r.status}`)
      } catch (e) {
        if (!cancelled) setPulseError(e instanceof Error ? e.message : String(e))
      } finally {
        clearTimeout(t)
      }
      if (cancelled) return
      attempt = ok ? 0 : attempt + 1
      timer = setTimeout(load, ok ? 30_000 : Math.min(2_000 * 2 ** attempt, 20_000))
    }
    load()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [])

  // "Total XP" is the user's real BROski XP from /api/broski (it sat in `pulse.xp`, unused: the panel showed the SUM of the
  // agents' own XP, which is 0 because the registry reports no per-agent XP). Falls back to the agent sum if /api/broski failed.
  const agentXp = useMemo(() => agents.reduce((s, a) => s + (a.xp ?? 0), 0), [agents])
  const totalXP = typeof pulse?.xp === 'number' && Number.isFinite(pulse.xp) ? pulse.xp : agentXp
  const topAgent = useMemo(() => {
    if (agents.length === 0) return null
    return [...agents].sort((a, b) => (b.xp ?? 0) - (a.xp ?? 0))[0] ?? null
  }, [agents])
  const healthyCount = useMemo(() => agents.filter((a) => a.status === 'healthy').length, [agents])
  const coins = typeof pulse?.coins === 'number' && Number.isFinite(pulse.coins) ? pulse.coins : 0

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, height: '100%' }} data-testid="broski-pulse">
      {[
        { label: '\uD83D\uDCB0 BROski$',   value: coins, colour: 'var(--accent-amber)'  },
        { label: '\uD83E\uDDEB Total XP',   value: totalXP,    colour: 'var(--accent-purple)' },
        { label: '\uD83D\uDFE2 Healthy',    value: `${healthyCount}/${agents.length}`, colour: 'var(--status-healthy)' },
        { label: '\uD83E\uDD47 Top Agent',  value: topAgent?.name ?? '—', colour: 'var(--accent-cyan)' },
      ].map((stat) => (
        <div
          key={stat.label}
          style={{
            background:   'rgba(255,255,255,0.03)',
            border:       '1px solid var(--pane-border)',
            borderRadius: 6,
            padding:      '8px 10px',
            display:      'flex',
            flexDirection: 'column',
            gap:          4,
          }}
        >
          <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{stat.label}</span>
          <span style={{ fontSize: 18, fontWeight: 700, color: stat.colour, fontFamily: 'var(--font-mono)' }}>
            {stat.value}
          </span>
        </div>
      ))}
      {pulseError && (
        <div
          style={{
            gridColumn: '1 / -1',
            background: 'rgba(255,68,102,0.08)',
            border: '1px solid rgba(255,68,102,0.35)',
            borderRadius: 6,
            padding: '8px 10px',
            fontSize: 10,
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          ⚠️ BROski pulse degraded: {pulseError}
        </div>
      )}
    </div>
  )
}
