// HyperStation - Healer Mission Log Panel
// Drops into the MISSION LOG tab
// Shows last 20 heal events: who was healed, what pattern, XP earned
// Auto-refreshes every 15s via useHealHistory hook

'use client';

import { useHealHistory, useHealerXP } from '../../hooks/useHealerTelemetry';

// -- Helpers ------------------------------------------------------------------

function healPatternEmoji(pattern: string): string {
  const map: Record<string, string> = {
    docker_restart : 'restart',
    oom_restart    : 'oom',
    crash_loop     : 'loop',
    timeout        : 'timeout',
    probe_fail     : 'probe',
  };
  return map[pattern] ?? 'fix';
}

function statusColour(status: string): string {
  if (status === 'healing_success') return 'text-emerald-400';
  if (status === 'failed')          return 'text-red-400';
  return 'text-yellow-400';
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1)  return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24)  return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// -- XP Status Bar ------------------------------------------------------------

function XPStatusBar(): React.JSX.Element | null {
  const { data, loading, error } = useHealerXP();

  if (loading) return <p className="text-xs text-gray-500 animate-pulse">Loading XP...</p>;
  if (error || !data) return <p className="text-xs text-red-400">Healer offline</p>;

  const xpForNextLevel = data.level * 100;
  const xpProgress     = Math.min((data.xp_total % xpForNextLevel) / xpForNextLevel, 1);

  return (
    <div className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/40 p-3">
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="font-bold text-emerald-400">Healer: {data.agent_id}</span>
        <span className="text-gray-400">Lv.{data.level} &middot; {data.xp_total} XP &middot; {data.coins_total.toFixed(1)} coins</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-gray-800">
        <div
          className="h-1.5 rounded-full bg-emerald-500 transition-all duration-700"
          style={{ width: `${xpProgress * 100}%` }}
        />
      </div>
    </div>
  );
}

// -- Main Panel ---------------------------------------------------------------

export default function HealerMissionLog(): React.JSX.Element {
  const { events, loading, error } = useHealHistory();

  return (
    <section aria-label="Healer Mission Log" className="flex flex-col gap-2">

      <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400">Heal Log</h2>

      <XPStatusBar />

      {loading && (
        <p className="text-xs text-gray-500 animate-pulse">Connecting to healer...</p>
      )}

      {error && !loading && (
        <p className="text-xs text-red-400">Error: {error}</p>
      )}

      {!loading && events.length === 0 && (
        <p className="text-xs text-gray-500">No heal events yet - all systems healthy</p>
      )}

      <ul className="flex flex-col gap-2">
        {events.map((event) => (
          <li
            key={event.message_id}
            className="rounded-lg border border-gray-800 bg-gray-900/60 p-3 text-xs"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-cyan-600 shrink-0">
                [{healPatternEmoji(event.heal_pattern)}]
              </span>
              <span className="font-semibold text-white">
                {event.healed_agent_id}
              </span>
              <span className="ml-auto font-mono text-gray-500">
                {relativeTime(event.timestamp)}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span className={`font-medium ${statusColour(event.status)}`}>
                {event.status === 'healing_success' ? 'Healed' : 'Failed'}
              </span>
              <span className="text-gray-400">
                +{event.xp_earned} XP &middot; {event.broski_coins} coins
              </span>
              <span className="text-gray-600 capitalize">
                {event.heal_pattern.replace(/_/g, ' ')}
              </span>
            </div>

            {event.error_trace && (
              <p className="mt-1 font-mono text-red-400 truncate">
                {event.error_trace}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
