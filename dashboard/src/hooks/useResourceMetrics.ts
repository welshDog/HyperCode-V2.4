// 📊 Resource Metrics Hook — polls /api/metrics/resources every 5s
// Keeps 60-point history for CPU/Memory chart

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
        const res = await fetch('/api/metrics/resources');
        if (!res.ok) throw new Error('Metrics fetch failed');
        const data: SystemMetrics = await res.json();
        setMetrics(data);
        setHistory(prev => [
          ...prev.slice(-59),
          {
            time: new Date().toLocaleTimeString(),
            cpu: data.system.cpu,
            memory: (data.system.memory / data.system.memory_total) * 100
          }
        ]);
        setError(null);
      } catch (e: any) {
        setError(e.message);
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  return { metrics, history, error };
}
