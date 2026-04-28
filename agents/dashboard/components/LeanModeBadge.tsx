'use client';

// 🏷️ LeanModeBadge
// Reads active Docker profiles from the /api/v1/orchestrator/system/health response.
// Cross-references against KNOWN_SERVICES to figure out which profile is active.
// Shows a coloured badge in the dashboard header.

import { useMemo } from 'react';
import { Zap, Layers, Server } from 'lucide-react';
import type { SystemHealthData } from '@/lib/api';
import { KNOWN_SERVICES } from '@/data/knownServices';

interface LeanModeBadgeProps {
  services: Record<string, SystemHealthData>;
  loading: boolean;
}

type Mode = 'lean' | 'standard' | 'agents' | 'hyper' | 'full' | 'unknown';

function detectMode(liveNames: Set<string>): Mode {
  const has = (name: string) => liveNames.has(name);

  const hasHyper = has('hyper-architect') || has('agent-x') || has('hyper-worker');
  const hasAgents = has('coder-agent') || has('crew-orchestrator') || has('project-strategist');
  const hasHealth = has('hyperhealth-api');

  // Count always-on services that are alive
  const alwaysOn = KNOWN_SERVICES.filter((s) => s.profiles.length === 0);
  const alwaysOnAlive = alwaysOn.filter((s) => liveNames.has(s.name)).length;
  const alwaysOnRatio = alwaysOnAlive / alwaysOn.length;

  if (hasHyper) return 'hyper';
  if (hasHealth && hasAgents) return 'full';
  if (hasAgents) return 'agents';
  if (alwaysOnRatio >= 0.7) return 'standard';
  if (alwaysOnRatio >= 0.3) return 'lean';
  return 'unknown';
}

const MODE_CONFIG: Record<Mode, { label: string; colour: string; icon: React.ReactNode; desc: string }> = {
  lean:     { label: 'Lean Mode',     colour: 'bg-blue-500/20 border-blue-500/40 text-blue-300',    icon: <Zap className="w-3 h-3" />,    desc: 'Core services only' },
  standard: { label: 'Standard',      colour: 'bg-zinc-700/50 border-zinc-600 text-zinc-300',        icon: <Server className="w-3 h-3" />, desc: 'Full infra, no agents' },
  agents:   { label: 'Agents Mode',   colour: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300', icon: <Layers className="w-3 h-3" />, desc: 'Agents profile active' },
  hyper:    { label: '⚡ Hyper Mode',  colour: 'bg-purple-500/20 border-purple-500/40 text-purple-300', icon: <Zap className="w-3 h-3" />,    desc: 'All systems GO' },
  full:     { label: 'Full Stack',    colour: 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300',      icon: <Layers className="w-3 h-3" />, desc: 'Health + agents active' },
  unknown:  { label: 'Unknown',       colour: 'bg-zinc-800 border-zinc-700 text-zinc-500',            icon: <Server className="w-3 h-3" />, desc: 'Waiting for data...' },
};

export function LeanModeBadge({ services, loading }: LeanModeBadgeProps) {
  const mode = useMemo<Mode>(() => {
    if (loading || Object.keys(services).length === 0) return 'unknown';
    const liveNames = new Set(
      Object.keys(services).map((n) => n.toLowerCase().replace(/^\//, ''))
    );
    return detectMode(liveNames);
  }, [services, loading]);

  const cfg = MODE_CONFIG[mode];

  return (
    <div
      title={cfg.desc}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
        cfg.colour
      }`}
    >
      {cfg.icon}
      {cfg.label}
    </div>
  );
}
