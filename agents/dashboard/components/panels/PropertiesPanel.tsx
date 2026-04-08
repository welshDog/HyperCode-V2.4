import React from 'react';
import { useFlowStore } from '../../store/flowStore';
import { Save, Trash2 } from 'lucide-react';

export const PropertiesPanel = () => {
  const { nodes, updateNodeStatus, deleteNode } = useFlowStore();
  
  // Find the first selected node (simplification for MVP)
  const selectedNode = nodes.find(n => n.selected);

  if (!selectedNode) {
    return (
      <div className="w-64 h-full bg-black/90 border-l border-cyan-500/20 backdrop-blur-xl p-6 flex flex-col items-center justify-center text-center">
        <div className="text-4xl mb-4 opacity-20">⚙️</div>
        <div className="text-xs text-gray-500 uppercase tracking-widest">
          Select an agent<br/>to configure
        </div>
      </div>
    );
  }

  const { data } = selectedNode;

  return (
    <div className="w-64 h-full bg-black/90 border-l border-cyan-500/20 backdrop-blur-xl flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-cyan-500/20 flex justify-between items-center">
        <h2 className="text-xs font-bold text-cyan-400 tracking-[0.2em] uppercase">
          Config
        </h2>
        <div className="text-[10px] text-gray-500 font-mono">
          ID: {selectedNode.id.slice(0, 4)}
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {/* Identity */}
        <div className="space-y-2">
          <label className="text-[10px] uppercase text-gray-500 font-bold">Identity</label>
          <div className="flex items-center gap-3 p-3 bg-white/5 rounded border border-white/10">
            <span className="text-2xl">{data.avatar}</span>
            <div>
              <div className="text-sm font-bold text-white">{data.name}</div>
              <div className="text-[10px] text-cyan-500">{data.role}</div>
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="space-y-2">
          <label className="text-[10px] uppercase text-gray-500 font-bold">Status Override</label>
          <select 
            className="w-full bg-black border border-white/20 rounded px-2 py-1.5 text-xs text-white focus:border-cyan-500 outline-none"
            value={data.status}
            onChange={(e) => updateNodeStatus(selectedNode.id, { status: e.target.value as 'idle' | 'working' | 'thinking' | 'coding' | 'error' })}
          >
            <option value="idle">Idle</option>
            <option value="thinking">Thinking</option>
            <option value="working">Working</option>
            <option value="error">Error</option>
          </select>
        </div>

        {/* Tools */}
        <div className="space-y-2">
          <label className="text-[10px] uppercase text-gray-500 font-bold">Active Tools</label>
          <div className="flex flex-wrap gap-2">
            {data.tools.map((tool: string) => (
              <span key={tool} className="text-[10px] px-2 py-1 bg-cyan-900/30 text-cyan-400 border border-cyan-500/30 rounded">
                {tool}
              </span>
            ))}
            <button className="text-[10px] px-2 py-1 bg-white/5 text-gray-400 border border-white/10 rounded hover:bg-white/10 hover:text-white transition-colors">
              + Add
            </button>
          </div>
        </div>

      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-cyan-500/20 grid grid-cols-2 gap-2">
        <button 
          onClick={() => deleteNode(selectedNode.id)}
          className="flex items-center justify-center gap-2 px-3 py-2 bg-red-900/20 text-red-500 border border-red-500/30 rounded hover:bg-red-900/40 transition-colors text-xs font-bold"
        >
          <Trash2 size={14} /> Kill
        </button>
        <button className="flex items-center justify-center gap-2 px-3 py-2 bg-cyan-900/20 text-cyan-500 border border-cyan-500/30 rounded hover:bg-cyan-900/40 transition-colors text-xs font-bold">
          <Save size={14} /> Save
        </button>
      </div>
    </div>
  );
};
