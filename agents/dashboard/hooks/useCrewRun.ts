'use client'

import { useEffect, useReducer, useState } from 'react'
import { initialRun, runReducer, type RunState } from '@/lib/agui/runStore'
import type { EventsPayload } from '@/lib/agui/types'

const DEFAULT_POLL_MS = 2000
const MAX_BACKOFF_MS = 15_000

export type Connection = 'idle' | 'live' | 'retrying'

// Polls GET /api/crew/{taskId}/events. Reconnect-safe by construction: every poll asks for
// events after the last sequence we applied, and the store ignores anything it already has,
// so a page refresh or dropped connection simply replays what was missed.
export function useCrewRun(taskId: string | null): { run: RunState; connection: Connection } {
  const [run, dispatch] = useReducer(runReducer, taskId, initialRun)
  const [connection, setConnection] = useState<Connection>('idle')

  useEffect(() => {
    dispatch({ type: 'reset', taskId })
    if (!taskId) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let after = -1
    let failures = 0

    const tick = async (): Promise<void> => {
      let delay: number
      let finished = false
      try {
        const res = await fetch(`/api/crew/${encodeURIComponent(taskId)}/events?after=${after}`, { cache: 'no-store' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const payload = (await res.json()) as EventsPayload
        if (cancelled) return
        after = Math.max(after, payload.nextAfter)
        failures = 0
        setConnection('live')
        dispatch({ type: 'payload', payload })
        finished = payload.done
        delay = payload.pollInterval ?? DEFAULT_POLL_MS
      } catch {
        if (cancelled) return
        failures += 1
        setConnection('retrying')
        delay = Math.min(MAX_BACKOFF_MS, DEFAULT_POLL_MS * 2 ** failures)
      }
      if (!cancelled && !finished) timer = setTimeout(() => void tick(), delay)
    }

    void tick()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [taskId])

  return { run, connection }
}
