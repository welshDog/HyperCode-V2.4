'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTasks } from '@/hooks/useTasks'
import { useToast } from '@/components/ui/ToastProvider'

type LaneId = 'queued' | 'running' | 'retrying' | 'failed' | 'complete' | 'dead'
type TaskFilter = 'all' | 'problems' | 'active' | 'complete'

type DlqEnvelope = {
  index?: number
  task_name?: string
  task_id?: string
  error?: string
  failed_at_unix?: number
  args?: unknown
  kwargs?: unknown
  extra?: Record<string, unknown>
}

function toErrorMessage(err: unknown, fallback: string) {
  if (err instanceof Error) return err.message || fallback
  if (typeof err === 'string') return err || fallback
  return fallback
}

function pickApiErrorMessage(data: unknown, fallback: string) {
  if (!data || typeof data !== 'object') return fallback
  const r = data as Record<string, unknown>
  const detail = r.detail
  if (typeof detail === 'string' && detail) return detail
  const error = r.error
  if (typeof error === 'string' && error) return error
  return fallback
}

function laneForStatus(statusRaw: string): Exclude<LaneId, 'dead'> {
  const s = String(statusRaw ?? '').toLowerCase().trim()
  if (s === 'done' || s === 'completed' || s === 'success') return 'complete'
  if (s === 'in_progress' || s === 'running' || s === 'started') return 'running'
  if (s === 'retrying' || s === 'retry') return 'retrying'
  if (s === 'error' || s === 'failed' || s === 'failure' || s === 'cancelled') return 'failed'
  return 'queued'
}

function normalisePriority(priorityRaw: string | null | undefined): 'high' | 'normal' | 'low' | 'unknown' {
  const p = String(priorityRaw ?? '').toLowerCase().trim()
  if (p === 'high' || p === 'critical' || p === 'urgent') return 'high'
  if (p === 'low') return 'low'
  if (p === 'normal' || p === 'medium' || p === 'default' || p) return 'normal'
  return 'unknown'
}

function queueForPriority(p: ReturnType<typeof normalisePriority>): string {
  if (p === 'high') return 'hypercode-high'
  if (p === 'low') return 'hypercode-low'
  if (p === 'normal') return 'hypercode-normal'
  return 'hypercode-normal'
}

function progressForLane(lane: Exclude<LaneId, 'dead'>): number {
  if (lane === 'complete') return 100
  if (lane === 'failed') return 100
  if (lane === 'running') return 60
  if (lane === 'retrying') return 40
  return 10
}

function formatDlqAge(failedAtUnix: number | undefined): string {
  if (!failedAtUnix || !Number.isFinite(failedAtUnix)) return '—'
  const delta = Math.max(0, Math.floor(Date.now() / 1000) - failedAtUnix)
  if (delta < 60) return `${delta}s`
  const m = Math.floor(delta / 60)
  if (m < 60) return `${m}m`
  const h = Math.floor(m / 60)
  if (h < 48) return `${h}h`
  const d = Math.floor(h / 24)
  return `${d}d`
}

export function TasksView(): React.JSX.Element {
  const { tasks, loading, error, refetch } = useTasks()
  const { toast } = useToast()
  const [creating, setCreating] = useState(false)
  const [newDesc, setNewDesc]   = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [busyIds, setBusyIds] = useState<Set<string | number>>(new Set())
  const scrollerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [pinned, setPinned] = useState(true)
  const [filter, setFilter] = useState<TaskFilter>('all')
  const [laneFocus, setLaneFocus] = useState<LaneId | 'all'>('all')
  const [dlqItems, setDlqItems] = useState<DlqEnvelope[]>([])
  const [dlqStats, setDlqStats] = useState<Record<string, unknown> | null>(null)
  const [dlqLoading, setDlqLoading] = useState(true)
  const [dlqError, setDlqError] = useState<string | null>(null)
  const [dlqBusy, setDlqBusy] = useState<Set<string>>(new Set())

  const setBusy = (id: string | number, value: boolean) => {
    setBusyIds((prev) => {
      const next = new Set(prev)
      if (value) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const setDlqBusyKey = (key: string, value: boolean) => {
    setDlqBusy((prev) => {
      const next = new Set(prev)
      if (value) next.add(key)
      else next.delete(key)
      return next
    })
  }

  const fetchDlq = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

      const [statsRes, listRes] = await Promise.all([
        fetch('/api/ops/dlq/stats', { headers, cache: 'no-store' }),
        fetch('/api/ops/dlq?limit=30&offset=0', { headers, cache: 'no-store' }),
      ])

      const statsData: unknown = await statsRes.json().catch(() => null)
      const listData: unknown = await listRes.json().catch(() => null)

      if (!statsRes.ok) throw new Error(pickApiErrorMessage(statsData, `DLQ stats failed (HTTP ${statsRes.status})`))
      if (!listRes.ok) throw new Error(pickApiErrorMessage(listData, `DLQ list failed (HTTP ${listRes.status})`))

      const items = (listData && typeof listData === 'object' && 'items' in listData)
        ? (listData as { items?: unknown }).items
        : null

      setDlqStats(statsData && typeof statsData === 'object' ? (statsData as Record<string, unknown>) : null)
      setDlqItems(Array.isArray(items) ? (items as DlqEnvelope[]) : [])
      setDlqError(null)
    } catch (e) {
      setDlqError(toErrorMessage(e, 'Failed to load DLQ'))
    } finally {
      setDlqLoading(false)
    }
  }

  useEffect(() => {
    fetchDlq()
    const t = window.setInterval(fetchDlq, 10_000)
    return () => window.clearInterval(t)
  }, [])

  useEffect(() => {
    if (!pinned) return
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ block: 'end' })
    }
  }, [pinned, tasks, dlqItems])

  const grouped = useMemo(() => {
    const out: Record<Exclude<LaneId, 'dead'>, typeof tasks> = {
      queued: [],
      running: [],
      retrying: [],
      failed: [],
      complete: [],
    }

    for (const t of tasks) {
      const lane = laneForStatus(t.status)
      out[lane].push(t)
    }
    return out
  }, [tasks])

  const taskCounts = useMemo(() => {
    const counts = {
      total: tasks.length,
      queued: grouped.queued.length,
      running: grouped.running.length,
      retrying: grouped.retrying.length,
      failed: grouped.failed.length,
      complete: grouped.complete.length,
      dead: dlqItems.length,
    }
    return counts
  }, [dlqItems.length, grouped, tasks.length])

  const visibleLanes = useMemo(() => {
    const lanes: LaneId[] = ['queued', 'running', 'retrying', 'failed', 'complete', 'dead']
    if (laneFocus !== 'all') return lanes.filter((l) => l === laneFocus)
    if (filter === 'active') return lanes.filter((l) => l === 'queued' || l === 'running' || l === 'retrying')
    if (filter === 'complete') return lanes.filter((l) => l === 'complete')
    if (filter === 'problems') return lanes.filter((l) => l === 'failed' || l === 'dead')
    return lanes
  }, [filter, laneFocus])

  const handleCreate = async () => {
    if (creating) return
    if (!newDesc.trim()) return
    setCreating(true)
    setCreateError(null)
    toast({
      variant: 'info',
      title: 'Creating task',
      message: newDesc.trim().length > 120 ? `${newDesc.trim().slice(0, 120)}…` : newDesc.trim(),
    })
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const storedProjectId =
        typeof window !== 'undefined'
          ? Number(localStorage.getItem('project_id') ?? localStorage.getItem('projectId') ?? '')
          : NaN
      const projectId = Number.isFinite(storedProjectId) && storedProjectId > 0 ? storedProjectId : 1
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          title: newDesc.trim().slice(0, 60),
          description: newDesc.trim(),
          priority: 'normal',
          type: 'user_command',
          project_id: projectId,
        }),
      })
      if (!res.ok) {
        const data: unknown = await res.json().catch(() => ({}))
        throw new Error(pickApiErrorMessage(data, `Create task failed (HTTP ${res.status})`))
      }
      setNewDesc('')
      toast({ variant: 'success', title: 'Task created', action: { label: 'View', href: '/' } })
      refetch()
    } catch (err) {
      const msg = toErrorMessage(err, 'Create task failed')
      setCreateError(msg)
      toast({ variant: 'error', title: 'Create failed', message: msg })
    } finally {
      setCreating(false)
    }
  }

  const handleComplete = async (taskId: string | number, label: string, status: string) => {
    if (busyIds.has(taskId)) return
    if (status === 'done' || status === 'completed') return
    setBusy(taskId, true)
    toast({ variant: 'info', title: 'Completing task', message: label })
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch(`/api/tasks/${encodeURIComponent(String(taskId))}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ status: 'done' }),
      })
      const data: unknown = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(pickApiErrorMessage(data, `Complete failed (HTTP ${res.status})`))
      toast({ variant: 'success', title: 'Task completed', message: label, action: { label: 'View', href: '/' } })
      refetch()
    } catch (err) {
      const msg = toErrorMessage(err, 'Complete failed')
      toast({ variant: 'error', title: 'Complete failed', message: msg })
    } finally {
      setBusy(taskId, false)
    }
  }

  const handleDispatch = async (taskId: string | number, label: string, payload: string, status: string) => {
    if (busyIds.has(taskId)) return
    if (status === 'done' || status === 'completed' || status === 'cancelled') return
    setBusy(taskId, true)
    toast({ variant: 'info', title: 'Dispatching task', message: label })
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch('/api/orchestrator', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          description: payload,
          type: 'terminal',
          agent: 'coder-agent',
          requires_approval: false,
        }),
      })
      const data: unknown = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(pickApiErrorMessage(data, `Dispatch failed (HTTP ${res.status})`))
      toast({ variant: 'success', title: 'Task dispatched', message: label, action: { label: 'View', href: '/' } })

      const updateRes = await fetch(`/api/tasks/${encodeURIComponent(String(taskId))}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ status: 'in_progress' }),
      })
      if (!updateRes.ok) {
        const updateData: unknown = await updateRes.json().catch(() => ({}))
        toast({
          variant: 'error',
          title: 'Status update failed',
          message: pickApiErrorMessage(updateData, `HTTP ${updateRes.status}`),
        })
      }

      refetch()
    } catch (err) {
      const msg = toErrorMessage(err, 'Dispatch failed')
      toast({ variant: 'error', title: 'Dispatch failed', message: msg })
    } finally {
      setBusy(taskId, false)
    }
  }

  const handleDlqReplay = async (env: DlqEnvelope) => {
    const key = env.task_id ? `id:${env.task_id}` : typeof env.index === 'number' ? `idx:${env.index}` : `row:${Math.random()}`
    if (dlqBusy.has(key)) return
    setDlqBusyKey(key, true)
    toast({ variant: 'info', title: 'Replaying from DLQ', message: env.task_id ?? env.task_name ?? 'task' })
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch('/api/ops/dlq/replay', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          task_id: env.task_id ?? null,
          index: typeof env.index === 'number' ? env.index : null,
          queue: typeof env.extra?.queue === 'string' ? env.extra.queue : null,
        }),
      })
      const data: unknown = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(pickApiErrorMessage(data, `Replay failed (HTTP ${res.status})`))
      const replayedValue =
        data && typeof data === 'object' && 'replayed' in data
          ? (data as Record<string, unknown>).replayed
          : null
      const replayed = replayedValue === true
      if (!replayed) throw new Error(pickApiErrorMessage(data, 'Replay failed'))
      toast({ variant: 'success', title: 'Replayed', message: env.task_id ?? env.task_name ?? 'task' })
      fetchDlq()
    } catch (e) {
      toast({ variant: 'error', title: 'Replay failed', message: toErrorMessage(e, 'Replay failed') })
    } finally {
      setDlqBusyKey(key, false)
    }
  }

  return (
    <div className="hc-tasks" data-testid="tasks-view">
      <div className="hc-tasks-head">
        <div className="hc-tasks-kpis" role="list" aria-label="Task counts">
          <span className="hc-tasks-kpi" role="listitem"><span className="hc-tasks-kpi-value hc-mono">{taskCounts.total}</span><span className="hc-tasks-kpi-label">total</span></span>
          <span className="hc-tasks-kpi" role="listitem"><span className="hc-tasks-kpi-value hc-mono">{taskCounts.queued}</span><span className="hc-tasks-kpi-label">queued</span></span>
          <span className="hc-tasks-kpi" role="listitem"><span className="hc-tasks-kpi-value hc-mono">{taskCounts.running}</span><span className="hc-tasks-kpi-label">running</span></span>
          <span className="hc-tasks-kpi" role="listitem"><span className="hc-tasks-kpi-value hc-mono">{taskCounts.failed}</span><span className="hc-tasks-kpi-label">failed</span></span>
          <span className="hc-tasks-kpi" role="listitem"><span className="hc-tasks-kpi-value hc-mono">{taskCounts.complete}</span><span className="hc-tasks-kpi-label">complete</span></span>
          <span className="hc-tasks-kpi" role="listitem"><span className="hc-tasks-kpi-value hc-mono">{taskCounts.dead}</span><span className="hc-tasks-kpi-label">dead</span></span>
        </div>

        <div className="hc-tasks-controls" role="group" aria-label="Task filters">
          <button type="button" className={`btn${filter === 'all' ? ' active' : ''}`} aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>All</button>
          <button type="button" className={`btn${filter === 'active' ? ' active' : ''}`} aria-pressed={filter === 'active'} onClick={() => setFilter('active')}>Active</button>
          <button type="button" className={`btn${filter === 'problems' ? ' active' : ''}`} aria-pressed={filter === 'problems'} onClick={() => setFilter('problems')}>Problems</button>
          <button type="button" className={`btn${filter === 'complete' ? ' active' : ''}`} aria-pressed={filter === 'complete'} onClick={() => setFilter('complete')}>Complete</button>

          <label className="hc-tasks-select">
            <span className="hc-tasks-select-label">Lane</span>
            <select
              className="hc-tasks-select-input"
              value={laneFocus}
              onChange={(e) => {
                const v = e.target.value
                const allowed = ['all', 'queued', 'running', 'retrying', 'failed', 'complete', 'dead'] as const
                if ((allowed as readonly string[]).includes(v)) setLaneFocus(v as LaneId | 'all')
              }}
              aria-label="Filter by lane"
            >
              <option value="all">All</option>
              <option value="queued">Queued</option>
              <option value="running">Running</option>
              <option value="retrying">Retrying</option>
              <option value="failed">Failed</option>
              <option value="complete">Complete</option>
              <option value="dead">Dead</option>
            </select>
          </label>

          <button type="button" className="btn" onClick={() => { refetch(); fetchDlq(); toast({ variant: 'info', title: 'Refreshing tasks' }) }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      <div className="hc-tasks-create">
        <input
          className={`hc-tasks-input${createError ? ' error' : ''}`}
          value={newDesc}
          onChange={(e) => { setNewDesc(e.target.value); setCreateError(null) }}
          onKeyDown={(e) => {
            if (e.key !== 'Enter') return
            e.preventDefault()
            handleCreate()
          }}
          placeholder="New task… (Enter to submit)"
          aria-label="New task"
        />
        <button type="button" className="hc-tasks-create-btn" onClick={handleCreate} disabled={creating || !newDesc.trim()}>
          {creating ? '…' : '+'}
        </button>
        {createError && <div className="hc-tasks-create-error">⚠️ {createError}</div>}
      </div>

      <div
        ref={scrollerRef}
        className="hc-tasks-body"
        onScroll={() => {
          const el = scrollerRef.current
          if (!el) return
          const distanceFromBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
          setPinned(distanceFromBottom < 24)
        }}
      >
        {(loading || dlqLoading) && (
          <div className="hc-tasks-skeleton">
            {Array.from({ length: 8 }).map((_, idx) => (
              <div key={idx} className="hc-tasks-card hc-skeleton" aria-hidden="true" />
            ))}
          </div>
        )}

        {(error || dlqError) && (
          <div className="hc-tasks-empty hc-tasks-error" role="alert">
            <div className="hc-tasks-empty-title">Tasks unavailable</div>
            <div className="hc-tasks-empty-subtitle hc-mono">
              {error ?? dlqError}
            </div>
          </div>
        )}

        {!loading && !dlqLoading && !error && !dlqError && visibleLanes.every((l) => (l === 'dead' ? dlqItems.length === 0 : grouped[l].length === 0)) && (
          <div className="hc-tasks-empty">
            <div className="hc-tasks-empty-title">No tasks yet — waiting for activity…</div>
            <div className="hc-tasks-empty-subtitle">
              Create a task above or watch queues + DLQ as work flows through.
            </div>
          </div>
        )}

        {!loading && !dlqLoading && !error && !dlqError && (
          <div className="hc-tasks-lanes">
            {visibleLanes.map((lane) => {
              if (lane === 'dead') {
                const dlqSize = typeof dlqStats?.size === 'number' ? dlqStats.size : dlqItems.length
                return (
                  <section key="dead" className="hc-tasks-lane">
                    <div className="hc-tasks-lane-head">
                      <div className="hc-tasks-lane-title">
                        <span className="hc-tasks-lane-name">Dead</span>
                        <span className="hc-tasks-chip dead">DLQ</span>
                        <span className="hc-tasks-lane-count hc-mono">{dlqSize}</span>
                      </div>
                      <div className="hc-tasks-lane-meta hc-mono">
                        {(dlqStats?.available === false) ? 'redis down' : 'hypercode-dlq'}
                      </div>
                    </div>

                    {dlqItems.length === 0 ? (
                      <div className="hc-tasks-lane-empty">No dead letters</div>
                    ) : (
                      <div className="hc-tasks-lane-list">
                        {dlqItems.map((env, idx) => {
                          const key = env.task_id ? `id:${env.task_id}` : typeof env.index === 'number' ? `idx:${env.index}` : `row:${idx}`
                          const isBusy = dlqBusy.has(key)
                          const q = typeof env.extra?.queue === 'string' ? env.extra.queue : null
                          const prio = q && q.includes('high') ? 'high' : q && q.includes('low') ? 'low' : q ? 'normal' : 'unknown'
                          const label = env.task_name ?? 'task'
                          const errMsg = (env.error ?? '').slice(0, 180)
                          return (
                            <div key={key} className="hc-tasks-card dead">
                              <div className="hc-tasks-card-top">
                                <div className="hc-tasks-card-title" title={label}>{label}</div>
                                <div className="hc-tasks-card-actions">
                                  <span className={`hc-tasks-chip ${prio}`}>{prio.toUpperCase()}</span>
                                  <span className="hc-tasks-chip dead">DEAD</span>
                                  <button type="button" className="btn" disabled={isBusy} onClick={() => handleDlqReplay(env)}>
                                    {isBusy ? '…' : 'Retry'}
                                  </button>
                                </div>
                              </div>
                              <div className="hc-tasks-card-meta">
                                <span className="hc-mono">{env.task_id ? `id:${env.task_id}` : typeof env.index === 'number' ? `idx:${env.index}` : ''}</span>
                                <span className="hc-mono">{formatDlqAge(env.failed_at_unix)}</span>
                                {q && <span className="hc-mono">{q}</span>}
                              </div>
                              {errMsg && <div className="hc-tasks-card-desc" title={env.error}>{errMsg}</div>}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </section>
                )
              }

              const laneTasks = grouped[lane]
              const laneName = lane.charAt(0).toUpperCase() + lane.slice(1)
              return (
                <section key={lane} className="hc-tasks-lane">
                  <div className="hc-tasks-lane-head">
                    <div className="hc-tasks-lane-title">
                      <span className="hc-tasks-lane-name">{laneName}</span>
                      <span className={`hc-tasks-chip ${lane}`}>{lane.toUpperCase()}</span>
                      <span className="hc-tasks-lane-count hc-mono">{laneTasks.length}</span>
                    </div>
                    <div className="hc-tasks-lane-meta hc-mono">{lane === 'queued' ? 'celery pending' : lane === 'running' ? 'in flight' : lane}</div>
                  </div>

                  {laneTasks.length === 0 ? (
                    <div className="hc-tasks-lane-empty">No {lane}</div>
                  ) : (
                    <div className="hc-tasks-lane-list">
                      {laneTasks.map((task) => {
                        const label = task.title || task.description?.slice(0, 60) || `Task #${task.id}`
                        const payload = task.description || task.title || `Task #${task.id}`
                        const isBusy = busyIds.has(task.id)
                        const canComplete = task.status !== 'done' && task.status !== 'completed' && task.status !== 'cancelled'
                        const canDispatch = task.status !== 'done' && task.status !== 'completed' && task.status !== 'cancelled'
                        const prio = normalisePriority(task.priority ?? null)
                        const queue = queueForPriority(prio)
                        const prog = progressForLane(lane)

                        return (
                          <div key={task.id} className={`hc-tasks-card ${lane}`}>
                            <div className="hc-tasks-card-top">
                              <div className="hc-tasks-card-title" title={label}>{label}</div>
                              <div className="hc-tasks-card-actions">
                                <span className={`hc-tasks-chip ${prio}`}>{prio.toUpperCase()}</span>
                                <span className="hc-tasks-chip queue">{queue}</span>
                                <button type="button" className="btn" onClick={() => handleDispatch(task.id, label, payload, task.status)} disabled={!canDispatch || isBusy}>
                                  Dispatch
                                </button>
                                <button type="button" className="btn" onClick={() => handleComplete(task.id, label, task.status)} disabled={!canComplete || isBusy}>
                                  Done
                                </button>
                              </div>
                            </div>
                            <div className="hc-tasks-progress">
                              <div className="hc-tasks-progress-fill" style={{ width: `${prog}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </section>
              )
            })}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {!pinned && (
        <button
          type="button"
          className="hc-tasks-latest"
          onClick={() => {
            setPinned(true)
            if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
              bottomRef.current.scrollIntoView({ block: 'end' })
            }
          }}
          aria-label="Scroll to latest tasks"
        >
          ↓ Latest
        </button>
      )}
    </div>
  )
}
