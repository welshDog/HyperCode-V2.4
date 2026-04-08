'use client';

import { motion } from 'framer-motion';
import { useEffect, useState, type ComponentType } from 'react';
import { Network, Cpu, Share2, Activity, Shield, Code, Server, Database, Eye, Wifi, WifiOff } from 'lucide-react';
import { useAgentStatus } from '../hooks/useAgentStatus';

// Agent Roles mapped to icons
const AGENT_ICONS: Record<string, ComponentType<{ className?: string }>> = {
  'Project Strategist': Network,
  'Frontend Specialist': Eye,
  'Backend Specialist': Server,
  'Database Architect': Database,
  'QA Engineer': Shield,
  'DevOps Engineer': Cpu,
  'Security Engineer': Shield,
  'System Architect': Share2,
  'Coder Agent': Code,
};

// Status colour mapping
const STATUS_COLOURS: Record<string, string> = {
  working:  'border-green-400  shadow-[0_0_15px_rgba(74,222,128,0.5)]',
  thinking: 'border-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.4)]',
  error:    'border-red-500    shadow-[0_0_15px_rgba(239,68,68,0.5)]',
  idle:     'border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.3)]',
};

const STATUS_DOT: Record<string, string> = {
  working:  'bg-green-400',
  thinking: 'bg-yellow-400 animate-pulse',
  error:    'bg-red-500 animate-ping',
  idle:     'bg-zinc-600',
};

// Fallback static positions — used when WebSocket has no position data
const AGENT_POSITIONS: Record<string, { x: number; y: number }> = {
  strategist: { x: 50, y: 10 },
  frontend:   { x: 20, y: 30 },
  backend:    { x: 80, y: 30 },
  db:         { x: 80, y: 70 },
  qa:         { x: 35, y: 90 },
  devops:     { x: 65, y: 90 },
  security:   { x: 50, y: 50 },
  sysarch:    { x: 50, y: 30 },
  coder:      { x: 20, y: 70 },
};

const NAME_TO_ID: Record<string, string> = {
  'Project Strategist': 'strategist',
  'Frontend Specialist': 'frontend',
  'Backend Specialist':  'backend',
  'Database Architect':  'db',
  'QA Engineer':         'qa',
  'DevOps Engineer':     'devops',
  'Security Engineer':   'security',
  'System Architect':    'sysarch',
  'Coder Agent':         'coder',
};

const CONNECTIONS = [
  ['strategist', 'sysarch'],
  ['sysarch', 'frontend'],
  ['sysarch', 'backend'],
  ['sysarch', 'security'],
  ['backend', 'db'],
  ['frontend', 'coder'],
  ['backend', 'coder'],
  ['coder', 'qa'],
  ['qa', 'devops'],
  ['devops', 'security'],
];

export default function NeuralViz() {
  const { agents: liveAgents, connected, error } = useAgentStatus();
  const [activeSignals, setActiveSignals] = useState<{ id: string; from: string; to: string }[]>([]);

  // Build a quick lookup: agentId → live status
  const statusMap: Record<string, string> = {};
  liveAgents.forEach(agent => {
    const id = NAME_TO_ID[agent.name] || agent.id;
    statusMap[id] = agent.status;
  });

  // Signal animation — fires on active (working/thinking) agents
  // Falls back to random simulation when disconnected
  useEffect(() => {
    const interval = setInterval(() => {
      let eligibleConnections = CONNECTIONS;

      // If live data: only pulse connections involving active agents
      if (connected && liveAgents.length > 0) {
        const activeIds = liveAgents
          .filter(a => a.status === 'working' || a.status === 'thinking')
          .map(a => NAME_TO_ID[a.name] || a.id);

        const liveConnections = CONNECTIONS.filter(
          ([from, to]) => activeIds.includes(from) || activeIds.includes(to)
        );
        if (liveConnections.length > 0) eligibleConnections = liveConnections;
      }

      const randomConnection = eligibleConnections[Math.floor(Math.random() * eligibleConnections.length)];
      const signalId = Math.random().toString(36).substring(7);

      setActiveSignals(prev => [...prev, { id: signalId, from: randomConnection[0], to: randomConnection[1] }]);

      setTimeout(() => {
        setActiveSignals(prev => prev.filter(s => s.id !== signalId));
      }, 2000);
    }, connected ? 800 : 1500); // faster pulses when live

    return () => clearInterval(interval);
  }, [connected, liveAgents]);

  return (
    <div className="relative w-full h-full bg-zinc-900/20 rounded-lg overflow-hidden border border-zinc-800">

      {/* Grid Background */}
      <div className="absolute inset-0 grid grid-cols-[repeat(20,minmax(0,1fr))] grid-rows-[repeat(20,minmax(0,1fr))] opacity-10 pointer-events-none">
        {Array.from({ length: 400 }).map((_, i) => (
          <div key={i} className="border-[0.5px] border-cyan-500/20" />
        ))}
      </div>

      {/* Connection Lines + Signal Pulses */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {CONNECTIONS.map(([startId, endId], i) => {
          const start = AGENT_POSITIONS[startId];
          const end   = AGENT_POSITIONS[endId];
          if (!start || !end) return null;

          // Highlight connection if both ends are active
          const bothActive =
            (statusMap[startId] === 'working' || statusMap[startId] === 'thinking') &&
            (statusMap[endId]   === 'working' || statusMap[endId]   === 'thinking');

          return (
            <g key={i}>
              <line
                x1={`${start.x}%`} y1={`${start.y}%`}
                x2={`${end.x}%`}   y2={`${end.y}%`}
                stroke={bothActive ? '#22d3ee' : '#3f3f46'}
                strokeWidth={bothActive ? '2' : '1.5'}
                opacity={bothActive ? 0.8 : 0.4}
              />
              {activeSignals
                .filter(s => s.from === startId && s.to === endId)
                .map(signal => (
                  <motion.circle
                    key={signal.id}
                    r="4"
                    fill={bothActive ? '#a78bfa' : '#06b6d4'}
                    initial={{ cx: `${start.x}%`, cy: `${start.y}%` }}
                    animate={{ cx: `${end.x}%`,   cy: `${end.y}%` }}
                    transition={{ duration: 1.5, ease: 'linear' }}
                  />
                ))}
            </g>
          );
        })}
      </svg>

      {/* Agent Nodes */}
      {Object.entries(AGENT_POSITIONS).map(([agentId, pos]) => {
        const name   = Object.keys(NAME_TO_ID).find(n => NAME_TO_ID[n] === agentId) || agentId;
        const Icon   = AGENT_ICONS[name] || Activity;
        const status = statusMap[agentId] || 'idle';
        const ring   = STATUS_COLOURS[status] || STATUS_COLOURS.idle;
        const dot    = STATUS_DOT[status]     || STATUS_DOT.idle;

        return (
          <div
            key={agentId}
            className="absolute -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2"
            style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              whileHover={{ scale: 1.15 }}
              className={`relative w-12 h-12 rounded-full bg-zinc-900 border-2 flex items-center justify-center z-10 transition-all duration-500 ${ring}`}
            >
              <Icon className="w-6 h-6 text-cyan-400" />
              {/* Status dot */}
              <span className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border border-zinc-900 ${dot}`} />
            </motion.div>
            <span className="text-[10px] font-mono text-zinc-400 bg-black/50 px-2 py-0.5 rounded backdrop-blur-sm whitespace-nowrap">
              {name}
            </span>
            {/* Status label on hover area */}
            {status !== 'idle' && (
              <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase tracking-wider
                ${ status === 'working'  ? 'text-green-400  bg-green-400/10'  :
                   status === 'thinking' ? 'text-yellow-400 bg-yellow-400/10' :
                   status === 'error'    ? 'text-red-400    bg-red-400/10'    : '' }`}>
                {status}
              </span>
            )}
          </div>
        );
      })}

      {/* Connection Status Badge */}
      <div className="absolute bottom-4 right-4 flex items-center gap-2 text-xs font-mono">
        {connected ? (
          <>
            <Wifi className="w-4 h-4 text-green-400" />
            <span className="text-green-400">LIVE — {liveAgents.length} AGENTS</span>
          </>
        ) : error ? (
          <>
            <WifiOff className="w-4 h-4 text-red-400" />
            <span className="text-red-400">DISCONNECTED — RECONNECTING...</span>
          </>
        ) : (
          <>
            <Activity className="w-4 h-4 text-cyan-500 animate-pulse" />
            <span className="text-cyan-500">NEURAL LINK CONNECTING...</span>
          </>
        )}
      </div>

      {/* Top-left: agent working count */}
      {connected && liveAgents.length > 0 && (
        <div className="absolute top-3 left-3 flex gap-2 text-[10px] font-mono">
          <span className="text-green-400 bg-green-400/10 px-2 py-0.5 rounded">
            {liveAgents.filter(a => a.status === 'working').length} WORKING
          </span>
          <span className="text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded">
            {liveAgents.filter(a => a.status === 'thinking').length} THINKING
          </span>
          {liveAgents.filter(a => a.status === 'error').length > 0 && (
            <span className="text-red-400 bg-red-400/10 px-2 py-0.5 rounded">
              {liveAgents.filter(a => a.status === 'error').length} ERROR
            </span>
          )}
        </div>
      )}
    </div>
  );
}
