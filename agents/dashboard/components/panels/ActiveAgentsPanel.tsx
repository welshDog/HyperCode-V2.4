// HyperStation - Active Agents Panel
// Combines live WebSocket agent roster (useAgentStatus) with
// circuit breaker health (useCircuitBreakers) from the Healer
// Drops into the ACTIVE AGENTS section on the main dashboard

'use client';

import { useAgentStatus } from '../../hooks/useAgentStatus';
import { useCircuitBreakers } from '../../hooks/useHealerTelemetry';

// -- Status config ------------------------------------------------------------

const STATUS_CONFIG: Record<string, { dot: string; label: string; text: string }> = {
  idle     : { dot: 'bg-gray-500',    label: 'Idle',     text: 'text-gray-400'   },
  thinking : { dot: 'bg-yellow-400',  label: 'Thinking', text: 'text-yellow-400' },
  working  : { dot: 'bg-emerald-400', label: 'Working',  text: 'text-emerald-400'},
  error    : { dot: 'bg-red-500',     label: 'Error',    text: 'text-red-400'    },
  online   : { dot: 'bg-emerald-400', label: 'Online',   text: 'text-emerald-400'},
  offline  : { dot: 'bg-red-500',     label: 'Offline',  text: 'text-red-400'    },
  busy     : { dot: 'bg-yellow-400',  label: 'Busy',     text: 'text-yellow-400' },
};

function circuitColour(state: string): string {
  if (state === 'open')      return 'text-red-400';
  if (state === 'half_open') return 'text-yellow-400';
  return 'text-emerald-400';
}

function circuitLabel(state: string): string {
  if (state === 'open')      return 'CB: OPEN';
  if (state === 'half_open') return 'CB: TESTING';
  return 'CB: OK';
}

// -- Single Agent Card --------------------------------------------------------

interface AgentCardProps {
  id: string;
  name: string;
  status: 'idle' | 'thinking' | 'working' | 'error' | 'online' | 'offline' | 'busy';
  lastActivity?: string;
  skills?: string[];
  circuitState?: string;
  circuitFailures?: number;
}

function AgentCard({
  id, name, status, lastActivity, skills, circuitState, circuitFailures
}: AgentCardProps): React.JSX.Element {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle;
  const cbState = circuitState ?? 'closed';

  return (
    <li
      className="rounded-lg border border-gray-800 bg-gray-900/60 p-3 text-xs"
      aria-label={`Agent ${name} - ${cfg.label}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className={`h-2 w-2 rounded-full shrink-0 ${
            status === 'working' ? 'animate-pulse' : ''
          } ${cfg.dot}`}
          aria-hidden
        />
        <span className="font-semibold text-white truncate">{name}</span>
        <span className="ml-auto font-mono text-gray-600 text-[10px]">{id}</span>
      </div>

      <div className="flex items-center gap-3 mb-2">
        <span className={`font-medium ${cfg.text}`}>{cfg.label}</span>
        <span className={`font-medium ${circuitColour(cbState)}`}>
          {circuitLabel(cbState)}
          {(circuitFailures ?? 0) > 0 && (
            <span className="ml-1 text-gray-500">({circuitFailures} fails)</span>
          )}
        </span>
      </div>

      {lastActivity && (
        <p className="text-gray-500 truncate mb-1">{lastActivity}</p>
      )}

      {skills && skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {skills.slice(0, 4).map((s) => (
            <span
              key={s}
              className="rounded bg-gray-800 px-1.5 py-0.5 font-mono text-gray-400"
            >
              {s}
            </span>
          ))}
          {skills.length > 4 && (
            <span className="text-gray-600">+{skills.length - 4} more</span>
          )}
        </div>
      )}
    </li>
  );
}

// -- Main Panel ---------------------------------------------------------------

export default function ActiveAgentsPanel(): React.JSX.Element {
  const { agents, connected, error: wsError } = useAgentStatus();
  const { status: cbStatus, error: cbError }  = useCircuitBreakers();

  const openBreakers = Object.entries(cbStatus).filter(
    ([, cb]) => cb.state !== 'closed'
  );

  return (
    <section aria-label="Active Agents" className="flex flex-col gap-2">

      <div className="flex items-center gap-2">
        <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">
          Active Agents
        </h2>
        <span
          className={`ml-auto rounded-full px-2 py-0.5 text-xs font-medium ${
            connected
              ? 'bg-emerald-900 text-emerald-400'
              : 'bg-gray-800 text-gray-500'
          }`}
        >
          {connected ? 'LIVE' : 'Connecting...'}
        </span>
      </div>

      {openBreakers.length > 0 && (
        <div
          role="alert"
          className="rounded border border-red-800 bg-red-950/40 px-3 py-2 text-xs text-red-400"
        >
          Warning: {openBreakers.length} circuit breaker{openBreakers.length > 1 ? 's' : ''} tripped:{' '}
          {openBreakers.map(([name]) => name).join(', ')}
        </div>
      )}

      {(wsError || cbError) && (
        <p className="text-xs text-red-400">Error: {wsError ?? cbError}</p>
      )}

      {!connected && !wsError && (
        <p className="text-xs text-gray-500 animate-pulse">Connecting to Neural Net...</p>
      )}

      {connected && agents.length === 0 && (
        <p className="text-xs text-gray-500">No agents registered yet.</p>
      )}

      <ul className="flex flex-col gap-2">
        {agents.map((agent) => {
          const cb = cbStatus[agent.id];
          return (
            <AgentCard
              key={agent.id}
              id={agent.id}
              name={agent.name}
              status={agent.status}
              lastActivity={agent.lastActivity}
              skills={agent.skills}
              circuitState={cb?.state}
              circuitFailures={cb?.failure_count}
            />
          );
        })}
      </ul>
    </section>
  );
}
