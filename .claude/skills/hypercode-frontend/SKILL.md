---
name: hypercode-frontend
description: HyperCode Mission Control dashboard — Next.js/React frontend patterns, CognitiveUplink WebSocket UI, useHyperSync hook, useSensoryProfile neurodivergent UX hook, and dashboard component conventions. Use when working on dashboard components, WebSocket client code, frontend state management, or the neurodivergent UI layer.
---

# HyperCode Frontend Skill

## Stack

- **Framework:** Next.js (React) — `agents/dashboard/`
- **Language:** TypeScript throughout
- **Testing:** Vitest
- **WS target:** `ws://localhost:8081/ws/uplink` (crew-orchestrator)
- **HTTP target:** `http://localhost:8000/api/v1` (FastAPI backend)

---

## Key Files

| File | Purpose |
|---|---|
| `agents/dashboard/components/CognitiveUplink.tsx` | Main AI chat/command UI + WS client |
| `agents/dashboard/hooks/useHyperSync.ts` | HyperSync threshold detection + handoff trigger |
| `agents/dashboard/hooks/useSensoryProfile.ts` | Neurodivergent UX preferences (motion, contrast, density) |
| `agents/dashboard/lib/api.ts` | Typed HTTP client for all backend endpoints |
| `agents/dashboard/components/` | All dashboard panels and widgets |

---

## CognitiveUplink — WebSocket Message Format

⚠️ **CRITICAL BUG — must fix before WS messages route correctly:**

```typescript
// WRONG (current) — orchestrator ignores this
{ type: "command", payload: { ... } }

// CORRECT — orchestrator expects this
{ type: "execute", payload: { ... } }
```

File: `agents/dashboard/components/CognitiveUplink.tsx` ~line 130
Orchestrator handler: `agents/crew-orchestrator/main.py` lines 796–866

### Full message shape

```typescript
interface UplinkMessage {
  type: "execute" | "ping";
  payload: {
    command: string;
    agent?: string;
    conversation_id?: string;
    hypersync_token?: string; // set when resuming from HyperSync handoff
  };
}
```

### Incoming message shape

```typescript
interface UplinkResponse {
  type: "result" | "error" | "stream" | "pong";
  data: unknown;
  agent?: string;
  timestamp: string;
}
```

---

## useHyperSync Hook

Detects context overflow and triggers HyperSync handoff:

```typescript
const { checkThreshold, initiateHandoff, resumeFromToken } = useHyperSync()

// Call on every message append
const overflow = checkThreshold(conversationText) // true if > 12,000 chars

if (overflow) {
  const { token, sessionId } = await initiateHandoff(conversationState)
  // Opens new tab: window.open(`/?resume=${token}`)
}

// On page load — check for resume token
const token = new URLSearchParams(location.search).get('resume')
if (token) await resumeFromToken(token)
```

**Threshold:** 12,000 chars (configurable via `NEXT_PUBLIC_HYPERSYNC_THRESHOLD`)

---

## useSensoryProfile Hook

Neurodivergent-first UX — respects user's cognitive load preferences:

```typescript
const { profile, setProfile } = useSensoryProfile()

// Profile shape
{
  reducedMotion: boolean,    // disable animations
  highContrast: boolean,     // WCAG AAA contrast
  compactDensity: boolean,   // tighter spacing for focus
  dyslexiaFont: boolean,     // OpenDyslexic font
  focusMode: boolean,        // hide non-essential panels
  colorTheme: 'dark' | 'light' | 'midnight' | 'forest'
}
```

Profile is persisted to `localStorage` and injected as CSS variables.

---

## Dashboard Component Conventions

- All panels are `PascalCase.tsx` in `agents/dashboard/components/`
- Props typed with `interface ComponentNameProps`
- Async data via SWR or React Query — no raw `useEffect` for fetching
- WS connections managed at page level, passed down via context
- Tailwind for styling — utility classes only, no custom CSS files
- Emojis as visual anchors in headings (neurodivergent UX pattern)

---

## WebSocket Connection Pattern

```typescript
const ws = useRef<WebSocket | null>(null)

useEffect(() => {
  ws.current = new WebSocket('ws://localhost:8081/ws/uplink')
  ws.current.onmessage = (event) => {
    const msg = JSON.parse(event.data) as UplinkResponse
    // handle msg.type
  }
  return () => ws.current?.close()
}, [])

// Send
const send = (command: string) => {
  ws.current?.send(JSON.stringify({
    type: "execute",  // ← always "execute", not "command"
    payload: { command }
  }))
}
```

---

## Event Stream (read-only)

For live agent event feed — connect to `/ws/events` on crew-orchestrator:

```typescript
// ws://localhost:8081/ws/events
// Receives: { channel: string, data: unknown, timestamp: string }
// Channels: ws_tasks | broski_events | approval_requests
```
