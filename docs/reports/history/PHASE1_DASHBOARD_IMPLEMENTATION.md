# Phase 1: Real-Time Mission Control Dashboard
## Implementation Guide

**Status:** Backend Complete ✅ | Frontend In Progress 🚧  
**Sprint Duration:** 3 Days  
**Priority:** High  
**Last Updated:** February 11, 2026

---

## 🎯 Overview

The Real-Time Mission Control Dashboard provides live visualization of the HyperCode agent swarm, showing:
- **Agent Status**: Live health, CPU/memory, current tasks
- **Mission Progress**: Active missions with real-time progress tracking
- **System Metrics**: Overall swarm performance and uptime

**Why This Feature First:**
1. Builds on stable infrastructure (Redis already configured)
2. Immediate visual impact (see agents working in real-time)
3. Critical debugging tool (track agent behavior live)
4. Foundation for future features (orchestration intelligence)

---

## ✅ Completed: Backend WebSocket Endpoint

### Implementation
**File:** [`THE-HYPERCODE/hypercode-core/app/api/dashboard.py`](https://github.com/welshDog/THE-HYPERCODE/blob/main/hypercode-core/app/api/dashboard.py)

**Features:**
- WebSocket endpoint: `ws://localhost:8000/dashboard/ws`
- HTTP fallback: `GET /dashboard/status`
- Broadcasts every 1 second
- Auto-manages connections
- Exponential backoff for reconnection

**Data Structure:**
```typescript
interface DashboardUpdate {
  type: 'dashboard_update';
  agents: AgentStatus[];      // 8 specialized agents
  missions: Mission[];         // Active missions (max 10)
  system: SystemMetrics;       // Overall stats
  timestamp: number;           // Unix timestamp
}
```

**Testing:**
```bash
# Test WebSocket connection
wscat -c ws://localhost:8000/dashboard/ws

# Test HTTP endpoint
curl http://localhost:8000/dashboard/status
```

---

## 🚧 In Progress: Frontend Components

### Architecture

```
BROski Terminal (Next.js)
├── src/
│   ├── hooks/
│   │   └── useWebSocket.ts       [SCAFFOLD READY]
│   ├── components/
│   │   ├── Dashboard/
│   │   │   ├── AgentGrid.tsx       [TO BUILD]
│   │   │   ├── AgentCard.tsx       [TO BUILD]
│   │   │   ├── MissionList.tsx     [TO BUILD]
│   │   │   ├── SystemMetrics.tsx   [TO BUILD]
│   │   │   └── index.tsx           [TO BUILD]
│   └── app/
│       └── dashboard/
│           └── page.tsx            [TO BUILD]
└── styles/
    └── dashboard.css               [TO BUILD]
```

---

## 📝 Implementation Steps

### Day 1: Frontend Foundation (4 hours)

#### Step 1.1: Create WebSocket Hook (45 mins)

**File:** `broski-terminal/src/hooks/useWebSocket.ts`

```typescript
import { useEffect, useState, useCallback, useRef } from 'react';

export interface AgentStatus {
  id: string;
  name: string;
  status: 'idle' | 'active' | 'thinking' | 'executing' | 'offline';
  current_task: string;
  last_heartbeat: string;
  metrics: {
    cpu: number;
    memory: number;
    tasks_completed: number;
  };
}

export interface Mission {
  id: string;
  type: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  progress: number;
  assigned_agents: string[];
  created_at: string;
}

export interface SystemMetrics {
  total_agents: number;
  active_agents: number;
  total_missions: number;
  completed_missions: number;
  uptime: string;
  timestamp: string;
}

export interface DashboardData {
  type: 'dashboard_update';
  agents: AgentStatus[];
  missions: Mission[];
  system: SystemMetrics;
  timestamp: number;
}

export function useWebSocket(url: string) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('✅ Dashboard connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const parsed = JSON.parse(event.data);
      setData(parsed);
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Auto-reconnect after 2s
      setTimeout(connect, 2000);
    };

    wsRef.current = ws;
  }, [url]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { data, isConnected };
}
```

#### Step 1.2: Create Agent Card Component (1 hour)

**File:** `broski-terminal/src/components/Dashboard/AgentCard.tsx`

```tsx
import { AgentStatus } from '@/hooks/useWebSocket';

interface AgentCardProps {
  agent: AgentStatus;
}

export function AgentCard({ agent }: AgentCardProps) {
  const statusColors = {
    idle: 'border-gray-500',
    active: 'border-green-500 shadow-green-500/50',
    thinking: 'border-yellow-500 shadow-yellow-500/50',
    executing: 'border-blue-500 shadow-blue-500/50',
    offline: 'border-red-500',
  };

  return (
    <div
      className={`
        relative p-4 rounded-lg border-2 
        ${statusColors[agent.status]}
        bg-black/80 backdrop-blur-md
        transition-all duration-300
        ${agent.status === 'active' ? 'animate-pulse' : ''}
      `}
    >
      {/* Agent Name */}
      <h3 className="text-lg font-bold text-cyan-400 mb-2">
        {agent.name}
      </h3>

      {/* Status Badge */}
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`
            w-3 h-3 rounded-full 
            ${agent.status === 'offline' ? 'bg-red-500' : 'bg-green-500'}
            ${agent.status === 'active' ? 'animate-ping' : ''}
          `}
        />
        <span className="text-sm text-gray-300 uppercase">
          {agent.status}
        </span>
      </div>

      {/* Current Task */}
      {agent.current_task && (
        <p className="text-sm text-gray-400 mb-3 truncate">
          {agent.current_task}
        </p>
      )}

      {/* Metrics */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">CPU</span>
          <span className="text-cyan-400">{agent.metrics.cpu.toFixed(1)}%</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Memory</span>
          <span className="text-cyan-400">{agent.metrics.memory.toFixed(0)}MB</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Tasks</span>
          <span className="text-cyan-400">{agent.metrics.tasks_completed}</span>
        </div>
      </div>
    </div>
  );
}
```

#### Step 1.3: Create Agent Grid Component (1 hour)

**File:** `broski-terminal/src/components/Dashboard/AgentGrid.tsx`

```tsx
import { useWebSocket, AgentStatus } from '@/hooks/useWebSocket';
import { AgentCard } from './AgentCard';

export function AgentGrid() {
  const { data, isConnected } = useWebSocket(
    `ws://${window.location.hostname}:8000/dashboard/ws`
  );

  if (!isConnected) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-yellow-500 animate-pulse">
          🔌 Connecting to dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {data?.agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
```

#### Step 1.4: Create System Metrics Panel (1 hour)

**File:** `broski-terminal/src/components/Dashboard/SystemMetrics.tsx`

```tsx
import { SystemMetrics } from '@/hooks/useWebSocket';

interface SystemMetricsPanelProps {
  metrics: SystemMetrics;
}

export function SystemMetricsPanel({ metrics }: SystemMetricsPanelProps) {
  return (
    <div className="bg-black/80 backdrop-blur-md border-2 border-cyan-500 rounded-lg p-6">
      <h2 className="text-2xl font-bold text-cyan-400 mb-4">
        📊 System Overview
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Active Agents"
          value={`${metrics.active_agents} / ${metrics.total_agents}`}
          color="text-green-400"
        />
        <MetricCard
          label="Total Missions"
          value={metrics.total_missions}
          color="text-blue-400"
        />
        <MetricCard
          label="Completed"
          value={metrics.completed_missions}
          color="text-purple-400"
        />
        <MetricCard
          label="Uptime"
          value={metrics.uptime}
          color="text-cyan-400"
        />
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: any) {
  return (
    <div>
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}
```

---

### Day 2: Mission Tracking & Polish (4 hours)

#### Step 2.1: Mission List Component (1.5 hours)

**File:** `broski-terminal/src/components/Dashboard/MissionList.tsx`

```tsx
import { Mission } from '@/hooks/useWebSocket';

interface MissionListProps {
  missions: Mission[];
}

export function MissionList({ missions }: MissionListProps) {
  return (
    <div className="bg-black/80 backdrop-blur-md border-2 border-cyan-500 rounded-lg p-6">
      <h2 className="text-2xl font-bold text-cyan-400 mb-4">
        🎯 Active Missions
      </h2>

      {missions.length === 0 ? (
        <p className="text-gray-500 text-center py-8">
          No active missions
        </p>
      ) : (
        <div className="space-y-3">
          {missions.map((mission) => (
            <MissionCard key={mission.id} mission={mission} />
          ))}
        </div>
      )}
    </div>
  );
}

function MissionCard({ mission }: { mission: Mission }) {
  const statusColors = {
    pending: 'bg-gray-500',
    active: 'bg-blue-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
  };

  return (
    <div className="border border-gray-700 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="text-white font-semibold">{mission.type}</h3>
          <p className="text-sm text-gray-400 mt-1">
            {mission.description}
          </p>
        </div>
        <span
          className={`
            px-2 py-1 rounded text-xs font-bold text-white
            ${statusColors[mission.status]}
          `}
        >
          {mission.status}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-700 rounded-full h-2 mt-3">
        <div
          className="bg-cyan-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${mission.progress}%` }}
        />
      </div>

      {/* Assigned Agents */}
      <div className="flex gap-2 mt-3">
        {mission.assigned_agents.map((agent) => (
          <span
            key={agent}
            className="text-xs bg-gray-800 px-2 py-1 rounded text-gray-400"
          >
            {agent}
          </span>
        ))}
      </div>
    </div>
  );
}
```

#### Step 2.2: Main Dashboard Page (1.5 hours)

**File:** `broski-terminal/src/app/dashboard/page.tsx`

```tsx
'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { AgentGrid } from '@/components/Dashboard/AgentGrid';
import { MissionList } from '@/components/Dashboard/MissionList';
import { SystemMetricsPanel } from '@/components/Dashboard/SystemMetrics';

export default function DashboardPage() {
  const { data, isConnected } = useWebSocket(
    `ws://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000/dashboard/ws`
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400 mb-2">
          🔥 HyperCode Mission Control
        </h1>
        <div className="flex items-center gap-2">
          <span
            className={`
              w-3 h-3 rounded-full
              ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}
            `}
          />
          <span className="text-gray-400 text-sm">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* System Metrics */}
      {data?.system && (
        <div className="mb-6">
          <SystemMetricsPanel metrics={data.system} />
        </div>
      )}

      {/* Agent Grid */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-4">
          🤖 Agent Swarm
        </h2>
        <AgentGrid />
      </div>

      {/* Active Missions */}
      {data?.missions && (
        <div>
          <MissionList missions={data.missions} />
        </div>
      )}
    </div>
  );
}
```

---

### Day 3: Testing & Integration (3 hours)

#### Step 3.1: Agent Heartbeat System (1 hour)

**Update each agent to report status to Redis:**

**File:** `agents/base-agent/agent.py` (extend)

```python
import asyncio
import psutil
import time
from redis import asyncio as aioredis

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.redis_client = None
        self.heartbeat_task = None
    
    async def start_heartbeat(self):
        """Start reporting agent status to Redis every 2 seconds."""
        self.redis_client = await aioredis.from_url("redis://redis:6379")
        
        async def heartbeat_loop():
            while True:
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                    
                    await self.redis_client.hset(
                        f"agents:status:{self.name}",
                        mapping={
                            "status": self.current_status,
                            "current_task": self.current_task or "",
                            "last_heartbeat": time.time(),
                            "cpu": cpu_percent,
                            "memory": memory_mb,
                            "tasks_completed": self.tasks_completed
                        }
                    )
                    
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"❌ Heartbeat error: {e}")
                    await asyncio.sleep(5)
        
        self.heartbeat_task = asyncio.create_task(heartbeat_loop())
```

#### Step 3.2: Integration Testing (1 hour)

**Test Plan:**

```bash
# 1. Start the stack
docker-compose up -d

# 2. Verify agents are reporting
redis-cli
> HGETALL agents:status:frontend-specialist
> HGETALL agents:status:backend-specialist

# 3. Test WebSocket endpoint
wscat -c ws://localhost:8000/dashboard/ws

# 4. Open dashboard in browser
open http://localhost:3000/dashboard

# 5. Verify real-time updates
# - Agent cards should update every 1s
# - CPU/memory should change
# - Status should reflect actual agent state
```

#### Step 3.3: Performance Validation (1 hour)

```bash
# Monitor WebSocket performance
docker stats --no-stream hypercode-core

# Expected:
# - CPU: <5% (WebSocket broadcasting is lightweight)
# - Memory: <100MB increase
# - Network: ~10KB/s per connection

# Load test with multiple connections
for i in {1..10}; do
  wscat -c ws://localhost:8000/dashboard/ws &
done

# Verify no performance degradation
```

---

## 📋 Sprint Breakdown

| Day | Tasks | Hours | Deliverables |
|-----|-------|-------|-------------|
| **Day 1** | WebSocket hook, Agent cards, Agent grid, System metrics | 4h | Working dashboard with static data |
| **Day 2** | Mission list, Main page, Styling polish | 4h | Fully functional dashboard UI |
| **Day 3** | Agent heartbeats, Integration tests, Performance validation | 3h | Production-ready feature |
| **Total** | | **11h** | Real-Time Mission Control Dashboard ✅ |

---

## ✅ Definition of Done

- [ ] Backend WebSocket endpoint is deployed and tested
- [ ] Frontend components render agent status correctly
- [ ] Real-time updates work without lag (<100ms latency)
- [ ] All 8 agents report heartbeats to Redis
- [ ] Dashboard handles disconnections gracefully
- [ ] Dashboard is responsive (mobile/tablet/desktop)
- [ ] Performance validated (CPU <5%, Memory <100MB)
- [ ] Documentation updated
- [ ] Team demo completed

---

## 🚀 Next Steps After Phase 1

1. **Phase 2: Intelligent Mission Router** (5 days)
   - LLM-powered task decomposition
   - Automatic agent assignment
   - DAG execution engine

2. **Phase 3: Swarm Memory** (8 days)
   - Shared context store
   - Vector search for artifacts
   - Cross-agent collaboration

---

**Status:** Ready to build! Backend is deployed, frontend scaffold is ready. Let's ship this! 🚀

---

*Built with ❤️ by the HyperCode Team*  
*Phase 1 initialized: February 11, 2026*
