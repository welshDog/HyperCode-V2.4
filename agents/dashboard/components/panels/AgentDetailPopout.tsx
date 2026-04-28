'use client';

// 🔍 AgentDetailPopout
// Slide-in panel — click any agent card to see:
//   • Full status + circuit breaker state
//   • Skills list
//   • Last activity / last seen
//   • Last 10 logs (fetched from /api/v1/logs?agent=<id>)

import { useEffect, useState, useCallback } from 'react';
import { X, Activity, Cpu, Clock, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { CORE_ORIGIN } from '@/lib/api';

export interface AgentSummary {
  id: string;
  name: string;
  status: string;
  lastActivity?: string;
  last_seen?: string;
  skills?: string[];
  circuitState?: string;
  circuitFailures?: number;
}

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

interface AgentDetailPopoutProps {
  agent: AgentSummary | null;
  onClose: () => void;
}

function statusColour(s: string) {
  if (s === 'working' || s === 'online' || s === 'healthy') return 'text-emerald-400';
  if (s === 'thinking' || s === 'busy' || s === 'starting') return 'text-yellow-400';
  if (s === 'error' || s === 'offline' || s === 'down') return 'text-red-400';
  return 'text-zinc-400';
}

function circuitColour(state: string) {
  if (state === 'open') return 'text-red-400';
  if (state === 'half_open') return 'text-yellow-400';
  return 'text-emerald-400';
}

export function AgentDetailPopout({ agent, onClose }: AgentDetailPopoutProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const fetchLogs = useCallback(async (agentId: string) => {
    setLogsLoading(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') || '' : '';
      const res = await fetch(
        `${CORE_ORIGIN}/api/v1/logs?agent=${encodeURIComponent(agentId)}&limit=10`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      if (res.ok) {
        const data = await res.json();
        setLogs(Array.isArray(data) ? data : data?.logs ?? []);
      } else {
        setLogs([]);
      }
    } catch {
      setLogs([]);
    } finally {
      setLogsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (agent) {
      setLogs([]);
      fetchLogs(agent.id);
    }
  }, [agent, fetchLogs]);

  if (!agent) return null;

  const cbState = agent.circuitState ?? 'closed';

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Slide-in panel */}
      <aside
        className="fixed right-0 top-0 z-50 h-full w-full max-w-md bg-zinc-950 border-l border-zinc-800 shadow-2xl flex flex-col"
        role="dialog"
        aria-label={`Agent detail: ${agent.name}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800">
          <div>
            <h2 className="text-sm font-bold text-white">{agent.name}</h2>
            <p className="font-mono text-[10px] text-zinc-500">{agent.id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 custom-scrollbar">

          {/* Status row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
              <div className="flex items-center gap-1 text-[10px] text-zinc-500 mb-1 uppercase tracking-wider">
                <Activity className="w-3 h-3" /> Status
              </div>
              <p className={`text-sm font-bold capitalize ${statusColour(agent.status)}`}>
                {agent.status}
              </p>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
              <div className="flex items-center gap-1 text-[10px] text-zinc-500 mb-1 uppercase tracking-wider">
                <Cpu className="w-3 h-3" /> Circuit Breaker
              </div>
              <p className={`text-sm font-bold ${circuitColour(cbState)}`}>
                {cbState.replace('_', ' ').toUpperCase()}
                {(agent.circuitFailures ?? 0) > 0 && (
                  <span className="ml-1 text-xs text-zinc-500">({agent.circuitFailures} fails)</span>
                )}
              </p>
            </div>
          </div>

          {/* Last activity */}
          {(agent.lastActivity || agent.last_seen) && (
            <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
              <div className="flex items-center gap-1 text-[10px] text-zinc-500 mb-1 uppercase tracking-wider">
                <Clock className="w-3 h-3" /> Last Activity
              </div>
              <p className="text-xs text-zinc-300">{agent.lastActivity ?? agent.last_seen}</p>
            </div>
          )}

          {/* Skills */}
          {agent.skills && agent.skills.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-2">Skills</p>
              <div className="flex flex-wrap gap-1.5">
                {agent.skills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded bg-zinc-800 border border-zinc-700 px-2 py-1 font-mono text-[10px] text-zinc-300"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Logs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] uppercase tracking-wider text-zinc-500">Last 10 Logs</p>
              <button
                onClick={() => fetchLogs(agent.id)}
                className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                ↺ Refresh
              </button>
            </div>

            {logsLoading ? (
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <Loader2 className="w-3 h-3 animate-spin" /> Fetching logs...
              </div>
            ) : logs.length === 0 ? (
              <p className="text-xs text-zinc-600">No logs available for this agent.</p>
            ) : (
              <ul className="space-y-1 font-mono text-[10px]">
                {logs.map((log, i) => (
                  <li
                    key={i}
                    className={`flex gap-2 rounded px-2 py-1 ${
                      log.level === 'ERROR' || log.level === 'CRITICAL'
                        ? 'bg-red-500/5 text-red-300'
                        : log.level === 'WARNING'
                        ? 'bg-yellow-500/5 text-yellow-300'
                        : 'bg-zinc-900 text-zinc-400'
                    }`}
                  >
                    <span className="shrink-0 text-zinc-600">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`shrink-0 w-12 ${
                      log.level === 'ERROR' ? 'text-red-400' :
                      log.level === 'WARNING' ? 'text-yellow-400' :
                      'text-zinc-500'
                    }`}>{log.level}</span>
                    <span className="break-all">{log.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Circuit breaker warning */}
          {cbState === 'open' && (
            <div className="flex items-start gap-2 rounded-lg border border-red-800 bg-red-950/40 p-3 text-xs text-red-400">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>Circuit breaker is OPEN — this agent is failing repeatedly. Check logs above.</span>
            </div>
          )}
          {cbState === 'half_open' && (
            <div className="flex items-start gap-2 rounded-lg border border-yellow-800 bg-yellow-950/40 p-3 text-xs text-yellow-400">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>Circuit breaker is TESTING — agent recovering, monitoring closely.</span>
            </div>
          )}
          {cbState === 'closed' && agent.status !== 'error' && (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-800/50 bg-emerald-950/20 p-3 text-xs text-emerald-400">
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>Agent is healthy and circuit breaker closed.</span>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
