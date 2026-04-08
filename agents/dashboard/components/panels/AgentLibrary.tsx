import React from 'react';
import { motion } from 'framer-motion';
import { AGENT_TEMPLATES } from '../../data/agentTemplates';

export const AgentLibrary = () => {
  const onDragStart = (e: React.DragEvent<HTMLDivElement>, agent: typeof AGENT_TEMPLATES[0]) => {
    e.dataTransfer.setData('application/hyperflow', JSON.stringify(agent));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="w-64 h-full bg-black/90 border-r border-cyan-500/20 backdrop-blur-xl flex flex-col overflow-hidden">
      <div className="p-4 border-b border-cyan-500/20">
        <h2 className="text-xs font-bold text-cyan-400 tracking-[0.2em] uppercase flex items-center gap-2">
          <span>📦</span> Agent Fleet
        </h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {AGENT_TEMPLATES.map((agent) => (
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
