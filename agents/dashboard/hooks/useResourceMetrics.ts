// 📊 Resource Metrics Hook — polls /api/metrics every 5s
// Keeps 60-point history for response-time / error-rate chart
// Falls back to /api/metrics (MetricsSnapshot) — resource-level Docker stats
// will be added once a dedicated /api/v1/system/resources endpoint is ready.

import { useEffect, useState } from 'react';

interface ServiceMetrics {
  cpu_percent: number;
  memory_mb: number;
  memory_limit_mb: number;
}

interface SystemMetrics {
  timestamp: string;
  services: Record<string, ServiceMetrics>;
  system: {
    cpu: number;
    memory: number;
    memory_total: number;
  };
}

interface MetricsPoint {
  time: string;
  cpu: number;
  memory: number;
}

export function useResourceMetrics() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [history, setHistory] = useState<MetricsPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        // Use /api/metrics (MetricsSnapshot) until a dedicated resource endpoint exists.
        // Build a SystemMetrics-compatible shape from the available data.
        const res = await fetch('/api/metrics');
        if (!res.ok) throw new Error('Metrics fetch failed');
        const snap = await res.json();

        const errorPct: number = typeof snap.errorRatePct === 'number' ? snap.errorRatePct : 0;
        const avgMs: number = typeof snap.avgResponseMs === 'number' ? snap.avgResponseMs : 0;
        // Treat error rate as a proxy for "cpu pressure" and avg response time as memory proxy
        // until cAdvisor/Docker stats endpoint is available.
        const adapted: SystemMetrics = {
          timestamp: snap.collectedAt ?? new Date().toISOString(),
          services: {},
          system: {
            cpu: errorPct,
            memory: Math.min(avgMs, 1000),
            memory_total: 1000,
          },
        };
        setMetrics(adapted);
        setHistory(prev => [
          ...prev.slice(-59),
          {
            time: new Date().toLocaleTimeString(),
            cpu: adapted.system.cpu,
            memory: (adapted.system.memory / adapted.system.memory_total) * 100,
          }
        ]);
        setError(null);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Metrics unavailable');
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  return { metrics, history, error };
}
