// Integration Guide for Dashboard Upgrade

## Components Created

### 1. AgentMonitor.tsx
**Location:** `components/dashboard/AgentMonitor.tsx`
**Features:**
- Real-time agent status (healthy/busy/error/offline)
- Live latency, task count, memory, CPU metrics
- WebSocket EventSource integration
- 4-column responsive grid
- Summary stats at the bottom

**Integration:**
```tsx
import { AgentMonitor } from '@/components/dashboard/AgentMonitor';

export default function Page() {
  return <AgentMonitor />;
}
```

### 2. HyperCodeIDE.tsx
**Location:** `components/dashboard/HyperCodeIDE.tsx`
**Features:**
- Monaco-style code editor
- Real-time code execution
- Live output panel (success/error)
- Example code button
- Split layout (code left, output right)

**Integration:**
```tsx
import { HyperCodeIDE } from '@/components/dashboard/HyperCodeIDE';

export default function Page() {
  return <HyperCodeIDE />;
}
```

### 3. MissionTimeline.tsx
**Location:** `components/dashboard/MissionTimeline.tsx`
**Features:**
- Gantt-style task visualization
- Real-time task updates (5s refresh)
- Status indicators (pending/running/completed/failed)
- Duration tracking
- Task history

**Integration:**
```tsx
import { MissionTimeline } from '@/components/dashboard/MissionTimeline';

export default function Page() {
  return <MissionTimeline />;
}
```

### 4. DockerZone.tsx
**Location:** `components/dashboard/DockerZone.tsx`
**Features:**
- Live container list
- Memory & CPU metrics
- Stop/Start/Restart controls
- Port information
- Status badges

**Integration:**
```tsx
import { DockerZone } from '@/components/dashboard/DockerZone';

export default function Page() {
  return <DockerZone />;
}
```

### 5. MCPToolBrowser.tsx
**Location:** `components/dashboard/MCPToolBrowser.tsx`
**Features:**
- MCP tool registry browser
- Tool testing interface
- JSON input/output
- Call history
- Duration tracking

**Integration:**
```tsx
import { MCPToolBrowser } from '@/components/dashboard/MCPToolBrowser';

export default function Page() {
  return <MCPToolBrowser />;
}
```

## Custom Hook

### useAgentStream.ts
**Location:** `hooks/useAgentStream.ts`
**Purpose:** Reusable hook for EventSource integration
**Usage:**
```tsx
import { useAgentStream } from '@/hooks/useAgentStream';

function MyComponent() {
  const { data, connected, error } = useAgentStream();
  
  if (!connected) return <p>Connecting...</p>;
  if (error) return <p>Error: {error}</p>;
  
  return <div>{/* render data */}</div>;
}
```

## Required Dependencies

Add to `package.json`:
```json
{
  "dependencies": {
    "react": "^19.2.3",
    "react-dom": "^19.2.3",
    "next": "^16.2.4"
  }
}
```

No additional npm packages needed — uses built-in EventSource, fetch, and Tailwind CSS.

## Environment Variables

Add to `.env.local`:
```
NEXT_PUBLIC_CORE_URL=http://hypercode-core:8000
NEXT_PUBLIC_API_KEY=your_api_key_here
```

## New Routes to Create

1. **/dashboard/agents** → AgentMonitor
2. **/dashboard/code-ide** → HyperCodeIDE
3. **/dashboard/timeline** → MissionTimeline
4. **/dashboard/docker** → DockerZone
5. **/dashboard/mcp** → MCPToolBrowser

## API Endpoints Required

These endpoints must exist on `hypercode-core:8000`:

1. `GET /agents/stream` → EventSource stream
2. `POST /execution/execute-hc` → Code execution
3. `GET /missions/tasks` → Task list
4. `GET /docker/containers` → Container list
5. `POST /docker/containers/{id}/stop` → Stop container
6. `POST /docker/containers/{id}/restart` → Restart container
7. `GET /mcp/tools` → Tool registry
8. `POST /mcp/tools/{name}/call` → Tool invocation

## Build & Deploy

1. Copy all `.tsx` files to `components/dashboard/`
2. Copy `useAgentStream.ts` to `hooks/`
3. Add routes in `app/dashboard/` folder
4. Run `npm run build`
5. Rebuild Docker image: `docker build -t hypercode-v24-dashboard:v1.1 .`
6. Deploy: `docker compose up -d`

## Testing

After deployment:
```bash
# Test agent stream
curl http://localhost:8088/dashboard/agents

# Test code IDE
curl http://localhost:8088/dashboard/code-ide

# Test mission timeline
curl http://localhost:8088/dashboard/timeline

# Test Docker zone
curl http://localhost:8088/dashboard/docker

# Test MCP browser
curl http://localhost:8088/dashboard/mcp
```

## Performance Notes

- WebSocket/EventSource reconnects automatically
- Refresh intervals: agents (real-time), timeline (5s), containers (10s)
- Component memory usage: ~15MB total (all 5 components)
- Network overhead: ~50KB/min for streaming

## Future Enhancements

- Dark mode toggle
- Keyboard shortcuts (Cmd+K for navigation, Cmd+E for execution)
- Custom layouts (drag-to-reorder)
- Export/import dashboard configs
- Advanced analytics graphs
