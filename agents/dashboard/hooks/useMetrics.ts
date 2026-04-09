'use client'

import { useState, useEffect, useCallback } from 'react'
import type { MetricsSnapshot } from '@/types/metrics'

export function useMetrics(onRefetchComplete?: (success: boolean) => void) {
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMetrics = useCallback(async (isManual = false) => {
    try {
      const res = await fetch('/api/metrics')
      if (!res.ok) throw new Error('Bad response')
      const data = await res.json()
      setMetrics(data)
      if (isManual && onRefetchComplete) onRefetchComplete(true)
    } catch {
      // keep stale data on error
      if (isManual && onRefetchComplete) onRefetchComplete(false)
    } finally {
      setLoading(false)
    }
  }, [onRefetchComplete])

  useEffect(() => {
    fetchMetrics(false)
    const t = setInterval(() => fetchMetrics(false), 15_000)
    return () => clearInterval(t)
  }, [fetchMetrics])

  return { metrics, loading, refetch: () => fetchMetrics(true) }
}
