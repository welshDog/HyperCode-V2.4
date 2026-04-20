"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

type MetricsSnapshot = {
  requestsPerMin: number
  avgResponseMs: number
  healsToday: number
  errorRatePct: number
  activeAgents: number
  redisQueueDepth: number
  celeryQueueDepths?: Record<string, number>
  dlqDepth?: number
  alertFiring?: number
  alertPending?: number
  collectedAt: string
}

function statusFromMetrics(s: MetricsSnapshot): "stable" | "watch" | "on_fire" {
  const firing = Number(s.alertFiring ?? 0)
  const dlq = Number(s.dlqDepth ?? 0)
  const err = Number(s.errorRatePct ?? 0)
  const q = s.celeryQueueDepths ?? {}
  const high = Number(q["hypercode-high"] ?? 0)

  if (firing > 0) return "on_fire"
  if (err > 5) return "on_fire"
  if (dlq > 0) return "watch"
  if (high > 0) return "watch"
  if (err > 1) return "watch"
  return "stable"
}

function colourForStatus(status: "stable" | "watch" | "on_fire"): string {
  if (status === "stable") return "var(--status-healthy)"
  if (status === "watch") return "var(--status-warning)"
  return "var(--status-error)"
}

function formatNumber(n: number): string {
  if (!Number.isFinite(n)) return "—"
  return n.toLocaleString()
}

export function MetricsPanel(): React.JSX.Element {
  const [snapshot, setSnapshot] = useState<MetricsSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/metrics", { cache: "no-store" })
      if (!res.ok) throw new Error(`Metrics API ${res.status}`)
      const data = (await res.json()) as MetricsSnapshot
      setSnapshot(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load metrics")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const t = window.setInterval(refresh, 5000)
    return () => window.clearInterval(t)
  }, [refresh])

  const derived = useMemo(() => {
    const s = snapshot
    if (!s) return null
    const status = statusFromMetrics(s)
    const q = s.celeryQueueDepths ?? {}
    const queues = [
      { key: "hypercode-high", label: "High", depth: Number(q["hypercode-high"] ?? 0) },
      { key: "hypercode-normal", label: "Normal", depth: Number(q["hypercode-normal"] ?? 0) },
      { key: "hypercode-low", label: "Low", depth: Number(q["hypercode-low"] ?? 0) },
      { key: "main-queue", label: "Legacy", depth: Number(q["main-queue"] ?? 0) },
    ]
    const dlq = Number(s.dlqDepth ?? 0)
    const firing = Number(s.alertFiring ?? 0)
    const pending = Number(s.alertPending ?? 0)
    const backlog = queues.reduce((acc, x) => acc + (Number.isFinite(x.depth) ? x.depth : 0), 0)
    return { status, queues, dlq, firing, pending, backlog }
  }, [snapshot])

  if (loading && !snapshot) {
    return (
      <div className="hc-metrics" data-testid="metrics-panel" aria-busy="true">
        <div className="hc-metrics-grid">
          {Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx} className="hc-metrics-card hc-skeleton" aria-hidden="true" />
          ))}
        </div>
      </div>
    )
  }

  if (!snapshot || derived === null) {
    return (
      <div className="hc-metrics" data-testid="metrics-panel" role="alert">
        <div className="hc-metrics-empty">
          <div className="hc-metrics-empty-title">Metrics unavailable</div>
          <div className="hc-metrics-empty-subtitle hc-mono">{error ?? "No data"}</div>
        </div>
      </div>
    )
  }

  const statusColour = colourForStatus(derived.status)

  return (
    <div className="hc-metrics" data-testid="metrics-panel">
      <div className="hc-metrics-head">
        <div className="hc-metrics-title">
          <span className="hc-metrics-state" style={{ color: statusColour }}>
            <span className="hc-conn-dot" aria-hidden="true" style={{ background: statusColour }} />
            {derived.status === "stable" ? "Stable" : derived.status === "watch" ? "Watch" : "On Fire"}
          </span>
          <span className="hc-metrics-sub hc-mono" title={snapshot.collectedAt}>
            {new Date(snapshot.collectedAt).toLocaleTimeString()}
          </span>
        </div>
        <button type="button" className="btn" onClick={refresh}>
          ↻ Refresh
        </button>
      </div>

      <div className="hc-metrics-grid">
        <div className="hc-metrics-card">
          <div className="hc-metrics-card-head">
            <div className="hc-metrics-card-title">Ops Pulse</div>
            <div className="hc-metrics-chips" role="list" aria-label="Alert counters">
              <span className={`hc-metrics-chip${derived.firing > 0 ? " bad" : ""}`} role="listitem">
                FIRING <span className="hc-mono">{formatNumber(derived.firing)}</span>
              </span>
              <span className={`hc-metrics-chip${derived.pending > 0 ? " warn" : ""}`} role="listitem">
                PENDING <span className="hc-mono">{formatNumber(derived.pending)}</span>
              </span>
              <span className={`hc-metrics-chip${derived.dlq > 0 ? " bad" : ""}`} role="listitem">
                DLQ <span className="hc-mono">{formatNumber(derived.dlq)}</span>
              </span>
            </div>
          </div>

          <div className="hc-metrics-rows" role="list" aria-label="Core vitals">
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">Error Rate</span>
              <span className="hc-metrics-v hc-mono" style={{ color: snapshot.errorRatePct > 5 ? "var(--status-error)" : snapshot.errorRatePct > 1 ? "var(--status-warning)" : "var(--text-primary)" }}>
                {formatNumber(snapshot.errorRatePct)}%
              </span>
            </div>
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">Avg Latency</span>
              <span className="hc-metrics-v hc-mono">{formatNumber(snapshot.avgResponseMs)}ms</span>
            </div>
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">Requests / Min</span>
              <span className="hc-metrics-v hc-mono">{formatNumber(snapshot.requestsPerMin)}</span>
            </div>
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">Active Agents</span>
              <span className="hc-metrics-v hc-mono">{formatNumber(snapshot.activeAgents)}</span>
            </div>
          </div>
        </div>

        <div className="hc-metrics-card">
          <div className="hc-metrics-card-head">
            <div className="hc-metrics-card-title">Queues</div>
            <span className="hc-metrics-chip">
              BACKLOG <span className="hc-mono">{formatNumber(derived.backlog)}</span>
            </span>
          </div>

          <div className="hc-metrics-queue-list" role="list" aria-label="Celery queues">
            {derived.queues.map((q) => (
              <div key={q.key} className="hc-metrics-queue" role="listitem">
                <span className="hc-metrics-queue-name">{q.label}</span>
                <span className={`hc-metrics-queue-depth hc-mono${q.depth > 0 ? " hot" : ""}`}>{formatNumber(q.depth)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="hc-metrics-card">
          <div className="hc-metrics-card-head">
            <div className="hc-metrics-card-title">Redis Backlog</div>
            <span className="hc-metrics-chip">
              TASK_QUEUE <span className="hc-mono">{formatNumber(snapshot.redisQueueDepth)}</span>
            </span>
          </div>

          <div className="hc-metrics-rows" role="list" aria-label="Side counters">
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">Heals Today</span>
              <span className="hc-metrics-v hc-mono">{formatNumber(snapshot.healsToday)}</span>
            </div>
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">DLQ Depth</span>
              <span className="hc-metrics-v hc-mono" style={{ color: derived.dlq > 0 ? "var(--status-error)" : "var(--text-primary)" }}>
                {formatNumber(derived.dlq)}
              </span>
            </div>
            <div className="hc-metrics-row" role="listitem">
              <span className="hc-metrics-k">Firing Alerts</span>
              <span className="hc-metrics-v hc-mono" style={{ color: derived.firing > 0 ? "var(--status-error)" : "var(--text-primary)" }}>
                {formatNumber(derived.firing)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="hc-metrics-foot hc-mono">{error}</div>}
    </div>
  )
}
