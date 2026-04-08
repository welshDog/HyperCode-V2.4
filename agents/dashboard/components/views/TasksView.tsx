'use client'

import React, { useState } from 'react'
import { useTasks } from '@/hooks/useTasks'

const STATUS_COLOUR: Record<string, string> = {
  completed:   'var(--status-healthy)',
  in_progress: 'var(--accent-cyan)',
  pending:     'var(--accent-amber)',
  error:       'var(--status-error)',
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
  const [creating, setCreating] = useState(false)
  const [newDesc, setNewDesc]   = useState('')
  const [createError, setCreateError] = useState<string | null>(null)

  const handleCreate = async () => {
    if (creating) return
    if (!newDesc.trim()) return
    setCreating(true)
    setCreateError(null)
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
        const text = await res.text()
        throw new Error(text || `Create task failed (HTTP ${res.status})`)
      }
      setNewDesc('')
      refetch()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Create task failed')
    } finally {
      setCreating(false)
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
      {/* Quick-create bar */}
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

      {/* Task list */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}
           data-testid="tasks-view">
        {tasks.length === 0 && (
          <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: 20, fontSize: 12 }}>
            No tasks yet — create one above
          </div>
        )}
        {tasks.map((task) => (
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
                {task.title || task.description?.slice(0, 60) || `Task #${task.id}`}
              </span>
              <span style={{
                fontSize: 9,
                fontWeight: 700,
                color: STATUS_COLOUR[task.status] ?? 'var(--text-secondary)',
                textTransform: 'uppercase',
                flexShrink: 0,
              }}>
                {task.status}
              </span>
            </div>
            <ProgressBar value={task.progress ?? 0} />
          </div>
        ))}
      </div>
    </div>
  )
}
