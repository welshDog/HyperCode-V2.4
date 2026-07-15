'use client'

import { useEffect, useRef, useState } from 'react'
import {
  fetchActiveFlows,
  fetchFlowRun,
  flowEventsUrl,
  type FlowRun,
} from '@/lib/api'

const POLL_MS = 3_000

/** Merge an SSE message (snapshot or single transition) into the current run. */
function mergeEvent(prev: FlowRun | null, runId: string, msg: Record<string, unknown>): FlowRun | null {
  // Snapshot frames carry the full history array.
  if (Array.isArray(msg.history)) {
    const base: FlowRun = prev ?? {
      run_id: runId,
      flow: String(msg.flow ?? ''),
      status: 'running',
      current_node: null,
      history: [],
    }
    return {
      ...base,
      flow: String(msg.flow ?? base.flow),
      status: String(msg.status ?? base.status),
      current_node: (msg.current_node as string | null) ?? base.current_node,
      history: msg.history as FlowRun['history'],
    }
  }
  // Transition frames: append to history; terminal frames set the final status.
  if (!prev) return prev
  const entry = {
    node: (msg.node as string | null) ?? null,
    type: String(msg.type ?? ''),
    status: String(msg.status ?? ''),
    result: (msg.result as Record<string, unknown>) ?? {},
    ts: String(msg.ts ?? new Date().toISOString()),
  }
  const isTerminal = entry.type === 'terminal'
  return {
    ...prev,
    status: isTerminal ? entry.status : prev.status,
    current_node: isTerminal ? null : (entry.node ?? prev.current_node),
    history: [...prev.history, entry],
  }
}

/**
 * Tracks the single most-recent active HyperFlow run (ADHD-friendly — one at a
 * time) and streams its node transitions live via SSE. When no run is active it
 * keeps showing the last run's terminal state.
 */
export function useMissionGraph() {
  const [run, setRun] = useState<FlowRun | null>(null)
  const [activeCount, setActiveCount] = useState(0)
  const [connected, setConnected] = useState(false)
  const runIdRef = useRef<string | null>(null)

  // Poll the active-runs list to discover which run to display.
  useEffect(() => {
    let cancelled = false
    async function poll() {
      const runs = await fetchActiveFlows()
      if (cancelled) return
      setActiveCount(runs.length)
      const top = runs[0]
      if (top) {
        if (top.run_id !== runIdRef.current) {
          runIdRef.current = top.run_id
          setRun(top)
        }
      } else if (runIdRef.current) {
        // No active runs — refresh the last one's terminal state once.
        const final = await fetchFlowRun(runIdRef.current)
        if (!cancelled && final) setRun(final)
      }
    }
    poll()
    const t = setInterval(poll, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [])

  // Stream live transitions for the displayed run.
  const runId = run?.run_id
  useEffect(() => {
    if (!runId) return
    const es = new EventSource(flowEventsUrl(runId))
    es.onopen = () => setConnected(true)
    es.onerror = () => setConnected(false)
    es.onmessage = (e: MessageEvent) => {
      try {
        const msg = JSON.parse(e.data) as Record<string, unknown>
        setRun((prev) => mergeEvent(prev, runId, msg))
      } catch {
        // malformed frame — skip
      }
    }
    return () => es.close()
  }, [runId])

  return { run, connected, activeCount }
}
