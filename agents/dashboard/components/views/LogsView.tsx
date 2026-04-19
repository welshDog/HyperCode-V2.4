'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useLogs, levelColour } from '@/hooks/useLogs'
import { useToast } from '@/components/ui/ToastProvider'

type LogsFilter = 'all' | 'problems' | 'success'
type WrapMode = 'scan' | 'wrap'

function formatRelative(ms: number, nowMs: number): string {
  const delta = Math.max(0, nowMs - ms)
  if (delta < 1000) return 'now'
  const s = Math.floor(delta / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

function levelIcon(level: string): string {
  if (level === 'debug') return '·'
  if (level === 'info') return 'i'
  if (level === 'warn') return '!'
  if (level === 'error') return '×'
  if (level === 'fatal') return '☠'
  if (level === 'success') return '✓'
  return '·'
}

export function LogsView(): React.JSX.Element {
  const { logs, loading, liveWs } = useLogs(80)
  const scrollerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const { toast } = useToast()
  const [filter, setFilter] = useState<LogsFilter>('all')
  const [levelExact, setLevelExact] = useState<string>('any')
  const [source, setSource] = useState<string>('all')
  const [wrapMode, setWrapMode] = useState<WrapMode>('scan')
  const [pinned, setPinned] = useState(true)
  const [nowMs, setNowMs] = useState(() => Date.now())

  // Track previous connection state to notify when live stream connects/drops
  const prevLiveWs = useRef(liveWs)
  useEffect(() => {
    if (prevLiveWs.current === false && liveWs === true) {
      toast({ type: 'success', message: '✅ Live logs connected' })
    } else if (prevLiveWs.current === true && liveWs === false) {
      toast({ type: 'error', message: '❌ Live logs disconnected, polling...' })
    }
    prevLiveWs.current = liveWs
  }, [liveWs, toast])

  useEffect(() => {
    if (!pinned) return
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ block: 'end' })
    }
  }, [logs, pinned])

  useEffect(() => {
    const t = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(t)
  }, [])

  const sources = useMemo(() => {
    const set = new Set<string>()
    for (const l of logs) {
      if (l.agent) set.add(l.agent)
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b))
  }, [logs])

  const filtered = useMemo(() => {
    const problems = (lvl: string) => lvl === 'warn' || lvl === 'error' || lvl === 'fatal'
    return logs.filter((l) => {
      if (source !== 'all' && l.agent !== source) return false
      if (levelExact !== 'any' && l.level !== levelExact) return false
      if (filter === 'success') return l.level === 'success'
      if (filter === 'problems') return problems(l.level)
      return true
    })
  }, [filter, levelExact, logs, source])

  if (loading) {
    return (
      <div className="hc-logs" data-testid="logs-view" aria-busy="true">
        <div className="hc-logs-head">
          <div className="hc-logs-left">
            <span className={`hc-conn ${liveWs ? 'ok' : 'bad'}`}>
              <span className="hc-conn-dot" aria-hidden="true" />
              {liveWs ? 'Live' : 'Polling'}
            </span>
            <span className="hc-logs-pin on">Pinned</span>
          </div>
          <div className="hc-logs-controls">
            <button type="button" className="btn" disabled aria-disabled="true">Copy</button>
            <button type="button" className="btn" disabled aria-disabled="true">Wrap</button>
          </div>
        </div>
        <div className="hc-logs-body">
          <div className="hc-logs-list">
            {Array.from({ length: 10 }).map((_, idx) => (
              <div key={idx} className="hc-logs-row hc-skeleton" aria-hidden="true" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast({ type: 'success', message: 'Copied' })
      return
    } catch {
      try {
        const el = document.createElement('textarea')
        el.value = text
        el.style.position = 'fixed'
        el.style.left = '-9999px'
        document.body.appendChild(el)
        el.select()
        document.execCommand('copy')
        document.body.removeChild(el)
        toast({ type: 'success', message: 'Copied' })
      } catch {
        toast({ type: 'error', message: 'Copy failed' })
      }
    }
  }

  return (
    <div className={`hc-logs ${wrapMode === 'wrap' ? 'wrap' : 'scan'}`} data-testid="logs-view">
      <div className="hc-logs-head">
        <div className="hc-logs-left">
          <span className={`hc-conn ${liveWs ? 'ok' : 'bad'}`} aria-label={liveWs ? 'Connected' : 'Disconnected'}>
            <span className="hc-conn-dot" aria-hidden="true" />
            {liveWs ? 'Live' : 'Polling'}
          </span>
          <span className={`hc-logs-pin ${pinned ? 'on' : 'off'}`}>
            {pinned ? 'Pinned' : 'Paused'}
          </span>
        </div>

        <div className="hc-logs-controls" role="group" aria-label="Log controls">
          <button type="button" className={`btn${filter === 'all' ? ' active' : ''}`} aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>
            All
          </button>
          <button type="button" className={`btn${filter === 'problems' ? ' active' : ''}`} aria-pressed={filter === 'problems'} onClick={() => setFilter('problems')}>
            Problems
          </button>
          <button type="button" className={`btn${filter === 'success' ? ' active' : ''}`} aria-pressed={filter === 'success'} onClick={() => setFilter('success')}>
            Success
          </button>

          <label className="hc-logs-select">
            <span className="hc-logs-select-label">Level</span>
            <select value={levelExact} onChange={(e) => setLevelExact(e.target.value)} className="hc-logs-select-input" aria-label="Filter by severity">
              <option value="any">Any</option>
              <option value="fatal">FATAL</option>
              <option value="error">ERROR</option>
              <option value="warn">WARN</option>
              <option value="info">INFO</option>
              <option value="debug">DEBUG</option>
              <option value="success">SUCCESS</option>
            </select>
          </label>

          <label className="hc-logs-select">
            <span className="hc-logs-select-label">Source</span>
            <select value={source} onChange={(e) => setSource(e.target.value)} className="hc-logs-select-input" aria-label="Filter by source">
              <option value="all">All</option>
              {sources.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>

          <button
            type="button"
            className="btn"
            onClick={() => setWrapMode((m) => (m === 'scan' ? 'wrap' : 'scan'))}
            aria-pressed={wrapMode === 'wrap'}
            aria-label="Toggle line wrapping"
            title={wrapMode === 'wrap' ? 'Read mode (wrapped)' : 'Scan mode (truncated)'}
          >
            {wrapMode === 'wrap' ? 'Wrap' : 'Scan'}
          </button>

          <button
            type="button"
            className="btn"
            onClick={() => copyText(filtered.map((l) => `[${new Date(l.timestampMs).toISOString()}] ${l.level.toUpperCase()} ${l.agent}: ${l.msg}`).join('\n'))}
            aria-label="Copy visible logs"
          >
            Copy
          </button>

          {!pinned && (
            <button
              type="button"
              className="btn"
              onClick={() => {
                setPinned(true)
                if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
                  bottomRef.current.scrollIntoView({ block: 'end' })
                }
              }}
              aria-label="Scroll to latest logs"
            >
              ↓ Latest
            </button>
          )}
        </div>
      </div>

      <div
        ref={scrollerRef}
        className="hc-logs-body"
        onScroll={() => {
          const el = scrollerRef.current
          if (!el) return
          const distanceFromBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
          setPinned(distanceFromBottom < 24)
        }}
      >
        {filtered.length === 0 ? (
          <div className="hc-logs-empty">
            <div className="hc-logs-empty-title">
              <span className="hc-pulse-dot" aria-hidden="true" />
              No logs yet — waiting for activity…
            </div>
            <div className="hc-logs-empty-subtitle">When Prometheus alerts or agents talk, it will show up here.</div>
          </div>
        ) : (
          <div className="hc-logs-list" role="list" aria-label="System logs">
            {filtered.map((entry, i) => {
              const abs = new Date(entry.timestampMs)
              const absText = Number.isNaN(abs.getTime()) ? entry.time : abs.toISOString()
              const rel = formatRelative(entry.timestampMs, nowMs)
              const lvl = entry.level.toUpperCase()
              const icon = levelIcon(entry.level)
              return (
                <div key={entry.id ?? i} className="hc-logs-row" role="listitem">
                  <span className="hc-logs-time hc-mono" title={absText}>{rel}</span>
                  <span className="hc-logs-level hc-mono" style={{ color: levelColour(entry.level) }} title={lvl}>
                    <span className="hc-logs-level-icon" aria-hidden="true">{icon}</span>
                    {lvl}
                  </span>
                  <span className="hc-logs-agent hc-mono" title={entry.agent}>{entry.agent}</span>
                  <span className="hc-logs-msg" title={wrapMode === 'scan' ? entry.msg : undefined}>{entry.msg}</span>
                  <button
                    type="button"
                    className="hc-logs-copy"
                    onClick={() => copyText(`[${absText}] ${lvl} ${entry.agent}: ${entry.msg}`)}
                    aria-label="Copy log line"
                    title="Copy line"
                  >
                    ⧉
                  </button>
                </div>
              )
            })}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
