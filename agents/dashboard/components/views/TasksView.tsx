'use client'

import React, { useState } from 'react'
import { useTasks } from '@/hooks/useTasks'
import { useToast } from '@/components/ui/ToastProvider'

const STATUS_COLOUR: Record<string, string> = {
  todo:        'var(--accent-amber)',
  done:        'var(--status-healthy)',
  cancelled:   'var(--text-secondary)',
  completed:   'var(--status-healthy)',
  in_progress: 'var(--accent-cyan)',
  pending:     'var(--accent-amber)',
  error:       'var(--status-error)',
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

function ProgressBar({ value }: { value: number }) {
  return (
    <div style={{ height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2, marginTop: 4 }}>
      <div style={{
        width: `${Math.min(100, Math.max(0, value))}%`,
        height: '100%',
        background: value >= 100 ? 'var(--status-healthy)' : 'var(--accent-cyan)',
        borderRadius: 2,
        transition: 'width 0.4s ease',
      }} />
    </div>
  )
}

export function TasksView(): React.JSX.Element {
  const { tasks, loading, error, refetch } = useTasks()
  const { toast } = useToast()
  const [creating, setCreating] = useState(false)
  const [newDesc, setNewDesc]   = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [busyIds, setBusyIds] = useState<Set<string | number>>(new Set())

  const setBusy = (id: string | number, value: boolean) => {
    setBusyIds((prev) => {
      const next = new Set(prev)
      if (value) next.add(id)
      else next.delete(id)
      return next
    })
  }

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

  if (loading) return (
    <div style={{ color: 'var(--text-secondary)', padding: 16 }}>⏳ Loading tasks...</div>
  )
  if (error) return (
    <div style={{ color: 'var(--status-error)', padding: 16 }}>⚠️ {error}</div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            value={newDesc}
            onChange={(e) => { setNewDesc(e.target.value); setCreateError(null) }}
            onKeyDown={(e) => {
              if (e.key !== 'Enter') return
              e.preventDefault()
              handleCreate()
            }}
            placeholder="New task… (Enter to submit)"
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.05)',
              border: `1px solid ${createError ? 'var(--status-error)' : 'var(--pane-border)'}`,
              borderRadius: 4,
              color: 'var(--text-primary)',
              padding: '4px 8px',
              fontSize: 11,
              outline: 'none',
            }}
          />
          <button
            onClick={handleCreate}
            disabled={creating || !newDesc.trim()}
            style={{
              background: 'var(--accent-cyan)',
              color: '#000',
              border: 'none',
              borderRadius: 4,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 700,
              cursor: creating ? 'wait' : 'pointer',
              opacity: creating || !newDesc.trim() ? 0.5 : 1,
            }}
          >
            {creating ? '…' : '+'}
          </button>
        </div>
        {createError && (
          <div style={{ fontSize: 10, color: 'var(--status-error)', paddingLeft: 2 }}>
            ⚠️ {createError}
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}
           data-testid="tasks-view">
        {tasks.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 20, fontSize: 12 }}>
            No tasks yet — create one above
          </div>
        )}
        {tasks.map((task) => {
          const label = task.title || task.description?.slice(0, 60) || `Task #${task.id}`
          const payload = task.description || task.title || `Task #${task.id}`
          const isBusy = busyIds.has(task.id)
          const canComplete = task.status !== 'done' && task.status !== 'completed' && task.status !== 'cancelled'
          const canDispatch = task.status !== 'done' && task.status !== 'completed' && task.status !== 'cancelled'
          return (
            <div
              key={task.id}
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--pane-border)',
                borderRadius: 5,
                padding: '6px 8px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: 11, fontWeight: 600, flex: 1, marginRight: 8, wordBreak: 'break-word' }}>
                  {label}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                  <button
                    type="button"
                    onClick={() => handleDispatch(task.id, label, payload, task.status)}
                    disabled={!canDispatch || isBusy}
                    aria-label={`Dispatch ${label}`}
                    title="Dispatch"
                    style={{
                      background: 'transparent',
                      color: 'var(--accent-cyan)',
                      border: `1px solid ${canDispatch && !isBusy ? 'rgba(0,255,255,0.35)' : 'rgba(255,255,255,0.12)'}`,
                      borderRadius: 4,
                      padding: '2px 6px',
                      fontSize: 10,
                      fontWeight: 700,
                      cursor: !canDispatch || isBusy ? 'not-allowed' : 'pointer',
                      opacity: !canDispatch || isBusy ? 0.5 : 1,
                    }}
                  >
                    Dispatch
                  </button>
                  <button
                    type="button"
                    onClick={() => handleComplete(task.id, label, task.status)}
                    disabled={!canComplete || isBusy}
                    aria-label={`Complete ${label}`}
                    title="Complete"
                    style={{
                      background: 'transparent',
                      color: 'var(--status-healthy)',
                      border: `1px solid ${canComplete && !isBusy ? 'rgba(0,255,120,0.35)' : 'rgba(255,255,255,0.12)'}`,
                      borderRadius: 4,
                      padding: '2px 6px',
                      fontSize: 10,
                      fontWeight: 700,
                      cursor: !canComplete || isBusy ? 'not-allowed' : 'pointer',
                      opacity: !canComplete || isBusy ? 0.5 : 1,
                    }}
                  >
                    Done
                  </button>
                  <span style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: STATUS_COLOUR[task.status] ?? 'var(--text-secondary)',
                    textTransform: 'uppercase',
                  }}>
                    {task.status}
                  </span>
                </div>
              </div>
              <ProgressBar value={task.progress ?? 0} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
