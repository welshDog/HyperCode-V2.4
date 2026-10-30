// Polling is the reliable status source; WebSocket remains an optional low-latency path.
import { useEffect, useState } from 'react'
import { fetchAgents } from '@/lib/api'

const POLL_INTERVAL_MS = 5_000
interface Agent {
  id: string
  name: string
  status: 'idle' | 'thinking' | 'working' | 'error' | 'online' | 'offline' | 'busy'
  lastActivity?: string
  last_seen?: string
  skills?: string[]
}
interface UseAgentStatusReturn { agents: Agent[]; connected: boolean; error: string | null }

function normaliseStatus(raw: unknown): Agent['status'] {
  const s = typeof raw === 'string' ? raw.toLowerCase() : ''
  if (['idle', 'thinking', 'working', 'busy', 'error', 'online', 'offline'].includes(s)) return s as Agent['status']
  if (['healthy', 'ok', 'up'].includes(s)) return 'online'
  if (['warning', 'warn', 'degraded'].includes(s)) return 'busy'
  if (['down', 'unhealthy', 'failed'].includes(s)) return 'offline'
  return 'online'
}
function normaliseAgent(raw: unknown): Agent | null {
  if (!raw || typeof raw !== 'object') return null
  const a = raw as Record<string, unknown>
  const id = typeof a.id === 'string' && a.id ? a.id : typeof a.name === 'string' ? a.name : ''
  const name = typeof a.name === 'string' && a.name ? a.name : id
  if (!id || !name) return null
  return {
    id, name, status: normaliseStatus(a.status),
    lastActivity: typeof a.lastActivity === 'string' ? a.lastActivity : typeof a.last_action === 'string' ? a.last_action : undefined,
    last_seen: typeof a.last_seen === 'string' ? a.last_seen : undefined,
    skills: Array.isArray(a.skills) ? a.skills.filter((s): s is string => typeof s === 'string') : undefined,
  }
}
function wsUrl(): string {
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
  const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000'
  const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${host}:${port}/api/v1/ws/agents`
}

export function useAgentStatus(): UseAgentStatusReturn {
  const [agents, setAgents] = useState<Agent[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let ws: WebSocket | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let delay = 3000
    let destroyed = false
    const seed = async () => {
      try {
        const data: unknown = await fetchAgents()
        const obj = data && typeof data === 'object' ? data as Record<string, unknown> : null
        const raw: unknown[] = Array.isArray(obj?.agents) ? obj.agents : Array.isArray(data) ? data : []
        if (!destroyed) {
          setAgents(raw.map(normaliseAgent).filter((x): x is Agent => x !== null))
          setError(null)
        }
      } catch (e) { if (!destroyed) setError(e instanceof Error ? e.message : 'Failed to load agents') }
    }
    const connect = () => {
      if (destroyed) return
      try {
        ws = new WebSocket(wsUrl())
        ws.onopen = () => { delay = 3000; setConnected(true); setError(null) }
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            const raw: unknown[] = Array.isArray(data?.agents) ? data.agents : []
            setAgents(raw.map(normaliseAgent).filter((x): x is Agent => x !== null))
          } catch { setError('Could not parse live agent data') }
        }
        ws.onerror = () => { setError(`Live updates unavailable; retrying in ${Math.round(delay / 1000)}s`) }
        ws.onclose = () => {
          setConnected(false)
          if (!destroyed) retryTimer = setTimeout(() => { delay = Math.min(delay * 2, 30_000); connect() }, delay)
        }
      } catch {
        setConnected(false)
        if (!destroyed) retryTimer = setTimeout(() => { delay = Math.min(delay * 2, 30_000); connect() }, delay)
      }
    }
    void seed()
    connect()
    const poll = setInterval(seed, POLL_INTERVAL_MS)
    return () => { destroyed = true; if (retryTimer) clearTimeout(retryTimer); clearInterval(poll); ws?.close() }
  }, [])
  return { agents, connected, error }
}
