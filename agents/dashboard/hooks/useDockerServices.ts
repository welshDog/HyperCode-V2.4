import { useCallback, useEffect, useState } from 'react'
import { fetchSystemHealth, type SystemHealthData } from '@/lib/api'

export function useDockerServices(pollMs = 15_000) {
  const [services, setServices] = useState<Record<string, SystemHealthData>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch_ = useCallback(async () => {
    try {
      const data = await fetchSystemHealth()
      setServices(data)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'System health unavailable')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch_()
    const id = setInterval(fetch_, pollMs)
    return () => clearInterval(id)
  }, [fetch_, pollMs])

  return { services, loading, error, refetch: fetch_ }
}
