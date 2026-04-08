// ⚡ Task Velocity Hook — polls /api/queue/stats every 5s
// Keeps 24-point history for velocity chart

import { useEffect, useState } from 'react';

interface QueueStats {
  total_tasks: number;
  queued: number;
  in_progress: number;
  completed: number;
  avg_latency_ms: number;
  tasks_per_hour: number;
  health: 'healthy' | 'degraded' | 'critical';
}

interface VelocityPoint {
  time: string;
  velocity: number;
}

export function useTaskVelocity() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [history, setHistory] = useState<VelocityPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('/api/queue/stats');
        if (!res.ok) throw new Error('Queue stats fetch failed');
        const data: QueueStats = await res.json();
        setStats(data);
        setHistory(prev => [
          ...prev.slice(-23),
          { time: new Date().toLocaleTimeString(), velocity: data.tasks_per_hour }
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

  return { stats, history, error };
}
