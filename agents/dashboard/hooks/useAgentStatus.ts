// 🦅 HyperStation — Live Agent Status WebSocket Hook
// Connects to FastAPI backend WS /api/v1/ws/agents (port 8000)
// Auto-reconnects with exponential backoff (3s → 6s → 12s … cap 30s)

import { useEffect, useState } from 'react';

interface Agent {
  id: string;
  name: string;
  status: 'idle' | 'thinking' | 'working' | 'error' | 'online' | 'offline' | 'busy';
  lastActivity?: string;
  last_seen?: string;
  skills?: string[];
}

interface UseAgentStatusReturn {
  agents: Agent[];
  connected: boolean;
  error: string | null;
}

function wsUrl(): string {
  const host = (typeof window !== 'undefined' && process.env.NEXT_PUBLIC_CORE_WS_HOST)
    ? process.env.NEXT_PUBLIC_CORE_WS_HOST
    : (typeof window !== 'undefined' ? window.location.hostname : 'localhost');
  const port = process.env.NEXT_PUBLIC_CORE_WS_PORT ?? '8000';
  return `ws://${host}:${port}/api/v1/ws/agents`;
}

export function useAgentStatus(): UseAgentStatusReturn {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let delay = 3_000;
    let destroyed = false;

    const connect = () => {
      if (destroyed) return;
      try {
        ws = new WebSocket(wsUrl());

        ws.onopen = () => {
          delay = 3_000; // reset backoff on success
          setConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setAgents(data.agents || []);
            setError(null);
          } catch {
            setError('Failed to parse agent data');
          }
        };

        ws.onerror = () => {
          setError(`WebSocket error — retrying in ${delay / 1000}s`);
        };

        ws.onclose = () => {
          setConnected(false);
          if (!destroyed) {
            reconnectTimer = setTimeout(() => {
              delay = Math.min(delay * 2, 30_000); // exponential backoff, cap 30s
              connect();
            }, delay);
          }
        };
      } catch {
        setError('Could not connect to backend');
        if (!destroyed) {
          reconnectTimer = setTimeout(() => {
            delay = Math.min(delay * 2, 30_000);
            connect();
          }, delay);
        }
      }
    };

    connect();

    return () => {
      destroyed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  return { agents, connected, error };
}
