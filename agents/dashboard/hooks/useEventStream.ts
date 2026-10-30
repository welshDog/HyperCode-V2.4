'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { AgentEvent } from '@/types/event'

const MAX_EVENTS = 200
const INITIAL_RECONNECT_DELAY = 2_000
const MAX_RECONNECT_DELAY = 30_000
const PING_INTERVAL = 25_000

function wsUrl(): string | null {
  if (typeof window === 'undefined') return null
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000'
  return `${protocol}//${window.location.hostname}:${port}/api/v1/ws/events`
}

function toAgentEvent(channel: string, data: Record<string, unknown>): AgentEvent | null {
  if (channel !== 'ws_tasks') return null
  const rawStatus = String(data.status ?? '').toLowerCase().trim()
  const status: AgentEvent['status'] = ['success', 'ok', 'healthy'].includes(rawStatus) ? 'success'
    : ['failed', 'error', 'unhealthy', 'down'].includes(rawStatus) ? 'failed'
      : ['healing', 'warning', 'warn', 'degraded'].includes(rawStatus) ? 'healing' : 'started'
  return {
    agentId: String(data.agent_id ?? data.agentId ?? 'system'),
    taskId: String(data.task_id ?? data.taskId ?? ''),
    status, rawStatus: rawStatus || undefined,
    payload: (data.payload as Record<string, unknown>) ?? {},
    errorTrace: data.error_trace ? String(data.error_trace) : undefined,
    xpEarned: Number(data.xp_earned ?? data.xpEarned ?? 0),
    timestamp: String(data.timestamp ?? new Date().toISOString()),
  }
}

export function useEventStream() {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const connectRef = useRef<() => void>(() => {})
  const delayRef = useRef(INITIAL_RECONNECT_DELAY)
  const stoppedRef = useRef(false)

  const connect = useCallback(() => {
    const url = wsUrl()
    if (!url || stoppedRef.current) return
    let ws: WebSocket
    try { ws = new WebSocket(url) } catch {
      retryRef.current = setTimeout(() => connectRef.current(), delayRef.current)
      delayRef.current = Math.min(delayRef.current * 2, MAX_RECONNECT_DELAY)
      return
    }
    wsRef.current = ws
    ws.onopen = () => {
      delayRef.current = INITIAL_RECONNECT_DELAY
      setConnected(true)
      if (pingRef.current) clearInterval(pingRef.current)
      pingRef.current = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send('ping') }, PING_INTERVAL)
    }
    ws.onmessage = (e: MessageEvent) => {
      try {
        const msg: { channel: string; data: Record<string, unknown> } = JSON.parse(e.data)
        const event = toAgentEvent(msg.channel, msg.data)
        if (event) setEvents((prev) => [...prev.slice(-MAX_EVENTS + 1), event])
      } catch { /* ignore malformed frames */ }
    }
    ws.onclose = () => {
      setConnected(false)
      if (pingRef.current) clearInterval(pingRef.current)
      if (!stoppedRef.current) {
        retryRef.current = setTimeout(() => connectRef.current(), delayRef.current)
        delayRef.current = Math.min(delayRef.current * 2, MAX_RECONNECT_DELAY)
      }
    }
    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    stoppedRef.current = false
    connectRef.current = connect
    connect()
    return () => {
      stoppedRef.current = true
      if (retryRef.current) clearTimeout(retryRef.current)
      if (pingRef.current) clearInterval(pingRef.current)
      wsRef.current?.close()
    }
  }, [connect])
  return { events, connected }
}
