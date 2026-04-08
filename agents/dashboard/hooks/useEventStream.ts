'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { AgentEvent } from '@/types/event'

const MAX_EVENTS       = 200
const RECONNECT_DELAY  = 3_000   // ms before reconnect attempt
const PING_INTERVAL    = 25_000  // ms between keep-alive pings

// Resolve WS URL: browser connects directly to FastAPI backend (port 8000).
// In SSR/test context we return null.
function wsUrl(): string | null {
  if (typeof window === 'undefined') return null
  const host = process.env.NEXT_PUBLIC_CORE_WS_HOST ?? window.location.hostname
  const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000'
  return `ws://${host}:${port}/api/v1/ws/events`
}

/** Normalise a raw ws_tasks message into an AgentEvent, or return null. */
function toAgentEvent(channel: string, data: Record<string, unknown>): AgentEvent | null {
  if (channel !== 'ws_tasks') return null
  // Orchestrator publishes task payloads — map known fields
  return {
    agentId:   String(data.agent_id   ?? data.agentId   ?? 'system'),
    taskId:    String(data.task_id    ?? data.taskId    ?? ''),
    status:    (data.status as AgentEvent['status']) ?? 'started',
    payload:   (data.payload as Record<string, unknown>) ?? {},
    errorTrace: data.error_trace ? String(data.error_trace) : undefined,
    xpEarned:  Number(data.xp_earned  ?? data.xpEarned  ?? 0),
    timestamp: String(data.timestamp  ?? new Date().toISOString()),
  }
}

export function useEventStream() {
  const [events, setEvents]       = useState<AgentEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef                     = useRef<WebSocket | null>(null)
  const pingRef                   = useRef<ReturnType<typeof setInterval> | null>(null)
  const retryRef                  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const connectRef                = useRef<() => void>(() => {})

  const connect = useCallback(() => {
    const url = wsUrl()
    if (!url) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // Keep-alive ping so the connection survives idle periods
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, PING_INTERVAL)
    }

    ws.onmessage = (e: MessageEvent) => {
      try {
        const msg: { channel: string; data: Record<string, unknown> } = JSON.parse(e.data)
        const ev = toAgentEvent(msg.channel, msg.data)
        if (ev) {
          setEvents((prev) => [...prev.slice(-MAX_EVENTS + 1), ev])
        }
      } catch {
        // malformed frame — skip
      }
    }

    ws.onclose = () => {
      setConnected(false)
      if (pingRef.current) clearInterval(pingRef.current)
      // Reconnect after delay
      retryRef.current = setTimeout(() => connectRef.current(), RECONNECT_DELAY)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connectRef.current = connect
    connect()
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      if (pingRef.current)  clearInterval(pingRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { events, connected }
}
