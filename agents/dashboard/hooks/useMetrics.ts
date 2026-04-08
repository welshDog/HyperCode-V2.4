'use client'

import { useState, useEffect, useCallback } from 'react'
import type { MetricsSnapshot } from '@/types/metrics'

export function useMetrics() {
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMetrics = useCallback(async () => {
    try {
      const res = await fetch('/api/metrics')
      if (!res.ok) return
      const data = await res.json()
      setMetrics(data)
    } catch {
      // keep stale data on error
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    const t = setInterval(fetchMetrics, 15_000)
    return () => clearInterval(t)
  }, [fetchMetrics])

  return { metrics, loading }
}
