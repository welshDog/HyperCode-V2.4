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

  useEffect(() => {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 5_000)
    fetch('/api/broski', { signal: controller.signal })
      .then((r) => r.json())
      .then((data: BroskiPulse) => {
        setPulse(data)
        setPulseError(data?.error ? String(data.error) : null)
      })
      .catch((e) => setPulseError(e instanceof Error ? e.message : String(e)))
      .finally(() => clearTimeout(t))
    return () => {
      clearTimeout(t)
      controller.abort()
    }
  }, [])

  const totalXP = useMemo(() => agents.reduce((s, a) => s + (a.xp ?? 0), 0), [agents])
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
