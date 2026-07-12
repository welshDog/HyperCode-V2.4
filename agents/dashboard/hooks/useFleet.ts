// Mission Control — live fleet status from the agent-registry (:8077),
// via /api/fleet. Polls every 10s (registry itself scans on a 30s cycle).

import { useEffect, useState } from 'react'

const POLL_INTERVAL_MS = 10_000

export interface FleetAgent {
  name: string
  role: string
  source: string
  status: 'healthy' | 'running' | 'down' | 'not_deployed' | string
  last_ping?: string
  memory_usage_mb?: number
  restart_count?: number
  crashes_in_window?: number
  crash_loop?: boolean
  auto_restarts_issued?: number
}

export interface FleetSummary {
  total: number
  healthy: number
  running: number
  down: number
  not_deployed: number
  crash_looping: number
  auto_restart_enabled: boolean
  generated_at: string
}

interface UseFleetReturn {
  summary: FleetSummary | null
  agents: FleetAgent[]
  error: string | null
  loading: boolean
}

export function useFleet(): UseFleetReturn {
  const [summary, setSummary] = useState<FleetSummary | null>(null)
  const [agents, setAgents] = useState<FleetAgent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let destroyed = false

    const poll = async () => {
      try {
        const res = await fetch('/api/fleet', { cache: 'no-store' })
        const data = await res.json()
        if (destroyed) return
        if (data?.error && !Array.isArray(data?.agents)) throw new Error(data.error)
        setSummary(data?.summary ?? null)
        setAgents(Array.isArray(data?.agents) ? data.agents : [])
        setError(data?.error ?? null)
      } catch (e) {
        if (!destroyed) setError(e instanceof Error ? e.message : 'Fleet fetch failed')
      } finally {
        if (!destroyed) setLoading(false)
      }
    }

    poll()
    const timer = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      destroyed = true
      clearInterval(timer)
    }
  }, [])

  return { summary, agents, error, loading }
}
