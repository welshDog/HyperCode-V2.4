// 🦅 HyperStation — Healer Agent Telemetry Hooks
// Polls healer-agent REST endpoints every 15s
// Three hooks: XP status, heal history, circuit breaker state
// Uses the same pattern as useAgentStatus.ts (useState + useEffect)

import { useEffect, useState, useCallback } from 'react';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface HealerXPStatus {
  agent_id: string;
  xp_total: number;
  coins_total: number;
  level: number;
}

export interface HealEvent {
  message_id: string;
  agent_id: string;
  agent_type: string;
  task_id: string;
  status: 'healing_success' | 'failed' | string;
  payload: Record<string, unknown>;
  error_trace: string | null;
  error_category: string | null;
  xp_earned: number;
  broski_coins: number;
  duration_ms: number | null;
  timestamp: string;
  session_id: string | null;
  healed_agent_id: string;
  heal_pattern: string;
  recurrence_count: number;
  auto_resolved: boolean;
}

export interface CircuitBreakerStatus {
  [agentName: string]: {
    state: 'closed' | 'open' | 'half_open';
    failure_count: number;
    last_failure_time: string | null;
  };
}

// ── Internal fetch helper ──────────────────────────────────────────────────────
// Calls the Next.js API proxy route so the browser never cross-origins to :8010
async function healerFetch<T>(path: string): Promise<T> {
  const res = await fetch(`/api/healer${path}`);
  if (!res.ok) throw new Error(`Healer API ${path} returned ${res.status}`);
  return res.json() as Promise<T>;
}

// ── Hook: XP Status ────────────────────────────────────────────────────────────
// Returns current XP total, BROski$ coins, and level for healer-01
export function useHealerXP(pollMs = 15_000) {
  const [data, setData] = useState<HealerXPStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const xp = await healerFetch<HealerXPStatus>('/xp/status');
      setData(xp);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, pollMs);
    return () => clearInterval(id);
  }, [fetch_, pollMs]);

  return { data, loading, error, refetch: fetch_ };
}

// ── Hook: Heal Event History ────────────────────────────────────────────────────
// Returns last 20 heal events — the live Mission Log feed
export function useHealHistory(pollMs = 15_000) {
  const [events, setEvents] = useState<HealEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const history = await healerFetch<HealEvent[]>('/xp/history');
      setEvents(history);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, pollMs);
    return () => clearInterval(id);
  }, [fetch_, pollMs]);

  return { events, loading, error, refetch: fetch_ };
}

// ── Hook: Circuit Breaker State ─────────────────────────────────────────────────
// Returns per-agent circuit breaker state for the Neural Net panel
export function useCircuitBreakers(pollMs = 15_000) {
  const [status, setStatus] = useState<CircuitBreakerStatus>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    try {
      const data = await healerFetch<CircuitBreakerStatus>('/circuit-breaker/status');
      setStatus(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, pollMs);
    return () => clearInterval(id);
  }, [fetch_, pollMs]);

  return { status, loading, error, refetch: fetch_ };
}
