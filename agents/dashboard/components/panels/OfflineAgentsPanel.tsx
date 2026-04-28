'use client';

// 👻 OfflineAgentsPanel
// Shows agents defined in docker-compose but NOT appearing in the live health feed.
// Helps spot ghost agents — running but not registered, or fully down.

import { useMemo } from 'react';
import { Ghost, AlertCircle } from 'lucide-react';
import { KNOWN_AGENTS } from '@/data/knownServices';
import type { SystemHealthData } from '@/lib/api';

interface OfflineAgentsPanelProps {
  /** Live health data from useDockerServices — keyed by container name */
  services: Record<string, SystemHealthData>;
  loading: boolean;
}

export function OfflineAgentsPanel({ services, loading }: OfflineAgentsPanelProps) {
  const offline = useMemo(() => {
    if (loading) return [];

    const liveNames = new Set(
      Object.keys(services).map((n) => n.toLowerCase().replace(/^[\/]/, ''))
    );

    return KNOWN_AGENTS.filter((agent) => {
      const key = agent.name.toLowerCase();
      // Not in live feed at all → offline/ghost
      if (!liveNames.has(key)) return true;
      // In live feed but explicitly down
      const s = services[agent.name]?.status ?? services[agent.name.replace(/-/g, '_')]?.status;
      return s === 'down' || s === 'unhealthy';
    });
  }, [services, loading]);

  if (loading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 bg-zinc-800 rounded w-full" />
        ))}
      </div>
    );
  }

  if (offline.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>All known agents accounted for 🎉</span>
      </div>
    );
  }

  // Group by profile so you know which compose flag starts them
  const grouped = offline.reduce<Record<string, typeof offline>>((acc, agent) => {
    const key = agent.profiles.length > 0 ? agent.profiles.join(', ') : 'always-on';
    if (!acc[key]) acc[key] = [];
    acc[key].push(agent);
    return acc;
  }, {});

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Ghost className="w-4 h-4 text-red-400" />
        <span className="text-xs font-bold uppercase tracking-widest text-red-400">
          {offline.length} Ghost Agent{offline.length !== 1 ? 's' : ''}
        </span>
      </div>

      {Object.entries(grouped).map(([profile, agents]) => (
        <div key={profile}>
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
            profile: <span className="text-zinc-400">{profile}</span>
          </p>
          <ul className="space-y-1">
            {agents.map((agent) => (
              <li
                key={agent.name}
                className="flex items-center justify-between rounded border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <Ghost className="w-3 h-3 text-red-400 shrink-0" />
                  <span className="text-red-200 font-medium">{agent.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  {agent.port && (
                    <span className="font-mono text-[10px] text-zinc-600">:{agent.port}</span>
                  )}
                  <span className="font-mono text-[10px] text-zinc-600">{agent.name}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <p className="text-[10px] text-zinc-600">
        Start missing agents: <code className="text-zinc-400">docker compose --profile agents up -d</code>
      </p>
    </div>
  );
}
