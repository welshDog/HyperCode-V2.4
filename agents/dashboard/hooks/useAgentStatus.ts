// 🦅 HyperStation — Live Agent Status WebSocket Hook
// Connects to FastAPI backend WS /api/v1/ws/agents (port 8000)
// Auto-reconnects with exponential backoff (3s → 6s → 12s … cap 30s)

import { useEffect, useState } from 'react';
import { fetchAgents } from '@/lib/api';

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

function normaliseStatus(raw: unknown): Agent['status'] {
  const s = typeof raw === 'string' ? raw.toLowerCase() : ''
  if (s === 'idle') return 'idle'
  if (s === 'thinking') return 'thinking'
  if (s === 'working') return 'working'
  if (s === 'busy') return 'busy'
  if (s === 'error') return 'error'
  if (s === 'online') return 'online'
  if (s === 'offline') return 'offline'
  if (s === 'healthy' || s === 'ok' || s === 'up') return 'online'
  if (s === 'warning' || s === 'warn' || s === 'degraded') return 'busy'
  if (s === 'down' || s === 'unhealthy' || s === 'failed') return 'offline'
  return 'online'
}

function normaliseAgent(raw: unknown): Agent | null {
  if (!raw || typeof raw !== 'object') return null
  const a = raw as Record<string, unknown>
  const id = typeof a.id === 'string' && a.id ? a.id : typeof a.name === 'string' ? a.name : ''
  const name = typeof a.name === 'string' && a.name ? a.name : id
  if (!id || !name) return null
  const lastActivity = typeof a.lastActivity === 'string'
    ? a.lastActivity
    : typeof a.last_action === 'string'
      ? a.last_action
      : undefined
  const last_seen = typeof a.last_seen === 'string' ? a.last_seen : undefined
  const skills = Array.isArray(a.skills) ? a.skills.filter((s): s is string => typeof s === 'string') : undefined

  return {
    id,
    name,
    status: normaliseStatus(a.status),
    lastActivity,
    last_seen,
    skills,
  }
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

    const seed = async () => {
      try {
        const data: unknown = await fetchAgents()
        const obj = data && typeof data === 'object' ? (data as Record<string, unknown>) : null
        const rawAgents: unknown[] = Array.isArray(obj?.agents)
          ? (obj?.agents as unknown[])
          : Array.isArray(data)
            ? (data as unknown[])
            : []
        const mapped = rawAgents.map(normaliseAgent).filter((x): x is Agent => x != null)
        if (!destroyed && mapped.length > 0) {
          setAgents(mapped)
          setError(null)
        }
      } catch (e) {
        if (!destroyed) setError(e instanceof Error ? e.message : 'Failed to seed agents')
      }
    }

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
            const rawAgents: unknown[] = Array.isArray(data?.agents) ? data.agents : [];
            const mapped = rawAgents.map(normaliseAgent).filter((x): x is Agent => x != null);
            setAgents(mapped);
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

    seed();
    connect();

    return () => {
      destroyed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, []);

  return { agents, connected, error };
}
