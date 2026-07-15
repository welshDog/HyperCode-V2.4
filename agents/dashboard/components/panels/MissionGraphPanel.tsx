'use client'

import React from 'react'
import { useMissionGraph } from '@/hooks/useMissionGraph'
import type { FlowTransition } from '@/lib/api'

// Node/status colour map (per P0-3 spec).
const RED = '#ef4444'
const GREEN = '#22c55e'
const YELLOW = '#eab308'
const BLUE = '#3b82f6'
const SLATE = '#64748b'

function statusColor(status: string): string {
  const s = (status || '').toLowerCase()
  if (s.includes('fail') || s === 'safety_block') return RED
  if (s === 'completed' || s === 'safety_allow' || s === 'safety_resolved') return GREEN
  if (s.includes('await') || s.includes('escalate')) return YELLOW
  if (s === 'running' || s === 'started') return BLUE
  return SLATE
}

function statusLabel(status: string): string {
  return (status || '').replace(/_/g, ' ')
}

function fmtTime(ts?: string): string {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function StatusBadge({ status }: { status: string }): React.JSX.Element {
  const c = statusColor(status)
  return (
    <span
      style={{
        color: c,
        border: `1px solid ${c}55`,
        background: `${c}1a`,
        borderRadius: 6,
        padding: '2px 8px',
        fontSize: 12,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: 0.4,
      }}
    >
      {statusLabel(status)}
    </span>
  )
}

function TransitionRow({ t, active }: { t: FlowTransition; active: boolean }): React.JSX.Element {
  const c = statusColor(t.status)
  return (
    <li
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 10px',
        borderRadius: 8,
        background: active ? `${BLUE}14` : 'transparent',
        border: active ? `1px solid ${BLUE}44` : '1px solid transparent',
      }}
    >
      <span
        aria-hidden
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: c,
          boxShadow: `0 0 8px ${c}`,
          flexShrink: 0,
        }}
      />
      <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 600, minWidth: 0, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {t.node ?? '∎ flow'}
      </span>
      <span style={{ color: c, fontSize: 12, fontWeight: 600 }}>{statusLabel(t.status)}</span>
      <span style={{ color: SLATE, fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>{fmtTime(t.ts)}</span>
    </li>
  )
}

export function MissionGraphPanel(): React.JSX.Element {
  const { run, connected, activeCount } = useMissionGraph()

  if (!run) {
    return (
      <div style={{ padding: 24, color: SLATE, textAlign: 'center' }}>
        <div style={{ fontSize: 32, marginBottom: 8 }}>🕸️</div>
        <div style={{ fontWeight: 600, color: '#cbd5e1' }}>No active mission flows</div>
        <div style={{ fontSize: 13, marginTop: 6 }}>
          Start one: <code>POST /api/v1/flows/runs</code> · then it streams here live.
        </div>
      </div>
    )
  }

  const history = run.history ?? []
  const last = history.length ? history[history.length - 1] : undefined
  const lastTs = last?.ts ?? run.updated_at ?? run.created_at ?? undefined

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, padding: 4 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12, flexWrap: 'wrap' }}>
        <span
          aria-label={connected ? 'live' : 'offline'}
          title={connected ? 'Live (SSE)' : 'Reconnecting…'}
          style={{
            width: 9, height: 9, borderRadius: '50%',
            background: connected ? GREEN : SLATE,
            boxShadow: connected ? `0 0 8px ${GREEN}` : 'none',
          }}
        />
        <span style={{ fontWeight: 700, fontSize: 16 }}>{run.flow}</span>
        <StatusBadge status={run.status} />
        {activeCount > 1 && (
          <span style={{ color: SLATE, fontSize: 12 }}>+{activeCount - 1} more active</span>
        )}
      </div>

      {/* Summary */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap', fontSize: 13 }}>
        <div>
          <span style={{ color: SLATE }}>Active node: </span>
          <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 600, color: run.current_node ? BLUE : SLATE }}>
            {run.current_node ?? '— done'}
          </span>
        </div>
        <div>
          <span style={{ color: SLATE }}>Last transition: </span>
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{fmtTime(lastTs)}</span>
        </div>
      </div>

      {run.error && (
        <div style={{ color: RED, fontSize: 12, marginBottom: 10, fontFamily: 'var(--font-mono, monospace)' }}>
          ⚠ {run.error}
        </div>
      )}

      {/* Timeline (most recent last) */}
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 4, overflowY: 'auto', minHeight: 0 }}>
        {history.length === 0 && (
          <li style={{ color: SLATE, fontSize: 13, padding: 8 }}>Waiting for first transition…</li>
        )}
        {history.map((t, i) => (
          <TransitionRow key={`${t.node ?? 'flow'}-${i}`} t={t} active={t.node === run.current_node && i === history.length - 1} />
        ))}
      </ul>

      <div style={{ marginTop: 10, color: SLATE, fontSize: 11, fontFamily: 'var(--font-mono, monospace)' }}>
        run {run.run_id.slice(0, 8)}…
      </div>
    </div>
  )
}
