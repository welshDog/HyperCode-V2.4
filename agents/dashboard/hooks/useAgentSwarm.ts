'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Agent } from '@/types/agent'

const POLL_MS = 5_000

function normaliseStatus(raw: unknown): Agent['status'] {
  const s = typeof raw === 'string' ? raw.toLowerCase() : ''
  if (s === 'healthy' || s === 'online' || s === 'ok' || s === 'up') return 'healthy'
  if (s === 'warning' || s === 'warn' || s === 'degraded') return 'warning'
  if (s === 'error' || s === 'unhealthy' || s === 'down' || s === 'failed') return 'error'
  if (s === 'idle') return 'idle'
  return 'idle'
}

function asNumber(v: unknown, fallback: number): number {
  const n = typeof v === 'number' ? v : typeof v === 'string' ? Number(v) : NaN
  return Number.isFinite(n) ? n : fallback
}

function normaliseAgent(raw: unknown): Agent | null {
  if (!raw || typeof raw !== 'object') return null
  const a = raw as Record<string, unknown>
  const id = typeof a.id === 'string' && a.id ? a.id : typeof a.name === 'string' ? a.name : ''
  const name = typeof a.name === 'string' && a.name ? a.name : id
  if (!id || !name) return null

  const level = Math.max(1, Math.floor(asNumber(a.level, 1)))
  const xp = Math.max(0, Math.floor(asNumber(a.xp ?? a.total_xp, 0)))
  const xpToNextLevel = Math.max(1, Math.floor(asNumber(a.xpToNextLevel ?? a.xp_to_next ?? a.xp_to_next_level, 100)))
  const coinsRaw = a.coins ?? a.broski_coins ?? a.balance
  const coins = asNumber(coinsRaw, 0)
  const port = a.port != null ? Math.floor(asNumber(a.port, 0)) : undefined

  const lastAction = typeof a.lastAction === 'string'
    ? a.lastAction
    : typeof a.last_action === 'string'
      ? a.last_action
      : undefined

  return {
    id,
    name,
    status: normaliseStatus(a.status),
    xp,
    xpToNextLevel,
    level,
    coins: Number.isFinite(coins) ? coins : 0,
    lastAction,
    port: port && port > 0 ? port : undefined,
  }
}

export function useAgentSwarm() {
  const [agents, setAgents]   = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch('/api/agents', { next: { revalidate: 0 } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const rawAgents: unknown[] = Array.isArray(data?.agents) ? data.agents : []
      const mapped = rawAgents.map(normaliseAgent).filter((x): x is Agent => x != null)
      setAgents(mapped)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAgents()
    const timer = setInterval(fetchAgents, POLL_MS)
    return () => clearInterval(timer)
  }, [fetchAgents])

  return { agents, loading, error, refetch: fetchAgents }
}
