'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useEventStream } from '@/hooks/useEventStream'
import type { AgentEvent } from '@/types/event'

type TimelineFilter = 'all' | 'problems' | 'success'

function statusColour(status: AgentEvent['status']): string {
  if (status === 'success') return 'var(--status-healthy)'
  if (status === 'failed') return 'var(--status-error)'
  if (status === 'healing') return 'var(--status-warning)'
  return 'var(--accent-cyan)'
}

function formatTime(value: string): string {
  const ts = new Date(value)
  if (Number.isNaN(ts.getTime())) return '--:--:--'
  return ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function asString(v: unknown): string | null {
  const s = typeof v === 'string' ? v.trim() : ''
  return s ? s : null
}

function eventSummary(ev: AgentEvent): string {
  const p = ev.payload ?? {}
  const msg =
    asString(p.message) ??
    asString(p.msg) ??
    asString(p.event) ??
    asString(p.action) ??
    asString(p.detail) ??
    asString(p.reason)
  if (msg) return msg
  if (ev.taskId) return `task ${ev.taskId}`
  return 'event'
}

export function TimelineView(): React.JSX.Element {
  const { events, connected } = useEventStream()
  const scrollerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [filter, setFilter] = useState<TimelineFilter>('all')
  const [pinned, setPinned] = useState(true)

  useEffect(() => {
    if (!pinned) return
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ block: 'end' })
    }
  }, [events, pinned])

  const visibleEvents = useMemo(() => {
    if (filter === 'all') return events
    if (filter === 'success') return events.filter((e) => e.status === 'success')
    return events.filter((e) => e.status === 'failed' || e.status === 'healing')
  }, [events, filter])

  return (
    <div className="hc-timeline" data-testid="timeline">
      <div className="hc-timeline-head">
        <div className="hc-timeline-left">
          <span className={`hc-conn ${connected ? 'ok' : 'bad'}`} aria-label={connected ? 'Connected' : 'Disconnected'}>
            <span className="hc-conn-dot" aria-hidden="true" />
            {connected ? 'Live' : 'Disconnected'}
          </span>
          <span className={`hc-timeline-pin ${pinned ? 'on' : 'off'}`}>
            {pinned ? 'Pinned' : 'Paused'}
          </span>
        </div>
        <div className="hc-timeline-controls" role="group" aria-label="Timeline filters">
          <button type="button" className={`btn${filter === 'all' ? ' active' : ''}`} aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>
            All
          </button>
          <button type="button" className={`btn${filter === 'problems' ? ' active' : ''}`} aria-pressed={filter === 'problems'} onClick={() => setFilter('problems')}>
            Problems
          </button>
          <button type="button" className={`btn${filter === 'success' ? ' active' : ''}`} aria-pressed={filter === 'success'} onClick={() => setFilter('success')}>
            Success
          </button>
          {!pinned && (
            <button
              type="button"
              className="btn"
              onClick={() => {
                setPinned(true)
                bottomRef.current?.scrollIntoView({ block: 'end' })
              }}
              aria-label="Scroll to latest events"
            >
              ↓ Latest
            </button>
          )}
        </div>
      </div>

      <div
        ref={scrollerRef}
        className="hc-timeline-body"
        onScroll={() => {
          const el = scrollerRef.current
          if (!el) return
          const distanceFromBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
          setPinned(distanceFromBottom < 24)
        }}
      >
        {visibleEvents.length === 0 ? (
          <div className="hc-timeline-empty">
            <div className="hc-timeline-empty-title">No events yet</div>
            <div className="hc-timeline-empty-subtitle">Waiting for alerts, tasks, and agent activity.</div>
          </div>
        ) : (
          <div className="hc-timeline-list" role="list" aria-label="Event timeline">
            {visibleEvents.map((ev: AgentEvent, idx) => {
              const key = `${ev.timestamp}:${ev.agentId}:${ev.taskId}:${idx}`
              const colour = statusColour(ev.status)
              const summary = eventSummary(ev)
              const meta = `${ev.agentId} ${ev.status}${ev.taskId ? ` ${ev.taskId}` : ''}`
              return (
                <details key={key} className="hc-timeline-row" role="listitem">
                  <summary className="hc-timeline-summary">
                    <span className="hc-timeline-mark" aria-hidden="true" style={{ background: colour }} />
                    <span className="hc-timeline-time hc-mono">{formatTime(ev.timestamp)}</span>
                    <span className="hc-timeline-agent" title={ev.agentId}>{ev.agentId}</span>
                    <span className="hc-timeline-status hc-mono" style={{ color: colour }} aria-label={`Status ${ev.status}`}>
                      {ev.status}
                    </span>
                    <span className="hc-timeline-msg" title={summary}>{summary}</span>
                    {ev.xpEarned > 0 && (
                      <span className="hc-timeline-xp hc-mono" aria-label={`XP earned ${ev.xpEarned}`}>
                        +{ev.xpEarned} XP
                      </span>
                    )}
                    <span className="hc-timeline-meta hc-mono" aria-label={meta}>
                      {ev.taskId ? `#${ev.taskId}` : ''}
                    </span>
                  </summary>
                  <div className="hc-timeline-details">
                    {ev.rawStatus && ev.rawStatus !== ev.status && (
                      <div className="hc-timeline-detail-line hc-mono">raw_status: {ev.rawStatus}</div>
                    )}
                    {ev.errorTrace && (
                      <pre className="hc-timeline-pre">{ev.errorTrace}</pre>
                    )}
                    <pre className="hc-timeline-pre">{JSON.stringify(ev.payload ?? {}, null, 2)}</pre>
                  </div>
                </details>
              )
            })}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
