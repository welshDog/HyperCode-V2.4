// 🦅 HyperStation — Live Agent Status WebSocket Hook
// Connects to Orchestrator ws://localhost:8081/ws/agents
// Auto-reconnects with 3s delay on disconnect

import { useEffect, useState } from 'react';

interface Agent {
  id: string;
  name: string;
  status: 'idle' | 'thinking' | 'working' | 'error';
  lastActivity?: string;
  skills?: string[];
}

interface UseAgentStatusReturn {
  agents: Agent[];
  connected: boolean;
  error: string | null;
}

export function useAgentStatus(): UseAgentStatusReturn {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connect = () => {
      try {
        ws = new WebSocket('ws://localhost:8081/ws/agents');

        ws.onopen = () => {
          setConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setAgents(data.agents || []);
            setError(null);
          } catch (e) {
            setError('Failed to parse agent data');
          }
        };

        ws.onerror = () => {
          setError('WebSocket connection failed — retrying in 3s');
        };

        ws.onclose = () => {
          setConnected(false);
          reconnectTimer = setTimeout(connect, 3000);
        };
      } catch (e) {
        setError('Could not connect to Orchestrator');
        reconnectTimer = setTimeout(connect, 3000);
      }
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  return { agents, connected, error };
}
