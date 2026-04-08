'use client'

import { useState, useEffect, useRef, useCallback } from 'react'

export interface LogEntry {
  id?: string | number
  time: string
  agent: string
  level: 'info' | 'warn' | 'error' | 'success'
  msg: string
}

const MAX_LOGS        = 200
const RECONNECT_DELAY = 3_000
const PING_INTERVAL   = 25_000
const POLL_FALLBACK   = 8_000   // poll interval when WS unavailable

const LEVEL_COLOUR: Record<string, string> = {
  info:    'var(--accent-cyan)',
  warn:    'var(--accent-amber)',
  error:   'var(--status-error)',
  success: 'var(--status-healthy)',
}

export function levelColour(level: string): string {
  return LEVEL_COLOUR[level] ?? 'var(--text-secondary)'
}

function wsUrl(): string | null {
  if (typeof window === 'undefined') return null
  const host = process.env.NEXT_PUBLIC_CORE_WS_HOST ?? window.location.hostname
  const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000'
  return `ws://${host}:${port}/api/v1/ws/logs`
}

function normaliseEntry(raw: Record<string, unknown>, idx: number): LogEntry {
  return {
    id:    raw.id    != null ? String(raw.id)    : `ws-${Date.now()}-${idx}`,
    time:  String(raw.time  ?? raw.timestamp ?? ''),
    agent: String(raw.agent ?? raw.agentId   ?? 'system'),
    level: (raw.level as LogEntry['level'])  ?? 'info',
    msg:   String(raw.msg   ?? raw.message   ?? ''),
  }
}

export function useLogs(maxEntries = 80) {
  const [logs, setLogs]       = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [liveWs, setLiveWs]   = useState(false)
  const wsRef                 = useRef<WebSocket | null>(null)
  const pingRef               = useRef<ReturnType<typeof setInterval> | null>(null)
  const retryRef              = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollRef               = useRef<ReturnType<typeof setInterval> | null>(null)

  const appendEntry = useCallback((entry: LogEntry) => {
    setLogs((prev) => {
      const next = [...prev, entry]
      return next.length > MAX_LOGS ? next.slice(next.length - MAX_LOGS) : next
    })
  }, [])

  // ── HTTP fallback poll ─────────────────────────────────────────────────────
  const fetchLogs = useCallback(async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch('/api/logs', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        cache: 'no-store',
      })
      if (!res.ok) return
      const data: unknown[] = await res.json()
      if (!Array.isArray(data)) return
      setLogs(data.slice(0, maxEntries).map((r, i) => normaliseEntry(r as Record<string, unknown>, i)))
    } catch {
      // keep stale data
    } finally {
      setLoading(false)
    }
  }, [maxEntries])

  // ── WebSocket live stream ──────────────────────────────────────────────────
  const connect = useCallback(() => {
    const url = wsUrl()
    if (!url) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setLiveWs(true)
      // Cancel HTTP polling — WS takes over
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, PING_INTERVAL)
    }

    ws.onmessage = (e: MessageEvent) => {
      try {
        const msg: { channel: string; data: Record<string, unknown> } = JSON.parse(e.data)
        // Accept both history seed and live log pushes
        if (msg.channel === 'logs:history' || msg.channel === 'logs:live') {
          appendEntry(normaliseEntry(msg.data, Date.now()))
          setLoading(false)
        }
      } catch {
        // skip malformed frames
      }
    }

    ws.onclose = () => {
      setLiveWs(false)
      if (pingRef.current) { clearInterval(pingRef.current); pingRef.current = null }
      // Fall back to polling while reconnecting
      if (!pollRef.current) {
        fetchLogs()
        pollRef.current = setInterval(fetchLogs, POLL_FALLBACK)
      }
      retryRef.current = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = () => ws.close()
  }, [appendEntry, fetchLogs])

  useEffect(() => {
    // Start with an HTTP fetch so there's immediate data, then open WS
    fetchLogs()
    connect()

    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      if (pingRef.current)  clearInterval(pingRef.current)
      if (pollRef.current)  clearInterval(pollRef.current)
      wsRef.current?.close()
    }
  }, [connect, fetchLogs])

  return { logs, loading, liveWs }
}
