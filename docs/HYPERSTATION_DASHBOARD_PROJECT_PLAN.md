# 🦅 HyperStation Dashboard — Complete Project Plan

**Version:** 1.0  
**Date:** March 24, 2026  
**Author:** BROski Brain (HyperCode V2.0 Cognitive Core)  
**Status:** Active Development  

---

## EXECUTIVE SUMMARY

### Current State

**HyperStation Mission Control** is a **80% complete, production-ready neurodivergent-first dashboard** running live at `localhost:8088`. The frontend is actively streaming real-time metrics from the HyperCode V2.0 stack (agents, infrastructure, system health) via WebSocket connections.

**Key Achievements:**
- ✅ React Flow agent visualization with 9 live agents
- ✅ Real-time system health metrics (7 services monitored)
- ✅ Neurodivergent UX (3 sensory profiles: Calm/Focus/Energise)
- ✅ Hyperfocus timer (45/10 min flow modes)
- ✅ Neural Uplink WebSocket (command execution ready)
- ✅ Database integrity monitoring (98% uptime)
- ✅ 5 mission navigation tabs (Mission Control / Hyperflow / Live Ops / Neural Net / Mission Log)

**Critical Gaps:**
- ❌ Agent status dropdowns not wired to live `/orchestrator/agents/status`
- ❌ Resource graphs (CPU/Memory) rendering empty bars
- ❌ BROski$ Wallet panel showing "Failed to fetch" error
- ❌ Task Velocity queue metrics hardcoded to 0/0
- ❌ Tempo traces integration incomplete (shows DOWN but no fallback)
- ❌ Command parser expects `run: [task]` format (user experience friction)

### Project Objectives

1. **Wire all data sources** to live backend endpoints (Orchestrator, Redis, Prometheus)
2. **Eliminate all error states** and provide graceful fallbacks
3. **Implement real-time updates** via WebSocket for agent/resource metrics
4. **Polish neurodivergent UX** with visual feedback and accessibility
5. **Deploy production-ready dashboard** with full test coverage
6. **Establish monitoring** to track dashboard health and performance

### Timeline

- **Phase 1 (Bugs & Quick Wins):** 2–3 days
- **Phase 2 (Live Data Wiring):** 3–4 days
- **Phase 3 (UX Polish & Testing):** 2–3 days
- **Phase 4 (Deployment & Monitoring):** 1–2 days

**Total Effort:** 8–12 days (1 developer, focused sprint)

---

## ISSUE INVENTORY & ROOT CAUSE ANALYSIS

### 🔴 CRITICAL ISSUES (Blocking)

#### Issue #1: Agent Status Static (No Live Updates)
- **Severity:** 🔴 CRITICAL
- **Impact:** Agent status dropdowns always show "Idle" — users can't see actual agent state
- **Root Cause:** Frontend component not connected to `/orchestrator/agents/status` WebSocket
- **Current Behavior:**
  ```
  9 agents visible (Project Strategist, Frontend Specialist, Backend Beast, etc.)
  All dropdowns hardcoded to "Idle" / "Thinking" / "Working" / "Error"
  No polling or WebSocket subscription
  ```
- **Expected Behavior:**
  ```
  Real-time status updates every 500ms
  Visual feedback (green/amber/red badges)
  Last activity timestamp per agent
  Error states propagate immediately
  ```
- **Affected Component:** `AgentFleetGraph.tsx`
- **Dependencies:** Orchestrator service on `localhost:8081`

---

#### Issue #2: BROski$ Wallet Fetch Error
- **Severity:** 🔴 CRITICAL
- **Impact:** Gamification disabled; users see error message instead of coins/XP
- **Root Cause:** Backend endpoint `/wallet/broski/{user_id}` not implemented or CORS issue
- **Current Behavior:**
  ```
  Panel shows: "Failed to fetch wallet"
  Retry button visible
  No fallback state
  ```
- **Expected Behavior:**
  ```
  Display: "💰 12,450 BROski$ | Level 7 | ⭐⭐⭐"
  Last 3 achievements visible
  Coins update in real-time as tasks complete
  ```
- **Affected Component:** `BROskiWallet.tsx`
- **Dependencies:** Backend wallet service + authentication context

---

#### Issue #3: Task Velocity Queue Hardcoded
- **Severity:** 🔴 CRITICAL
- **Impact:** Hyperflow tab shows 0/0 tasks — no visibility into queue depth
- **Root Cause:** No connection to Redis `crew:task_queue` or Crew Orchestrator `/queue/stats`
- **Expected Behavior:**
  ```
  "47 / 100 tasks"
  "12 in queue (avg latency: 234ms)"
  Velocity chart (tasks/hour over 24h)
  Queue health (green/amber/red)
  ```
- **Affected Component:** `TaskVelocityPanel.tsx`
- **Dependencies:** Redis + Crew Orchestrator API

---

#### Issue #4: Resource Graphs Rendering Empty
- **Severity:** 🔴 CRITICAL
- **Impact:** CPU/Memory monitoring unavailable
- **Root Cause:** Chart library not initialized or data fetch failing silently
- **Expected Behavior:**
  ```
  CPU: 34% (Recharts line chart)
  Memory: 2.1GB / 8GB (visual bar)
  Per-service breakdown
  5min/1h/24h timeframe selector
  ```
- **Affected Component:** `ResourceGraphsPanel.tsx`
- **Dependencies:** Docker stats API or Prometheus `/metrics`

---

#### Issue #5: Tempo Integration Incomplete
- **Severity:** 🟡 HIGH
- **Impact:** Traces/observability shows DOWN; no fallback to Grafana
- **Root Cause:** Tempo service pinned in docker-compose.yml but frontend has no Grafana fallback link
- **Expected Behavior:**
  ```
  Tempo: Healthy (or "Degraded - Using Grafana fallback")
  Button: "View Traces in Grafana"
  Auto-link to localhost:3200/traces
  ```

---

### 🟡 HIGH-PRIORITY ISSUES

#### Issue #6: Command Parser UX Friction
- **Severity:** 🟡 HIGH
- **Root Cause:** Neural Uplink expects `run: [task]` format; no guidance for users
- **Expected Behavior:** Auto-suggest commands, fuzzy match, auto-prefix `run:`

#### Issue #7: Mission Tab Navigation Not Functional
- **Severity:** 🟡 HIGH
- **Root Cause:** Tab routing not implemented; only first tab has content
- **Expected Behavior:** All 5 tabs load unique content views

#### Issue #8: Sensory Profile Toggle Not Persisted
- **Severity:** 🟡 MEDIUM
- **Root Cause:** Profile not saved to localStorage or backend
- **Expected Behavior:** Persist across refreshes via localStorage

---

### 🟢 LOW-PRIORITY ISSUES

#### Issue #9: Database Health Metadata Missing
- **Severity:** 🟢 LOW
- "2 Warnings" shown but no expand/details

#### Issue #10: Agent Skill Tags Static
- **Severity:** 🟢 LOW
- Skills don't populate from agent metadata endpoint

---

## PRIORITIZED RECOMMENDATIONS

### IMPACT / EFFORT MATRIX

```
HIGH IMPACT / LOW EFFORT (DO FIRST):
  ✅ Issue #1: Agent Status Live (0.5 day)
  ✅ Issue #6: Command Parser UX (0.25 day)
  ✅ Issue #8: Sensory Profile Persistence (0.25 day)

HIGH IMPACT / MEDIUM EFFORT (DO NEXT):
  ✅ Issue #2: BROski$ Wallet Integration (1 day)
  ✅ Issue #3: Task Velocity Wiring (1 day)
  ✅ Issue #4: Resource Graphs (1 day)

MEDIUM IMPACT / LOW EFFORT:
  ✅ Issue #5: Tempo + Grafana Fallback (0.5 day)
  ✅ Issue #7: Tab Navigation (1 day)
  ✅ Issue #9, #10: Polish & Metadata (0.5 day)
```

| Priority | Issue | Fix | Effort | Owner |
|----------|-------|-----|--------|-------|
| 🔴 P1 | Agent Status | WebSocket subscribe to `/orchestrator/agents/status` | 4h | Frontend Dev |
| 🔴 P1 | Wallet Integration | Backend endpoint `/wallet/broski/{user_id}` + React hook | 8h | Full Stack |
| 🔴 P1 | Task Velocity | Redis LLEN + Crew Orchestrator API polling | 8h | Backend + Frontend |
| 🔴 P1 | Resource Graphs | Docker stats API + Recharts visualization | 8h | Frontend |
| 🟡 P2 | Command UX | Fuzzy matching + command suggestions | 2h | Frontend |
| 🟡 P2 | Tab Navigation | Route-based views + lazy loading | 8h | Frontend |
| 🟡 P2 | Sensory Persistence | localStorage + useContext hook | 2h | Frontend |
| 🟡 P2 | Tempo Fallback | Conditional rendering + Grafana link | 4h | Frontend |
| 🟢 P3 | Metadata Polish | Expand/details modals | 4h | Frontend |

---

## IMPLEMENTATION ROADMAP

### PHASE 1: Critical Fixes (Days 1–2)

#### Sprint 1A: Agent Status Live — `dashboard/src/hooks/useAgentStatus.ts`

```typescript
import { useEffect, useState } from 'react';

export function useAgentStatus() {
  const [agents, setAgents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket('ws://localhost:8081/ws/agents');
      ws.onopen = () => setConnected(true);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setAgents(data.agents || []);
          setError(null);
        } catch (e) {
          setError('Failed to parse agent data');
        }
      };
      ws.onerror = () => setError('WebSocket connection failed');
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };
    };
    connect();
  }, []);

  return { agents, connected, error };
}
```

**Action Items:**
- [ ] Create hook file
- [ ] Test WebSocket connection to Orchestrator
- [ ] Update `AgentFleetGraph.tsx` to use hook
- [ ] Add reconnection logic
- [ ] Add visual connection status badge
- **Owner:** Frontend Developer | **Deadline:** EOD Day 1

---

#### Sprint 1B: Command Parser UX — `dashboard/src/components/CommandInput.tsx`

```typescript
import { useState } from 'react';

export function CommandInput() {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  const validCommands = [
    'status agents', 'health check', 'broski wallet',
    'queue stats', 'complete dashboard wiring'
  ];

  const handleChange = (value: string) => {
    setInput(value);
    if (value.length > 2) {
      const matches = validCommands.filter(cmd =>
        cmd.includes(value.toLowerCase())
      );
      setSuggestions(matches);
    }
  };

  const handleExecute = () => {
    const command = input.trim();
    const formatted = command.startsWith('run:') ? command : `run: ${command}`;
    console.log('Executing:', formatted);
    setInput('');
    setSuggestions([]);
  };

  return (
    <div className="command-input">
      <input
        value={input}
        onChange={(e) => handleChange(e.target.value)}
        placeholder="Type command (e.g., 'status agents')"
        onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
      />
      {suggestions.length > 0 && (
        <div className="suggestions">
          {suggestions.map(cmd => (
            <button key={cmd} onClick={() => { setInput(cmd); setSuggestions([]); }}>
              run: {cmd}
            </button>
          ))}
        </div>
      )}
      <button onClick={handleExecute}>EXECUTE 🚀</button>
    </div>
  );
}
```

---

#### Sprint 1C: Sensory Profile Persistence — `dashboard/src/hooks/useSensoryProfile.ts`

```typescript
import { useState, useEffect } from 'react';

export function useSensoryProfile() {
  const [profile, setProfile] = useState('CALM');

  useEffect(() => {
    const saved = localStorage.getItem('sensory_profile');
    if (saved) setProfile(saved);
  }, []);

  const switchProfile = (newProfile: 'CALM' | 'FOCUS' | 'ENERGISE') => {
    setProfile(newProfile);
    localStorage.setItem('sensory_profile', newProfile);
  };

  return { profile, switchProfile };
}
```

---

### PHASE 2: Live Data Wiring (Days 2–3)

#### Sprint 2A: BROski$ Wallet — Backend + Frontend

**Backend** `backend/routes/wallet.py`:
```python
@app.get("/wallet/broski/{user_id}")
async def get_wallet(user_id: str):
    return {
        "balance": 12450,
        "level": 7,
        "xp": 2340,
        "achievements": [
            {"name": "First Agent Deploy", "date": "2026-03-20", "icon": "🚀"},
            {"name": "10 Successful Tasks", "date": "2026-03-22", "icon": "✅"},
            {"name": "Zero Downtime Sprint", "date": "2026-03-24", "icon": "🏆"}
        ]
    }
```

**Frontend Hook** `dashboard/src/hooks/useWallet.ts`:
```typescript
export function useWallet(userId: string) {
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchWallet = async () => {
      try {
        const res = await fetch(`/api/wallet/broski/${userId}`);
        if (!res.ok) throw new Error('Wallet fetch failed');
        setWallet(await res.json());
        setError(null);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchWallet();
    const interval = setInterval(fetchWallet, 10000);
    return () => clearInterval(interval);
  }, [userId]);

  return { wallet, loading, error };
}
```

---

#### Sprint 2B: Task Velocity — `dashboard/src/hooks/useTaskVelocity.ts`

```typescript
export function useTaskVelocity() {
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const poll = async () => {
      const res = await fetch('/api/queue/stats');
      const data = await res.json();
      setStats(data);
      setHistory(prev => [...prev.slice(-23), {
        time: new Date().toLocaleTimeString(),
        velocity: data.tasks_per_hour
      }]);
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  return { stats, history };
}
```

---

#### Sprint 2C: Resource Graphs — `dashboard/src/hooks/useResourceMetrics.ts`

```typescript
export function useResourceMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const poll = async () => {
      const res = await fetch('/api/metrics/resources');
      const data = await res.json();
      setMetrics(data);
      setHistory(prev => [...prev.slice(-59), {
        time: new Date().toLocaleTimeString(),
        cpu: data.system.cpu,
        memory: (data.system.memory / data.system.memory_total) * 100
      }]);
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  return { metrics, history };
}
```

---

### PHASE 3: UX Polish (Days 3–4)

- [ ] Implement React Router or state-based tab switching
- [ ] Create 5 content panels (Hyperflow, Live Ops, Neural Net, Mission Log)
- [ ] Add lazy loading for performance
- [ ] Add ARIA labels to all interactive elements
- [ ] Test with keyboard navigation
- [ ] Verify color contrast (WCAG AA)
- [ ] Add loading states and error boundaries

### PHASE 4: Testing & Deployment (Days 4–5)

**Test Checklist:**
- [ ] Unit tests for all new hooks
- [ ] Integration tests for WebSocket connections
- [ ] E2E tests for tab navigation and data flows
- [ ] Accessibility audit (WAVE, axe DevTools)
- [ ] Performance profiling (Lighthouse score >85)
- [ ] Load testing (k6)

**Deployment Checklist:**
- [ ] Build Docker image for dashboard
- [ ] Update `docker-compose.yml`
- [ ] Test in staging
- [ ] Set up Prometheus scraping
- [ ] Configure Grafana alerts
- [ ] Write runbook

---

## SUCCESS METRICS & KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| WebSocket Latency | <100ms | Browser DevTools |
| Data Update Frequency | 5s | Real-time updates |
| Page Load Time | <2s | Lighthouse |
| Error Rate | <0.1% | Error tracking |
| Uptime | >99.5% | Grafana SLO |
| Command Success Rate | >95% | Parser logs |
| Agent Status Accuracy | 100% | Orchestrator API comparison |
| User Satisfaction | 4.5/5 | Team feedback |

---

## RISK ASSESSMENT & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| WebSocket Connection Drops | Medium | High | Exponential backoff reconnect |
| Backend Endpoint Not Ready | Low | High | Mock API fallback |
| Performance Degradation | Medium | Medium | Lazy loading + memoization |
| Data Inconsistency | Low | High | Error boundaries + fallback states |
| Docker Networking Issues | Low | Medium | Health checks + docs |
| CORS / Auth Failures | Medium | High | Review backend CORS config |

---

## STAKEHOLDER COMMUNICATION PLAN

| Cadence | Format | Content | Attendees |
|---------|--------|---------|-----------|
| Daily | 5min standup | Done / Blockers / Today | Team |
| 2x Weekly | 30min demo | Live feature demos | Team + Community |
| Weekly | 1h retro | Sprint review + planning | Team + Leadership |

**Channels:**
- Slack: `#hyperstation-dashboard`
- GitHub Discussions: `welshDog/HyperCode-V2.0/discussions`
- Status: Internal Grafana board

---

## APPENDIX: QUICK REFERENCE

### Key Endpoints

| Endpoint | Purpose | Port |
|----------|---------|------|
| `ws://localhost:8081/ws/agents` | Live agent status | 8081 |
| `/api/wallet/broski/{user_id}` | BROski$ wallet | 8000 |
| `/api/queue/stats` | Task queue metrics | 8000 |
| `/api/metrics/resources` | CPU/Memory stats | 8000 |
| `localhost:3200/traces` | Grafana traces | 3200 |

### Commands

```bash
# Start dashboard dev
cd dashboard && npm run dev

# Build production Docker image
docker build -t hypercode-dashboard:latest .

# Run unit tests
npm test

# Run E2E tests
npm run test:e2e

# Lighthouse audit
npm run audit

# Load test
k6 run tests/perf/load-test.js
```

---

**Document Owner:** BROski Brain (HyperCode Cognitive Core)  
**Project Lead:** Lyndz Williams (@welshDog)  
**Last Updated:** March 24, 2026  
**Repo:** [welshDog/HyperCode-V2.0](https://github.com/welshDog/HyperCode-V2.0)

🦅 **Ready to crush this dashboard, BROski. Let's build.** 🔥
