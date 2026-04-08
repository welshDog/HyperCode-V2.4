import { Handle, Position, NodeProps } from 'reactflow';
import { motion } from 'framer-motion';

// Role → BDS colour map
const ROLE_COLORS: Record<string, string> = {
  frontend:   '#00F0FF', // Hyper Cyan
  backend:    '#00FF9D', // Matrix Green
  qa:         '#FF9F43', // Ember Orange
  devops:     '#9D00FF', // Plasma Purple
  security:   '#FF3366', // Danger Red
  architect:  '#FFD700', // Gold
  strategist: '#00F0FF',
  healer:     '#00FF9D',
};

export const AgentNode = ({ data, selected }: NodeProps) => {
  const color = ROLE_COLORS[data.role] || '#00F0FF';
  const isActive = data.status === 'working' || data.status === 'thinking';

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ 
        scale: 1, 
        opacity: 1,
        borderColor: isActive ? `${color}80` : `rgba(0, 243, 255, 0.2)`,
        boxShadow: isActive && selected 
          ? `0 0 30px ${color}40` 
          : selected 
            ? `0 0 20px ${color}66` 
            : '0 4px 12px rgba(0,0,0,0.5)'
      }}
      whileHover={{ scale: 1.05 }}
      style={{
        background: 'rgba(11, 4, 24, 0.9)',
        backdropFilter: 'blur(12px)',
        borderWidth: '1px',
        borderStyle: 'solid',
        borderRadius: '12px',
        padding: '12px',
        minWidth: '180px',
        color: '#fff',
        fontFamily: 'monospace'
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color }} />
      <Handle type="source" position={Position.Right} style={{ background: color }} />

      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <div className="relative w-10 h-10 flex items-center justify-center rounded-full bg-white/5 border border-white/10 text-xl">
          {data.avatar}
          {/* Health Ring */}
          <svg className="absolute inset-0 w-full h-full -rotate-90">
            <circle
              cx="20" cy="20" r="18"
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeDasharray={`${data.health * 1.13} 113`}
              opacity="0.8"
            />
          </svg>
        </div>
        
        <div>
          <div className="text-xs font-bold tracking-wider uppercase text-white">{data.name}</div>
          <div className="text-[10px] px-1.5 py-0.5 rounded border border-white/10 inline-block mt-1" style={{ color: color, background: `${color}15` }}>
            {data.role.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Status Dot - PULSING */}
      <motion.div 
        className="absolute top-3 right-3 w-2 h-2 rounded-full"
        animate={{
          backgroundColor: isActive ? color : '#555',
          boxShadow: isActive 
            ? [`0 0 0px ${color}`, `0 0 12px ${color}`, `0 0 0px ${color}`] 
            : 'none',
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />

      {/* Tools */}
      <div className="flex flex-wrap gap-1 mt-2">
        {data.tools.map((tool: string) => (
          <span key={tool} className="text-[9px] px-1 py-0.5 bg-white/5 rounded text-gray-400 border border-white/5">
            {tool}
          </span>
        ))}
      </div>
    </motion.div>
  );
};
