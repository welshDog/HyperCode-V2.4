'use client';

/**
 * AgentMonitor — live agent status panel.
 *
 * ⚠️ WIRING FIX (2026-05-21 audit):
 * The original version pointed at `GET /agents/stream` (SSE) — that endpoint
 * DOES NOT EXIST in the backend. Rewired to poll `GET /orchestrator/agents`,
 * which is the real endpoint (see backend/app/api/v1/endpoints/orchestrator.py).
 *
 * TWO UNKNOWNS still need a live test before this counts as "verified working":
 *  1. AUTH — /orchestrator/agents is gated by `get_current_active_user` (JWT).
 *     This component sends `X-API-Key` via api-client. If the dashboard's auth
 *     is JWT/cookie-only, calls may 401 — confirm against a running stack.
 *  2. SHAPE — /orchestrator/agents proxies to the crew-orchestrator service
 *     and returns its raw payload (or [] on failure). The exact field names
 *     are unconfirmed. `normalizeAgent()` maps defensively with safe fallbacks
 *     so a shape mismatch degrades gracefully instead of crashing the panel.
 */

import { useCallback, useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/lib/api-client';

interface Agent {
  id: string;
  name: string;
  status: 'healthy' | 'busy' | 'error' | 'offline';
  latency: number;
  taskCount: number;
  memory: number;
  cpu: number;
  port: number;
  uptime: number;
}

const POLL_INTERVAL_MS = 5000;
const VALID_STATUS = ['healthy', 'busy', 'error', 'offline'] as const;

/** Map an unknown-shape payload item into a safe Agent (handles snake_case + camelCase). */
function normalizeAgent(raw: Record<string, unknown>, index: number): Agent {
  const num = (...candidates: unknown[]): number => {
    for (const c of candidates) {
      const n = Number(c);
      if (Number.isFinite(n) && c !== undefined && c !== null) return n;
    }
    return 0;
  };
  const status = VALID_STATUS.includes(raw?.status as Agent['status'])
    ? (raw.status as Agent['status'])
    : 'offline';

  return {
    id: String(raw?.id ?? raw?.name ?? `agent-${index}`),
    name: String(raw?.name ?? raw?.id ?? `Agent ${index + 1}`),
    status,
    latency: num(raw?.latency, raw?.latency_ms),
    taskCount: num(raw?.taskCount, raw?.task_count, raw?.tasks),
    memory: num(raw?.memory, raw?.memory_mb),
    cpu: num(raw?.cpu, raw?.cpu_percent),
    port: num(raw?.port),
    uptime: num(raw?.uptime, raw?.uptime_seconds),
  };
}

export function AgentMonitor() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      // Real endpoint — backend/app/api/v1/endpoints/orchestrator.py @router.get("/agents")
      const data = await apiClient.get<unknown>('/orchestrator/agents');
      const list: Record<string, unknown>[] = Array.isArray(data)
        ? (data as Record<string, unknown>[])
        : (((data as Record<string, unknown>)?.agents as Record<string, unknown>[]) ?? []);
      setAgents(list.map(normalizeAgent));
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? `Failed to load agents: ${err.message}`
          : 'Failed to load agents',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    const id = setInterval(fetchAgents, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchAgents]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'busy':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'offline':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500">Loading agent data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-800">{error}</p>
        <p className="mt-1 text-xs text-red-600">
          Endpoint: <code>GET /orchestrator/agents</code> — check the backend is
          running and the dashboard is authenticated.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {agents.map((agent) => (
          <Card key={agent.id} className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <CardTitle className="text-base">{agent.name}</CardTitle>
                <Badge className={getStatusColor(agent.status)}>
                  {agent.status}
                </Badge>
              </div>
              {agent.port > 0 && (
                <p className="text-xs text-gray-500">Port {agent.port}</p>
              )}
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Latency:</span>
                <span className="font-mono font-semibold">{agent.latency}ms</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Tasks:</span>
                <span className="font-mono font-semibold">{agent.taskCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Memory:</span>
                <span className="font-mono font-semibold">{agent.memory}MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">CPU:</span>
                <span className="font-mono font-semibold">{agent.cpu}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Uptime:</span>
                <span className="font-mono font-semibold text-green-600">
                  {Math.floor(agent.uptime / 3600)}h
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {agents.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <p className="text-gray-500">No agents online</p>
        </div>
      )}
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
        <p>
          🟢 {agents.filter((a) => a.status === 'healthy').length} healthy •
          🟡 {agents.filter((a) => a.status === 'busy').length} busy •
          🔴 {agents.filter((a) => a.status === 'error').length} errors •
          ⚪ {agents.filter((a) => a.status === 'offline').length} offline
          <span className="ml-2 text-blue-500">(polls every {POLL_INTERVAL_MS / 1000}s)</span>
        </p>
      </div>
    </div>
  );
}
