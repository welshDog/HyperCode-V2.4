'use client'

import { useState, useEffect, useCallback } from 'react'

export interface TaskItem {
  id: number | string
  title: string
  description: string
  status: string
  progress: number
  started_at?: string
}

const POLL_MS = 10_000

export function useTasks() {
  const [tasks, setTasks]     = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
      const res = await fetch('/api/tasks', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        cache: 'no-store',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      if (data && typeof data === 'object' && 'error' in data && data.error) {
        throw new Error(String(data.error))
      }
      setTasks(Array.isArray(data) ? data : data.tasks ?? [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
    const t = setInterval(fetchTasks, POLL_MS)
    return () => clearInterval(t)
  }, [fetchTasks])

  return { tasks, loading, error, refetch: fetchTasks }
}
