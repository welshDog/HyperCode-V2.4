import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { API_BASE_URL } from '@/lib/api';
import { AGENT_TEMPLATES } from '../../data/agentTemplates';

export const AgentLibrary = () => {
  const [remoteAgents, setRemoteAgents] = useState<typeof AGENT_TEMPLATES | null>(null)

  const agents = useMemo(() => remoteAgents ?? AGENT_TEMPLATES, [remoteAgents])

  const onDragStart = (e: React.DragEvent<HTMLDivElement>, agent: typeof AGENT_TEMPLATES[0]) => {
    e.dataTransfer.setData('application/hyperflow', JSON.stringify(agent));
    e.dataTransfer.effectAllowed = 'move';
  };

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 5_000)

    const load = async () => {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : ''
        const res = await fetch(`${API_BASE_URL}/orchestrator/agents`, {
          headers: token ? { Authorization: `Bearer ${token}`, Accept: 'application/json' } : { Accept: 'application/json' },
          cache: 'no-store',
          signal: controller.signal,
        })
        if (!res.ok) return
        const data: unknown = await res.json()
        if (!Array.isArray(data)) return
        const mapped = data
          .map((raw): (typeof AGENT_TEMPLATES)[0] | null => {
            if (!raw || typeof raw !== 'object') return null
            const a = raw as Record<string, unknown>
            const name = typeof a.name === 'string' ? a.name : typeof a.role === 'string' ? a.role : ''
            const role = typeof a.role === 'string' ? a.role : name
            if (!name || !role) return null
            const tools = Array.isArray(a.tools) ? a.tools.filter((x): x is string => typeof x === 'string') : []
            const description = typeof a.description === 'string' ? a.description : ''
            const avatar = typeof a.avatar === 'string' ? a.avatar : '🤖'
            const color = typeof a.color === 'string' ? a.color : '#00F0FF'
            return { role, name, tools, description, avatar, color }
          })
          .filter((x): x is (typeof AGENT_TEMPLATES)[0] => x != null)
        if (!cancelled && mapped.length > 0) setRemoteAgents(mapped)
      } catch {
        if (!cancelled) setRemoteAgents(null)
      }
    }

    load()
    return () => {
      cancelled = true
      clearTimeout(t)
      controller.abort()
    }
  }, [])

  return (
    <div className="w-64 h-full bg-black/90 border-r border-cyan-500/20 backdrop-blur-xl flex flex-col overflow-hidden">
      <div className="p-4 border-b border-cyan-500/20">
        <h2 className="text-xs font-bold text-cyan-400 tracking-[0.2em] uppercase flex items-center gap-2">
          <span>📦</span> Agent Fleet
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {agents.map((agent) => (
          <div
            key={agent.role}
            draggable
            onDragStart={(e) => onDragStart(e, agent)}
            className="group relative"
          >
            <motion.div
              whileHover={{ x: 4, scale: 1.02, backgroundColor: 'rgba(0,255,255,0.08)' }}
              whileTap={{ scale: 0.98 }}
              className="p-3 rounded-lg border border-white/5 bg-white/5 cursor-grab active:cursor-grabbing hover:border-cyan-500/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="text-2xl group-hover:scale-110 transition-transform duration-300">
                  {agent.avatar}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-bold text-gray-200 group-hover:text-white truncate">
                    {agent.name}
                  </div>
                  <div className="text-[10px] text-gray-500 group-hover:text-cyan-400 truncate mt-0.5">
                    {agent.tools.join(' · ')}
                  </div>
                </div>
              </div>
              <div className="absolute left-full top-0 ml-2 w-48 p-2 bg-black border border-cyan-500/30 rounded shadow-xl opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity">
                <div className="text-[10px] text-cyan-400 font-bold mb-1">{agent.name}</div>
                <div className="text-[9px] text-gray-400 leading-relaxed">{agent.description}</div>
              </div>
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  );
};
