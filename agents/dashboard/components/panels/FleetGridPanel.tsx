// Mission Control — Agent Fleet grid.
// Live roster from the agent-registry: every defined agent, its container
// health, memory, and restart history. Trouble sorts to the front.

'use client'

import { useMemo } from 'react'
import { useFleet, type FleetAgent, type FleetSummary } from '../../hooks/useFleet'

const STATUS_CONFIG: Record<string, { dot: string; text: string; label: string; rank: number }> = {
  crash_loop:   { dot: 'bg-red-500 animate-pulse', text: 'text-red-400',     label: 'CRASH LOOP', rank: 0 },
  down:         { dot: 'bg-red-500',               text: 'text-red-400',     label: 'Down',       rank: 1 },
  running:      { dot: 'bg-cyan-400',              text: 'text-cyan-400/80', label: 'Running',    rank: 2 },
  healthy:      { dot: 'bg-emerald-400',           text: 'text-emerald-400', label: 'Healthy',    rank: 3 },
  not_deployed: { dot: 'bg-gray-700',              text: 'text-gray-600',    label: 'Not deployed', rank: 4 },
}

function statusKey(agent: FleetAgent): string {
  if (agent.crash_loop) return 'crash_loop'
  return STATUS_CONFIG[agent.status] ? agent.status : 'down'
}

function FleetSummaryStrip({ summary }: { summary: FleetSummary }): React.JSX.Element {
  const live = summary.healthy + summary.running
  return (
    <div className="flex items-baseline gap-4 flex-wrap">
      <span>
        <span className="text-3xl font-bold text-emerald-400 tabular-nums">{live}</span>
        <span className="ml-1.5 text-xs text-gray-400">live</span>
      </span>
      <span className="text-xs text-gray-500 tabular-nums">
        {summary.down > 0 && <span className="text-red-400 font-medium">{summary.down} down · </span>}
        {summary.crash_looping > 0 && (
          <span className="text-red-400 font-medium">{summary.crash_looping} crash-looping · </span>
        )}
        {summary.not_deployed} dormant · {summary.total} total
      </span>
      {summary.auto_restart_enabled && (
        <span className="ml-auto rounded-full bg-cyan-950/60 px-2 py-0.5 text-[10px] font-mono text-cyan-400/80">
          AUTO-HEAL ON
        </span>
      )}
    </div>
  )
}

function FleetCard({ agent }: { agent: FleetAgent }): React.JSX.Element {
  const key = statusKey(agent)
  const cfg = STATUS_CONFIG[key]
  const dormant = key === 'not_deployed'
  return (
    <li
      className={`rounded-lg border p-3 text-xs ${
        dormant
          ? 'border-gray-900 bg-gray-950/40 opacity-60'
          : 'border-gray-800 bg-gray-900/60 hover:border-gray-700'
      }`}
      aria-label={`${agent.name} — ${cfg.label}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full shrink-0 ${cfg.dot}`} aria-hidden />
        <span className="font-semibold text-white truncate">{agent.name}</span>
        <span className={`ml-auto font-medium shrink-0 ${cfg.text}`}>{cfg.label}</span>
      </div>
      <p className="mt-1 text-gray-500 truncate">{agent.role}</p>
      {!dormant && (
        <div className="mt-2 flex gap-3 font-mono text-[10px] text-gray-600 tabular-nums">
          {typeof agent.memory_usage_mb === 'number' && <span>{agent.memory_usage_mb.toFixed(0)} MB</span>}
          {(agent.restart_count ?? 0) > 0 && <span>{agent.restart_count} restarts</span>}
          {(agent.auto_restarts_issued ?? 0) > 0 && (
            <span className="text-cyan-400/60">{agent.auto_restarts_issued} auto-heals</span>
          )}
        </div>
      )}
    </li>
  )
}

export default function FleetGridPanel(): React.JSX.Element {
  const { summary, agents, error, loading } = useFleet()

  const sorted = useMemo(
    () =>
      [...agents].sort(
        (a, b) =>
          (STATUS_CONFIG[statusKey(a)]?.rank ?? 9) - (STATUS_CONFIG[statusKey(b)]?.rank ?? 9) ||
          a.name.localeCompare(b.name)
      ),
    [agents]
  )

  return (
    <section aria-label="Agent Fleet" className="flex flex-col gap-3">
      <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">Agent Fleet</h2>

      {summary && <FleetSummaryStrip summary={summary} />}

      {error && (
        <p role="alert" className="text-xs text-red-400">
          Registry unreachable: {error}
        </p>
      )}

      {loading && !error && (
        <p className="text-xs text-gray-500 animate-pulse">Scanning the fleet…</p>
      )}

      {!loading && !error && agents.length === 0 && (
        <p className="text-xs text-gray-500">No agents in the registry yet.</p>
      )}

      <ul className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
        {sorted.map((agent) => (
          <FleetCard key={agent.name} agent={agent} />
        ))}
      </ul>
    </section>
  )
}
