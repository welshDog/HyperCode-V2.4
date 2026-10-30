'use client'

import { useState, useEffect, useCallback } from 'react'

export interface TaskItem {
  id: number | string
  title: string
  description?: string | null
  status: string
  priority?: string | null
  created_at?: string
  updated_at?: string | null
}
const POLL_MS = 10_000
const MAX_BACKOFF_MS = 30_000

export function useTasks() {
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const refetch = useCallback(() => setRefreshKey((n) => n + 1), [])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    let failures = 0
    const refresh = async () => {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
        const res = await fetch('/api/tasks', { headers: token ? { Authorization: `Bearer ${token}` } : {}, cache: 'no-store' })
        const data: unknown = await res.json().catch(() => null)
        if (!res.ok) {
          const message = data && typeof data === 'object' && 'error' in data ? String(data.error) : `HTTP ${res.status}`
          throw new Error(message)
        }
        if (data && typeof data === 'object' && 'error' in data && data.error) throw new Error(String(data.error))
        const items = Array.isArray(data) ? data : data && typeof data === 'object' && 'tasks' in data && Array.isArray(data.tasks) ? data.tasks : []
        if (cancelled) return
        setTasks(items as TaskItem[])
        setError(null)
        failures = 0
        setRetryCount(0)
        timer = setTimeout(refresh, POLL_MS)
      } catch (err) {
        if (cancelled) return
        failures += 1
        setRetryCount(failures)
        setError(err instanceof Error ? err.message : 'Failed to load tasks')
        timer = setTimeout(refresh, Math.min(POLL_MS * 2 ** Math.min(failures, 4), MAX_BACKOFF_MS))
      } finally { if (!cancelled) setLoading(false) }
    }
    setLoading(true)
    void refresh()
    return () => { cancelled = true; clearTimeout(timer) }
  }, [refreshKey])

  return { tasks, loading, error, retryCount, refetch }
}
