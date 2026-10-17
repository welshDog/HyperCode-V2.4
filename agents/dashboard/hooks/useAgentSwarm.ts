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

// One shared poll for every widget. The Mission page mounts several consumers (swarm panel, BROski pulse, layout); each used to run its own
// 5s timer, so a slow core stacked up a dozen overlapping /api/agents requests that then 502'd together. Now there is a single timer and a
// single in-flight request, and every subscriber reads the same snapshot.
type Snapshot = { agents: Agent[]; loading: boolean; error: string | null }

let snapshot: Snapshot = { agents: [], loading: true, error: null }
const subscribers = new Set<() => void>()
let timer: ReturnType<typeof setInterval> | null = null
let inFlight: Promise<boolean> | null = null

function publish(next: Snapshot) {
  snapshot = next
  subscribers.forEach((fn) => fn())
}

function fetchShared(): Promise<boolean> {
  if (inFlight) return inFlight
  inFlight = (async () => {
    try {
      const res = await fetch('/api/agents', { next: { revalidate: 0 } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const rawAgents: unknown[] = Array.isArray(data?.agents) ? data.agents : []
      const mapped = rawAgents.map(normaliseAgent).filter((x): x is Agent => x != null)
      publish({ agents: mapped, loading: false, error: null })
      return true
    } catch (err) {
      // keep the last good roster on a transient failure; only the error flag changes
      publish({ ...snapshot, loading: false, error: err instanceof Error ? err.message : 'Unknown error' })
      return false
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

function subscribe(fn: () => void): () => void {
  subscribers.add(fn)
  if (subscribers.size === 1) {
    fetchShared()
    timer = setInterval(fetchShared, POLL_MS)
  }
  return () => {
    subscribers.delete(fn)
    if (subscribers.size === 0 && timer) {
      clearInterval(timer)
      timer = null
    }
  }
}

export function useAgentSwarm(onRefetchComplete?: (success: boolean) => void) {
  const [, force] = useState(0)

  useEffect(() => subscribe(() => force((n) => n + 1)), [])

  const refetch = useCallback(() => {
    fetchShared().then((ok) => onRefetchComplete?.(ok))
  }, [onRefetchComplete])

  return { agents: snapshot.agents, loading: snapshot.loading, error: snapshot.error, refetch }
}
