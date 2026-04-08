'use client'

import React from 'react'
import { useMetrics } from '@/hooks/useMetrics'

export function MetricsView(): React.JSX.Element {
  const { metrics, loading } = useMetrics()

  if (loading) return <div style={{ color: 'var(--text-secondary)', padding: 16 }}>\u23F3 Loading metrics...</div>

  const rows = [
    { label: 'API Requests/min',  value: metrics?.requestsPerMin  ?? '—', colour: 'var(--accent-cyan)'   },
    { label: 'Avg Response (ms)', value: metrics?.avgResponseMs   ?? '—', colour: 'var(--accent-green)'  },
    { label: 'Heals Today',       value: metrics?.healsToday      ?? '—', colour: 'var(--accent-amber)'  },
    { label: 'Error Rate (%)',    value: metrics?.errorRatePct    ?? '—', colour: metrics?.errorRatePct && Number(metrics.errorRatePct) > 5 ? 'var(--status-error)' : 'var(--status-healthy)' },
    { label: 'Active Agents',     value: metrics?.activeAgents    ?? '—', colour: 'var(--accent-purple)' },
    { label: 'Redis Queue Depth', value: metrics?.redisQueueDepth ?? '—', colour: 'var(--text-secondary)'},
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} data-testid="metrics">
      {rows.map((r) => (
        <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid var(--pane-border)' }}>
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{r.label}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: r.colour, fontFamily: 'var(--font-mono)' }}>{r.value}</span>
        </div>
      ))}
    </div>
  )
}
