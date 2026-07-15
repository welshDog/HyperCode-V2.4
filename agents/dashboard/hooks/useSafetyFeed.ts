// Mission Control — live Safety Shepherd verdict feed (:8096/safety/events),
// via /api/safety. Polls every 5s; the Shepherd keeps the last 500 verdicts.

import { useEffect, useState } from 'react'

const POLL_INTERVAL_MS = 5_000

export interface SafetyEvent {
  id: string
  ts: string
  agent: string
  category: string
  tool?: string | null
  target?: string | null
  domain?: string | null
  decision: 'ALLOW' | 'BLOCK' | 'ESCALATE' | string
  reason?: string
  rule?: string
  approval_id?: string
}

interface UseSafetyFeedReturn {
  events: SafetyEvent[]
  error: string | null
  loading: boolean
}

export function useSafetyFeed(limit = 50): UseSafetyFeedReturn {
  const [events, setEvents] = useState<SafetyEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let destroyed = false

    const poll = async () => {
      try {
        const res = await fetch(`/api/safety?limit=${limit}`, { cache: 'no-store' })
        const data = await res.json()
        if (destroyed) return
        setEvents(Array.isArray(data?.events) ? data.events : [])
        setError(data?.error ?? null)
      } catch (e) {
        if (!destroyed) setError(e instanceof Error ? e.message : 'Safety feed fetch failed')
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
  }, [limit])

  return { events, error, loading }
}
