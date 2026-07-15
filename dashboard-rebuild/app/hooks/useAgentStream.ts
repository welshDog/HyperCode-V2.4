// hooks/useAgentStream.ts
'use client';

import { useEffect, useState } from 'react';

export interface AgentStreamData {
  agents: Array<{
    id: string;
    name: string;
    status: 'healthy' | 'busy' | 'error' | 'offline';
    latency: number;
    taskCount: number;
    memory: number;
    cpu: number;
    port: number;
    uptime: number;
  }>;
  timestamp: number;
}

export function useAgentStream(url: string = 'http://hypercode-core:8000/agents/stream') {
  const [data, setData] = useState<AgentStreamData | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const eventSource = new EventSource(url);

      eventSource.onopen = () => {
        setConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
        } catch (parseError) {
          console.error('Failed to parse agent stream data:', parseError);
        }
      };

      eventSource.onerror = (err) => {
        setConnected(false);
        setError('Connection error');
        console.error('EventSource error:', err);
      };

      return () => {
        eventSource.close();
        setConnected(false);
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setConnected(false);
    }
  }, [url]);

  return { data, connected, error };
}
