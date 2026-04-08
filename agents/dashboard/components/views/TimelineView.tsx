'use client'

import React, { useEffect, useRef } from 'react'
import { useEventStream } from '@/hooks/useEventStream'
import type { AgentEvent } from '@/types/event'

const STATUS_COLOURS: Record<string, string> = {
  success: 'var(--status-healthy)',
  failed:  'var(--status-error)',
  healing: 'var(--status-warning)',
  started: 'var(--accent-cyan)',
}

export function TimelineView(): React.JSX.Element {
  const { events, connected } = useEventStream()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [events])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }} data-testid="timeline">
      <div style={{ padding: '4px 0 8px', marginBottom: 4, borderBottom: '1px solid var(--pane-border)', fontSize: 10, color: connected ? 'var(--status-healthy)' : 'var(--status-error)' }}>
        {connected ? '\u2022 Live' : '\u25CF Disconnected'}
      </div>
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {events.map((ev: AgentEvent) => (
          <div
            key={ev.taskId}
            style={{
              fontSize:     11,
              borderLeft:   `3px solid ${STATUS_COLOURS[ev.status] ?? 'var(--text-secondary)'}`,
              paddingLeft:  8,
              paddingTop:   2,
              paddingBottom: 2,
            }}
          >
            <span style={{ color: 'var(--text-secondary)', marginRight: 6 }}>
              {new Date(ev.timestamp).toLocaleTimeString()}
            </span>
            <strong style={{ color: 'var(--accent-cyan)' }}>{ev.agentId}</strong>
            {' '}
            <span style={{ color: STATUS_COLOURS[ev.status] ?? 'var(--text-primary)' }}>{ev.status}</span>
            {ev.xpEarned > 0 && (
              <span style={{ color: 'var(--accent-purple)', marginLeft: 6 }}>+{ev.xpEarned} XP</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
