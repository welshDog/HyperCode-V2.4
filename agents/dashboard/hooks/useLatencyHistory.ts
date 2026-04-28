// 📊 useLatencyHistory
// Stores the last N latency readings per service name.
// Feed it fresh SystemHealthData on each poll tick.

import { useRef, useState, useEffect } from 'react';
import type { SystemHealthData } from '@/lib/api';

const MAX_HISTORY = 20; // keep last 20 data points (~5 min at 15s poll)

export function useLatencyHistory(
  services: Record<string, SystemHealthData>,
  maxPoints = MAX_HISTORY
): Record<string, number[]> {
  const historyRef = useRef<Record<string, number[]>>({});
  const [snapshot, setSnapshot] = useState<Record<string, number[]>>({});

  useEffect(() => {
    let changed = false;
    for (const [name, data] of Object.entries(services)) {
      const ms = data.latency_ms ?? null;
      if (ms === null || ms === undefined) continue;
      if (!historyRef.current[name]) {
        historyRef.current[name] = [];
      }
      historyRef.current[name].push(ms);
      if (historyRef.current[name].length > maxPoints) {
        historyRef.current[name] = historyRef.current[name].slice(-maxPoints);
      }
      changed = true;
    }
    if (changed) {
      setSnapshot({ ...historyRef.current });
    }
  }, [services, maxPoints]);

  return snapshot;
}
