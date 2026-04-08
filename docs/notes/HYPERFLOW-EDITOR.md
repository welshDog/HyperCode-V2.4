YOOOO BRO!!! 🔥 I've got the full BDS design system in my hands now — `Deep Void`, `Hyper Cyan`, `Matrix Green`, `Cyberpunk Dopamine` aesthetic, Orbitron fonts, Bento Grid, Holo-Cards — ALL of it. 

Now let me go **FULL 2026** on this. Strap in. 🪄🤖💫

***

# 🌌 **HYPERFLOW-EDITOR: FULL COMPONENT ARCHITECTURE**
### *The Visual Brain of HyperCode V2.0 — 2026 Edition*

***

## 🎯 **The Big Idea**

HyperFlow-Editor is not just a node editor. It's a **living, breathing, real-time cognitive workspace** where you SEE your AI agents thinking, connecting, remembering, and evolving — all draped in the BDS Cyberpunk Dopamine aesthetic. Built ND-first: spatial, chunked, zero cognitive overload.

> *"You don't write code here. You orchestrate minds."*

***

## 🗂️ **File Structure**

```
HyperFlow-Editor/
│
├── 📁 src/
│   ├── 📁 components/
│   │   ├── 📁 canvas/
│   │   │   ├── HyperCanvas.tsx          ← Main visual workspace
│   │   │   ├── CanvasBackground.tsx     ← Animated grid + stars
│   │   │   ├── MiniMap.tsx              ← ND spatial overview
│   │   │   └── SelectionBox.tsx         ← Multi-select agents
│   │   │
│   │   ├── 📁 nodes/
│   │   │   ├── AgentNode.tsx            ← 🤖 Core agent card
│   │   │   ├── GoalNode.tsx             ← 🎯 Mission/objective node
│   │   │   ├── ToolNode.tsx             ← 🔧 Tool/function node
│   │   │   ├── MemoryNode.tsx           ← 🧠 Memory store node
│   │   │   ├── QuantumNode.tsx          ← ⚛️ Quantum circuit node
│   │   │   ├── TriggerNode.tsx          ← ⚡ Event trigger node
│   │   │   └── OutputNode.tsx           ← 📤 Result output node
│   │   │
│   │   ├── 📁 edges/
│   │   │   ├── HyperEdge.tsx            ← Animated flow connection
│   │   │   ├── DataEdge.tsx             ← Data stream (pulsing)
│   │   │   └── MemoryEdge.tsx           ← Memory link (dotted glow)
│   │   │
│   │   ├── 📁 panels/
│   │   │   ├── AgentLibrary.tsx         ← Left: drag-from agent shelf
│   │   │   ├── PropertiesPanel.tsx      ← Right: selected node config
│   │   │   ├── MissionConsole.tsx       ← Bottom: live logs/trace
│   │   │   └── ContextMenu.tsx          ← Right-click popup
│   │   │
│   │   ├── 📁 toolbar/
│   │   │   ├── HyperToolbar.tsx         ← Top control bar
│   │   │   ├── RunControls.tsx          ← Play/Pause/Stop
│   │   │   ├── ExportMenu.tsx           ← Export .hc / JSON / Python
│   │   │   └── ViewControls.tsx         ← Zoom, fit, minimap toggle
│   │   │
│   │   ├── 📁 hud/
│   │   │   ├── StatusOrb.tsx            ← Live system health orb
│   │   │   ├── AgentHealthBar.tsx       ← Per-agent status
│   │   │   ├── TokenCounter.tsx         ← LLM token usage
│   │   │   ├── BROskiCoins.tsx          ← 🪙 Gamification display
│   │   │   └── EvolveAlert.tsx          ← Evolutionary pipeline alert
│   │   │
│   │   └── 📁 shared/
│   │       ├── HoloCard.tsx             ← BDS glass card
│   │       ├── NeonBadge.tsx            ← BDS status badge
│   │       ├── GlowButton.tsx           ← BDS button
│   │       ├── PulseRing.tsx            ← Animated status ring
│   │       └── CyberTooltip.tsx         ← Hover info tooltip
│   │
│   ├── 📁 store/
│   │   ├── flowStore.ts                 ← Zustand: nodes + edges state
│   │   ├── agentStore.ts                ← Zustand: agent fleet state
│   │   ├── missionStore.ts              ← Zustand: active missions
│   │   └── uiStore.ts                   ← Zustand: panels, zoom, prefs
│   │
│   ├── 📁 hooks/
│   │   ├── useFlowSync.ts               ← Sync canvas → backend API
│   │   ├── useAgentStream.ts            ← SSE: live agent events
│   │   ├── useHyperCode.ts              ← Generate .hc from graph
│   │   ├── useKeyboardShortcuts.ts      ← ND power-user shortcuts
│   │   └── useAutoSave.ts               ← Auto-save every 30s
│   │
│   ├── 📁 styles/
│   │   ├── bds-core.css                 ← BDS design tokens (imported)
│   │   ├── canvas.css                   ← Canvas-specific styles
│   │   ├── nodes.css                    ← Node animations
│   │   └── edges.css                    ← Edge pulse animations
│   │
│   ├── 📁 utils/
│   │   ├── graphToHyperCode.ts          ← Canvas → .hc syntax
│   │   ├── hyperCodeToGraph.ts          ← .hc syntax → Canvas
│   │   ├── layoutEngine.ts              ← Auto-arrange nodes (Dagre)
│   │   └── agentColor.ts                ← Role → BDS colour mapping
│   │
│   ├── App.tsx                          ← Root component
│   └── main.tsx                         ← Entry point
│
├── 📁 public/
│   ├── hyperflow-icon.svg               ← HyperFocus branding
│   └── agent-sprites/                   ← Agent avatar icons
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

***

## 🧩 **Component Deep-Dives**

***

### 1. 🌌 `HyperCanvas.tsx` — The Main Workspace

The entire visual brain. Built on **ReactFlow** with full BDS theming.

```tsx
// HyperCanvas.tsx
import ReactFlow, {
  Background, Controls, MiniMap,
  BackgroundVariant
} from 'reactflow';
import { useFlowStore } from '../store/flowStore';
import { AgentNode, GoalNode, ToolNode, 
         MemoryNode, QuantumNode } from './nodes';
import { HyperEdge, DataEdge } from './edges';
import { CanvasBackground } from './CanvasBackground';

const nodeTypes = {
  agent:    AgentNode,
  goal:     GoalNode,
  tool:     ToolNode,
  memory:   MemoryNode,
  quantum:  QuantumNode,
  trigger:  TriggerNode,
  output:   OutputNode,
};

const edgeTypes = {
  hyper:  HyperEdge,
  data:   DataEdge,
  memory: MemoryEdge,
};

export const HyperCanvas = () => {
  const { nodes, edges, onNodesChange, 
          onEdgesChange, onConnect } = useFlowStore();

  return (
    <div style={{
      width: '100%',
      height: '100vh',
      background: 'var(--deep-void)',
      position: 'relative'
    }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        snapToGrid
        snapGrid={[16, 16]}
      >
        {/* Animated star-field + grid background */}
        <CanvasBackground />

        {/* BDS-styled minimap */}
        <MiniMap
          style={{
            background: 'rgba(11, 4, 24, 0.9)',
            border: '1px solid rgba(0, 243, 255, 0.3)',
            borderRadius: '8px',
          }}
          nodeColor={(node) => agentColor(node.data.role)}
          maskColor="rgba(11, 4, 24, 0.7)"
        />

        {/* Zoom + fit controls */}
        <Controls
          style={{
            background: 'rgba(11, 4, 24, 0.8)',
            border: '1px solid rgba(0, 243, 255, 0.2)',
          }}
        />
      </ReactFlow>
    </div>
  );
};
```

***

### 2. 🤖 `AgentNode.tsx` — The Hero Component

This is the star of the show. Every agent in your fleet renders as a **Holo-Card** with live status, role badge, health ring, and tool list.

```tsx
// AgentNode.tsx
import { Handle, Position, NodeProps } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';

interface AgentData {
  name:     string;
  role:     'frontend' | 'backend' | 'qa' | 'devops' | 
            'security' | 'architect' | 'strategist' | 'healer';
  status:   'idle' | 'thinking' | 'running' | 'done' | 'error';
  tools:    string[];
  memory:   'short_term' | 'long_term' | 'both';
  avatar:   string;        // emoji or URL
  health:   number;        // 0-100
  taskDesc: string;        // what it's doing right now
}

// Role → BDS colour map
const ROLE_COLORS = {
  frontend:   'var(--hyper-cyan)',
  backend:    'var(--matrix-green)',
  qa:         'var(--ember-orange)',
  devops:     'var(--plasma-purple)',
  security:   '#FF3366',       // Danger red
  architect:  '#FFD700',       // Gold
  strategist: 'var(--hyper-cyan)',
  healer:     'var(--matrix-green)',
};

// Status → pulse animation speed
const STATUS_PULSE = {
  idle:     { duration: 3,   opacity: [0.4, 0.8] },
  thinking: { duration: 1,   opacity: [0.3, 1.0] },
  running:  { duration: 0.5, opacity: [0.5, 1.0] },
  done:     { duration: 5,   opacity: [0.7, 0.9] },
  error:    { duration: 0.3, opacity: [0.2, 1.0] },
};

export const AgentNode = ({ data, selected }: NodeProps<AgentData>) => {
  const color     = ROLE_COLORS[data.role];
  const pulse     = STATUS_PULSE[data.status];
  const isActive  = data.status === 'thinking' || data.status === 'running';

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1,   opacity: 1 }}
      whileHover={{ scale: 1.03, y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      style={{
        // Holo-Card BDS styling
        background:      'rgba(11, 4, 24, 0.85)',
        backdropFilter:  'blur(16px)',
        border:          `1.5px solid ${selected 
                           ? color 
                           : 'rgba(0, 243, 255, 0.2)'}`,
        borderRadius:    '16px',
        padding:         '16px',
        minWidth:        '200px',
        maxWidth:        '240px',
        boxShadow:       selected 
                           ? `0 0 24px ${color}66` 
                           : '0 4px 24px rgba(0,0,0,0.4)',
        cursor:          'grab',
        position:        'relative',
        overflow:        'hidden',
      }}
    >
      {/* ⬆️ Top: animated glow stripe when active */}
      {isActive && (
        <motion.div
          animate={{ opacity: pulse.opacity as any }}
          transition={{ duration: pulse.duration, repeat: Infinity, 
                        repeatType: 'reverse' }}
          style={{
            position:   'absolute',
            top:        0, left: 0, right: 0,
            height:     '2px',
            background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
          }}
        />
      )}

      {/* 🔗 ReactFlow connection handles */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: color, border: 'none', width: 10, height: 10 }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: color, border: 'none', width: 10, height: 10 }}
      />

      {/* 👤 Agent header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, 
                    marginBottom: 12 }}>
        
        {/* Avatar with health ring */}
        <div style={{ position: 'relative' }}>
          <svg width="40" height="40" style={{ position: 'absolute', 
                                               top: -2, left: -2 }}>
            <circle cx="22" cy="22" r="20"
              fill="none"
              stroke={color}
              strokeWidth="2"
              strokeDasharray={`${data.health * 1.26} 126`}
              transform="rotate(-90 22 22)"
              opacity="0.8"
            />
          </svg>
          <div style={{
            width:        36, height: 36,
            borderRadius: '50%',
            background:   `${color}22`,
            display:      'flex',
            alignItems:   'center',
            justifyContent: 'center',
            fontSize:     '18px',
            border:       `1px solid ${color}44`,
          }}>
            {data.avatar}
          </div>
        </div>

        {/* Name + role badge */}
        <div>
          <div style={{
            fontFamily:  'var(--font-heading)',
            fontSize:    '11px',
            color:       'var(--ghost-white)',
            fontWeight:  700,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
          }}>
            {data.name}
          </div>
          <div style={{
            fontSize:     '9px',
            color:        color,
            fontFamily:   'var(--font-code)',
            background:   `${color}18`,
            padding:      '2px 6px',
            borderRadius: '4px',
            border:       `1px solid ${color}33`,
            marginTop:    '3px',
            display:      'inline-block',
          }}>
            {data.role.toUpperCase()}
          </div>
        </div>

        {/* Status dot */}
        <motion.div
          animate={pulse}
          transition={{ duration: pulse.duration, repeat: Infinity,
                        repeatType: 'reverse' }}
          style={{
            marginLeft:   'auto',
            width:        8, height: 8,
            borderRadius: '50%',
            background:   data.status === 'error' 
                            ? '#FF3366' 
                            : data.status === 'done' 
                              ? 'var(--matrix-green)' 
                              : color,
            boxShadow:    `0 0 8px ${color}`,
          }}
        />
      </div>

      {/* 📋 Current task (truncated) */}
      {data.taskDesc && (
        <div style={{
          fontSize:     '10px',
          color:        'rgba(245, 247, 250, 0.6)',
          fontFamily:   'var(--font-code)',
          background:   'rgba(0,0,0,0.3)',
          padding:      '6px 8px',
          borderRadius: '6px',
          marginBottom: '10px',
          borderLeft:   `2px solid ${color}`,
          maxHeight:    '36px',
          overflow:     'hidden',
          lineHeight:   1.4,
        }}>
          {data.taskDesc}
        </div>
      )}

      {/* 🔧 Tools (chips) */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {data.tools.slice(0, 3).map(tool => (
          <span key={tool} style={{
            fontSize:     '8px',
            color:        'rgba(245,247,250,0.7)',
            background:   'rgba(0, 243, 255, 0.08)',
            border:       '1px solid rgba(0, 243, 255, 0.15)',
            padding:      '2px 5px',
            borderRadius: '3px',
            fontFamily:   'var(--font-code)',
          }}>
            {tool}
          </span>
        ))}
        {data.tools.length > 3 && (
          <span style={{ fontSize: '8px', color: color }}>
            +{data.tools.length - 3}
          </span>
        )}
      </div>
    </motion.div>
  );
};
```

***

### 3. ✨ `HyperEdge.tsx` — Animated Data Flows

Edges that **pulse particles** in the direction of data flow. 

```tsx
// HyperEdge.tsx — animated particle edge
import { BaseEdge, EdgeProps, getBezierPath } from 'reactflow';
import { useEffect, useRef } from 'react';

export const HyperEdge = ({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition,
  data
}: EdgeProps) => {

  const [edgePath] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const isActive = data?.active;
  const color    = data?.color || 'var(--hyper-cyan)';

  return (
    <>
      {/* Base edge line */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke:      isActive ? color : 'rgba(0, 243, 255, 0.2)',
          strokeWidth: isActive ? 2 : 1,
          filter:      isActive ? `drop-shadow(0 0 4px ${color})` : 'none',
        }}
      />

      {/* Moving particle along the path when active */}
      {isActive && (
        <circle r="4" fill={color}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}>
          <animateMotion
            dur="1.5s"
            repeatCount="indefinite"
            path={edgePath}
          />
        </circle>
      )}
    </>
  );
};
```

***

### 4. 📚 `AgentLibrary.tsx` — Drag-From Shelf

Left panel with all 13+ agents from your fleet — draggable onto the canvas.

```tsx
// AgentLibrary.tsx
const AGENT_TEMPLATES = [
  { role: 'frontend',   avatar: '🎨', name: 'Frontend Ace',
    tools: ['react', 'css', 'nextjs'],        color: 'var(--hyper-cyan)' },
  { role: 'backend',    avatar: '⚙️', name: 'Backend Beast',
    tools: ['fastapi', 'postgres', 'redis'],  color: 'var(--matrix-green)' },
  { role: 'qa',         avatar: '🧪', name: 'QA Ninja',
    tools: ['pytest', 'playwright'],          color: 'var(--ember-orange)' },
  { role: 'devops',     avatar: '🚀', name: 'DevOps Wizard',
    tools: ['docker', 'k8s', 'ci-cd'],        color: 'var(--plasma-purple)' },
  { role: 'security',   avatar: '🛡️', name: 'Security Guard',
    tools: ['audit', 'scan', 'shield'],       color: '#FF3366' },
  { role: 'architect',  avatar: '🏗️', name: 'Sys Architect',
    tools: ['design', 'review', 'plan'],      color: '#FFD700' },
  { role: 'strategist', avatar: '🎯', name: 'Project Boss',
    tools: ['roadmap', 'prioritize'],         color: 'var(--hyper-cyan)' },
  { role: 'healer',     avatar: '❤️', name: 'Healer Agent',
    tools: ['monitor', 'recover', 'restart'], color: 'var(--matrix-green)' },
  { role: 'coder',      avatar: '💻', name: 'Code Forge',
    tools: ['write', 'refactor', 'debug'],    color: 'var(--hyper-cyan)' },
  { role: 'memory',     avatar: '🧠', name: 'Memory Keeper',
    tools: ['store', 'recall', 'vectorize'],  color: 'var(--plasma-purple)' },
  { role: 'quantum',    avatar: '⚛️', name: 'Quantum Brain',
    tools: ['qiskit', 'pennylane', 'optimize'], color: '#00F0FF' },
];

export const AgentLibrary = () => {
  const onDragStart = (e: React.DragEvent, agent: typeof AGENT_TEMPLATES[0]) => {
    e.dataTransfer.setData('application/hyperflow', JSON.stringify(agent));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div style={{
      width:        '220px',
      height:       '100vh',
      background:   'rgba(11, 4, 24, 0.95)',
      borderRight:  '1px solid rgba(0, 243, 255, 0.15)',
      backdropFilter: 'blur(20px)',
      overflowY:    'auto',
      padding:      '16px 12px',
      display:      'flex',
      flexDirection:'column',
      gap:          '8px',
    }}>
      {/* Header */}
      <div style={{
        fontFamily:   'var(--font-heading)',
        fontSize:     '11px',
        color:        'var(--hyper-cyan)',
        letterSpacing:'0.15em',
        textTransform:'uppercase',
        marginBottom: '8px',
        paddingBottom:'8px',
        borderBottom: '1px solid rgba(0,243,255,0.15)',
      }}>
        🤖 Agent Fleet
      </div>

      {/* Agent cards — draggable */}
      {AGENT_TEMPLATES.map(agent => (
        <motion.div
          key={agent.role}
          draggable
          onDragStart={(e) => onDragStart(e, agent)}
          whileHover={{ x: 4, scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          style={{
            background:    `${agent.color}10`,
            border:        `1px solid ${agent.color}30`,
            borderRadius:  '10px',
            padding:       '10px 12px',
            cursor:        'grab',
            display:       'flex',
            alignItems:    'center',
            gap:           '10px',
          }}
        >
          <span style={{ fontSize: '20px' }}>{agent.avatar}</span>
          <div>
            <div style={{
              fontSize:   '11px',
              fontWeight: 600,
              color:      'var(--ghost-white)',
              fontFamily: 'var(--font-heading)',
            }}>
              {agent.name}
            </div>
            <div style={{ fontSize: '9px', color: agent.color }}>
              {agent.tools.join(' · ')}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
};
```

***

### 5. 🖥️ `MissionConsole.tsx` — Live Logs Panel

Bottom panel — streams live agent activity like a terminal but beautiful. 

```tsx
// MissionConsole.tsx
export const MissionConsole = () => {
  const logs = useMissionStore(s => s.logs);  // SSE stream from backend

  // Log levels → BDS colours
  const LOG_COLORS = {
    info:    'var(--hyper-cyan)',
    success: 'var(--matrix-green)',
    warning: 'var(--ember-orange)',
    error:   '#FF3366',
    think:   'var(--plasma-purple)',
    system:  'rgba(245,247,250,0.4)',
  };

  return (
    <div style={{
      height:        '180px',
      background:    'rgba(7, 2, 16, 0.97)',
      borderTop:     '1px solid rgba(0,243,255,0.15)',
      padding:       '12px 16px',
      overflowY:     'auto',
      fontFamily:    'var(--font-code)',
      fontSize:      '11px',
      display:       'flex',
      flexDirection: 'column',
      gap:           '4px',
    }}>
      {/* Console header */}
      <div style={{
        color:       'rgba(0,243,255,0.5)',
        marginBottom:'8px',
        fontFamily:  'var(--font-heading)',
        fontSize:    '9px',
        letterSpacing:'0.15em',
        textTransform:'uppercase',
        display:     'flex',
        alignItems:  'center',
        gap:         '8px',
      }}>
        <motion.div
          animate={{ opacity: [1, 0.3] }}
          transition={{ duration: 1, repeat: Infinity, repeatType: 'reverse' }}
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--matrix-green)',
          }}
        />
        Mission Console — Live
      </div>

      {/* Log lines */}
      <AnimatePresence initial={false}>
        {logs.map((log, i) => (
          <motion.div
            key={log.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}
          >
            {/* Timestamp */}
            <span style={{ color: 'rgba(245,247,250,0.25)', 
                           minWidth: '60px', fontSize: '10px' }}>
              {log.time}
            </span>
            {/* Agent name */}
            <span style={{
              color:     LOG_COLORS[log.level] || LOG_COLORS.info,
              minWidth:  '80px',
              fontWeight:600,
            }}>
              [{log.agent}]
            </span>
            {/* Message */}
            <span style={{ color: 'rgba(245,247,250,0.75)' }}>
              {log.message}
            </span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
```

***

### 6. 🧰 `HyperToolbar.tsx` — Mission Control Bar

Top bar with run controls, export, and the BROski$ coin display.

```tsx
// HyperToolbar.tsx
export const HyperToolbar = () => {
  const { isRunning, run, pause, stop } = useMissionStore();
  const coins = useBROskiStore(s => s.coins);

  return (
    <div style={{
      height:      '52px',
      background:  'rgba(11, 4, 24, 0.97)',
      borderBottom:'1px solid rgba(0,243,255,0.12)',
      backdropFilter: 'blur(20px)',
      display:     'flex',
      alignItems:  'center',
      padding:     '0 16px',
      gap:         '12px',
      position:    'relative',
      zIndex:      100,
    }}>

      {/* HyperFocus Logo */}
      <div style={{
        fontFamily:   'var(--font-heading)',
        fontSize:     '14px',
        fontWeight:   900,
        background:   'linear-gradient(90deg, var(--hyper-cyan), var(--plasma-purple))',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        letterSpacing:'0.1em',
        marginRight:  '16px',
      }}>
        ⚡ HYPERFLOW
      </div>

      {/* Divider */}
      <div style={{ width:1, height:28, 
                    background:'rgba(0,243,255,0.15)' }} />

      {/* ▶️ Run Controls */}
      <GlowButton
        color="var(--matrix-green)"
        onClick={run}
        disabled={isRunning}
        icon="▶"
        label="RUN"
      />
      <GlowButton
        color="var(--ember-orange)"
        onClick={pause}
        disabled={!isRunning}
        icon="⏸"
        label="PAUSE"
      />
      <GlowButton
        color="#FF3366"
        onClick={stop}
        disabled={!isRunning}
        icon="⏹"
        label="STOP"
      />

      {/* Divider */}
      <div style={{ width:1, height:28, 
                    background:'rgba(0,243,255,0.15)' }} />

      {/* 📤 Export */}
      <ExportMenu />

      {/* Auto-arrange */}
      <GlowButton
        color="var(--plasma-purple)"
        onClick={autoLayout}
        icon="⬡"
        label="ARRANGE"
      />

      {/* SPACER */}
      <div style={{ flex: 1 }} />

      {/* 🪙 BROski$ Coins */}
      <motion.div
        whileHover={{ scale: 1.05 }}
        style={{
          display:     'flex',
          alignItems:  'center',
          gap:         '6px',
          background:  'rgba(255, 215, 0, 0.1)',
          border:      '1px solid rgba(255,215,0,0.3)',
          borderRadius:'20px',
          padding:     '4px 12px',
          cursor:      'pointer',
        }}
      >
        <span>🪙</span>
        <span style={{
          fontFamily:   'var(--font-heading)',
          fontSize:     '12px',
          color:        '#FFD700',
          fontWeight:   700,
        }}>
          {coins.toLocaleString()}
        </span>
      </motion.div>

      {/* ❤️ System Health Orb */}
      <StatusOrb />

      {/* ♿ Accessibility toggle */}
      <button
        onClick={toggleDyslexiaMode}
        title="Toggle Dyslexia-Friendly Mode"
        style={{
          background:   'transparent',
          border:       '1px solid rgba(0,243,255,0.2)',
          borderRadius: '6px',
          color:        'rgba(0,243,255,0.6)',
          padding:      '4px 8px',
          cursor:       'pointer',
          fontSize:     '11px',
          fontFamily:   'var(--font-code)',
        }}
      >
        Aa
      </button>
    </div>
  );
};
```

***

### 7. 🌐 `useAgentStream.ts` — Live Backend Connection

Connects the canvas to your existing **FastAPI backend** via Server-Sent Events (SSE). 

```typescript
// useAgentStream.ts
import { useEffect } from 'react';
import { useFlowStore } from '../store/flowStore';
import { useMissionStore } from '../store/missionStore';

export const useAgentStream = () => {
  const updateNodeStatus = useFlowStore(s => s.updateNodeStatus);
  const addLog           = useMissionStore(s => s.addLog);

  useEffect(() => {
    // Connect to existing HyperCode backend SSE stream
    const eventSource = new EventSource(
      'http://localhost:8000/api/v1/agents/stream'
    );

    // Agent status update → update canvas node live
    eventSource.addEventListener('agent_update', (e) => {
      const data = JSON.parse(e.data);
      updateNodeStatus(data.agent_id, {
        status:   data.status,
        taskDesc: data.current_task,
        health:   data.health,
      });
    });

    // New log entry → Mission Console
    eventSource.addEventListener('log', (e) => {
      const data = JSON.parse(e.data);
      addLog({
        id:      crypto.randomUUID(),
        time:    new Date().toLocaleTimeString(),
        agent:   data.agent_name,
        level:   data.level,
        message: data.message,
      });
    });

    // Evolutionary pipeline trigger → show EvolveAlert
    eventSource.addEventListener('evolve', (e) => {
      const data = JSON.parse(e.data);
      showEvolveAlert(data);  // 🧬 agent is upgrading itself!
    });

    return () => eventSource.close();
  }, []);
};
```

***

### 8. 📄 `graphToHyperCode.ts` — Canvas → Language

Converts what's on the visual canvas to actual `.hc` HyperCode syntax. 

```typescript
// graphToHyperCode.ts
import { Node, Edge } from 'reactflow';

export const graphToHyperCode = (
  nodes: Node[], 
  edges: Edge[]
): string => {
  
  let code = `// 🤖 HyperCode — Generated by HyperFlow-Editor\n`;
  code    += `// ⏱️ ${new Date().toISOString()}\n\n`;

  // 1. Generate agent blocks
  const agentNodes = nodes.filter(n => n.type === 'agent');
  agentNodes.forEach(node => {
    const d = node.data;
    code += `agent ${d.name.toLowerCase().replace(/\s/g, '_')} {\n`;
    code += `  role:   "${d.role}"\n`;
    code += `  avatar: "${d.avatar}"\n`;
    code += `  tools:  [${d.tools.map((t: string) => `"${t}"`).join(', ')}]\n`;
    code += `  memory: ${d.memory}\n`;
    code += `  safety: { sandbox: docker, requires_review: false }\n`;
    code += `}\n\n`;
  });

  // 2. Generate goal blocks
  const goalNodes = nodes.filter(n => n.type === 'goal');
  goalNodes.forEach(node => {
    const d = node.data;
    code += `goal ${d.name.toLowerCase().replace(/\s/g, '_')} {\n`;
    code += `  success: "${d.successCondition}"\n`;
    code += `  vibe:    "${d.vibe || 'focused and efficient'}"\n`;
    code += `}\n\n`;
  });

  // 3. Generate flow block from edges
  code += `flow main_pipeline {\n`;
  // Topological sort edges into readable chain
  const chain = buildFlowChain(nodes, edges);
  chain.forEach(step => {
    code += `  ${step.from} → ${step.action}(${step.args});\n`;
  });
  code += `}\n`;

  return code;
};
```

***

## 🎨 **The Full Layout — What You Actually See**

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ HYPERFLOW    ▶ RUN  ⏸ PAUSE  ⏹ STOP  | ⬡ ARRANGE  📤 EXPORT  │
│                                                    🪙 4,250  ● ❤️ │
├──────────┬──────────────────────────────────────┬───────────────┤
│          │                                      │               │
│ 🤖 AGENT │      ∷ ∷ ∷  HYPER CANVAS  ∷ ∷ ∷     │  ⚙️ PROPERTIES│
│  FLEET   │                                      │               │
│          │    [🎨 Frontend]──●──[⚙️ Backend]    │  Selected:    │
│ Frontend │         │              │             │  AgentNode    │
│ Backend  │    [🎯 Goal]      [🧪 QA Agent]      │               │
│ QA       │         │              │             │  Name: ...    │
│ DevOps   │    [🔧 Tool]──●──[🚀 DevOps]         │  Role: ...    │
│ Security │                   │                  │  Tools: ...   │
│ Arch...  │              [📤 Output]             │  Memory: ...  │
│ Healer   │                                      │  Status: ...  │
│ Coder    │                               [MAP]  │               │
│ Memory   │                                      │               │
│ Quantum  │                                      │               │
│ + more   │                                      │               │
├──────────┴──────────────────────────────────────┴───────────────┤
│ MISSION CONSOLE ● Live                                           │
│ 12:04:31 [frontend_ace]  Analyzing component structure...        │
│ 12:04:32 [backend_beast] API endpoint created: /api/v1/flow      │
│ 12:04:33 [qa_ninja]      Running test suite... 47/50 passed ✅   │
│ 12:04:34 [HEALER]        All systems nominal. BROski vibes! ❤️   │
└─────────────────────────────────────────────────────────────────┘
```

***

## 📦 **Tech Stack Summary**

| Layer | Choice | Why |
|-------|--------|-----|
| **Framework** | React + TypeScript | Already in your Next.js stack |
| **Canvas** | ReactFlow v11+ | Industry standard, extensible |
| **Animation** | Framer Motion | Smooth + ND-friendly transitions |
| **State** | Zustand | Lightweight, no boilerplate |
| **Backend Sync** | SSE + Fetch | Connects to your existing FastAPI |
| **Layout Engine** | Dagre.js | Auto-arrange nodes cleanly |
| **Build** | Vite | Blazing fast dev server |
| **Design** | BDS (BROski Design System) | Your own system — Cyberpunk Dopamine ✅ |

***

## ⚡ **NEXT STEP: Ship It**

Everything above wires directly into your existing:
- ✅ FastAPI backend on `:8000` (SSE stream endpoint needed)
- ✅ 13+ agents already defined in `/agents/`
- ✅ BDS design tokens already in [`THE VISUAL SOUL OF HYPERCODE.md`](https://github.com/welshDog/HyperCode-V2.0/blob/main/THE%20VISUAL%20SOUL%20OF%20HYPERCODE.md) 
- ✅ Mission Control dashboard already exists on `:8088`

**Want me to generate the full working starter files right now?** I can write:

- **A:** `HyperCanvas.tsx` + `AgentNode.tsx` + `HyperEdge.tsx` (the core 3)
- **B:** `flowStore.ts` + `useAgentStream.ts` (the state + backend sync)
- **C:** `package.json` + `vite.config.ts` (zero-to-running in 5 mins)

Pick your lane and we BUILD! 🚀👊💓🪄
