'use client'

import React, { useEffect, useRef } from 'react'
import type { Decision, StreamItem } from '@/hooks/useStudioSession'

const VERDICT: Record<Decision, { color: string; glyph: string }> = {
  ALLOW: { color: 'var(--accent-green)', glyph: '✓' }, // ✓
  BLOCK: { color: 'var(--accent-red)', glyph: '✕' }, // ✕
  ESCALATE: { color: 'var(--accent-amber)', glyph: '⚠' }, // ⚠
}

function Row({ item }: { item: StreamItem }): React.JSX.Element | null {
  if (item.kind === 'decision') {
    const v = VERDICT[item.decision]
    return (
      <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', padding: '2px 0' }}>
        <span aria-hidden style={{ color: v.color, width: 14, flexShrink: 0 }}>{v.glyph}</span>
        <span style={{ color: v.color, fontWeight: 600, letterSpacing: '0.02em' }}>
          {item.decision}
        </span>
        <span style={{ color: 'var(--text-secondary)' }}>{item.tool}</span>
        <span style={{ color: 'var(--text-secondary)', opacity: 0.7 }}>— {item.reason || item.rule}</span>
      </div>
    )
  }

  if (item.kind === 'error') {
    return (
      <div style={{ display: 'flex', gap: 8, padding: '2px 0', color: 'var(--accent-red)' }}>
        <span aria-hidden style={{ width: 14, flexShrink: 0 }}>{'✗'}</span>
        <span>{item.error}</span>
      </div>
    )
  }

  if (item.kind === 'status') {
    return (
      <div style={{ padding: '4px 0', color: 'var(--accent-cyan)', opacity: 0.75 }}>
        <span aria-hidden>{'›'}</span> {item.status}
      </div>
    )
  }

  if (item.kind === 'approval_request' || item.kind === 'approval_resolved') {
    // Surfaced as an actionable approval card in the Task pane, not in the log
    // feed. The preceding ESCALATE `decision` line already marks it here.
    return null
  }

  // message
  if (item.role === 'tool_use') {
    return (
      <div style={{ display: 'flex', gap: 8, padding: '2px 0', color: 'var(--text-secondary)' }}>
        <span aria-hidden style={{ width: 14, flexShrink: 0, opacity: 0.6 }}>{'⚙'}</span>
        <span>
          <span style={{ color: 'var(--accent-cyan)' }}>{item.tool}</span>
          <span style={{ opacity: 0.6 }}>({shortInput(item.input)})</span>
        </span>
      </div>
    )
  }
  if (item.role === 'result') {
    return (
      <div style={{ padding: '4px 0', color: 'var(--text-secondary)', opacity: 0.7 }}>
        {'—'} run complete
        {typeof item.cost_usd === 'number' && item.cost_usd > 0 && (
          <span style={{ color: 'var(--accent-amber)', marginLeft: 8 }}>${item.cost_usd.toFixed(4)}</span>
        )}
      </div>
    )
  }
  return (
    <div style={{ padding: '2px 0', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
      {item.text}
    </div>
  )
}

function shortInput(input: unknown): string {
  if (!input || typeof input !== 'object') return ''
  const obj = input as Record<string, unknown>
  const key = obj.file_path ?? obj.path ?? obj.command ?? obj.pattern
  return typeof key === 'string' ? key.slice(0, 48) : ''
}

export function StreamFeed({ items, live }: { items: StreamItem[]; live: boolean }): React.JSX.Element {
  const endRef = useRef<HTMLDivElement | null>(null)

  // Follow the tail as the agent works.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [items.length])

  return (
    <div
      role="log"
      aria-live="polite"
      aria-label="Agent activity"
      style={{
        height: '100%',
        overflow: 'auto',
        background: 'rgba(0,0,0,0.35)',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 6,
        padding: '10px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        lineHeight: 1.7,
      }}
    >
      {items.length === 0 ? (
        <div style={{ color: 'var(--text-secondary)', opacity: 0.6 }}>
          {live
            ? <>Waiting for the agent<span className="studio-caret">{'█'}</span></>
            : 'Hand the agent a task above and watch it work — every tool call is gated by Safety Shepherd.'}
        </div>
      ) : (
        items.map((item) => <Row key={item.seq} item={item} />)
      )}
      <div ref={endRef} />
    </div>
  )
}
