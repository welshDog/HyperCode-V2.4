# Morning Ecosystem To‑Do Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In one focused morning session: (1) fix HYPER Agents IDE “Failed to load …” for agents/chat/skills, (2) finish Stripe go-live polish for the course, (3) clear the HyperCode IDE “credential validation / CRITICAL health” blockers.

**Architecture:** Prioritize user-visible unblocks first (Agents IDE), then revenue loop polish (Stripe links/env), then local platform stability (HyperCode IDE health + credentials). Each task ends with an objective verification command and a commit.

**Tech Stack:** FastAPI (Python) + Vite/React (Agents IDE), Vercel env + Stripe + Supabase, Docker Compose + Next.js dashboard (HyperCode).

---

## Task 1: Fix HYPER Agents IDE “Failed to load …”

### Why this is the next best win
- The IDE UI is already served by the FastAPI backend (same origin) but the backend can still reject API calls (e.g. `ADMIN_TOKEN` enabled) or return `503` while warming up.

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/hyper-agents-ide/ui/src/lib/api.ts`
- Create: `h:/HYPERFOCUSZONE/HperCore/hyper-agents-ide/ui/src/lib/adminToken.ts`
- Modify: `h:/HYPERFOCUSZONE/HperCore/hyper-agents-ide/ui/src/components/SidebarAgents.tsx`
- Modify: `h:/HYPERFOCUSZONE/HperCore/hyper-agents-ide/ui/src/components/MainChat.tsx`
- Modify: `h:/HYPERFOCUSZONE/HperCore/hyper-agents-ide/ui/src/components/SidebarTools.tsx`
- Verify: `h:/HYPERFOCUSZONE/HperCore/hyper-agents-ide/src/trae_ide_api/main.py` (auth behavior)

---

### Task 1.1: Add admin-token support in the UI (fix 401/403 cases)

- [ ] **Step 1: Create a tiny localStorage token helper**

Create `ui/src/lib/adminToken.ts`:

```ts
const KEY = "hyper_agents_ide_admin_token";

export function getAdminToken(): string | null {
  try {
    const raw = localStorage.getItem(KEY);
    const trimmed = (raw ?? "").trim();
    return trimmed ? trimmed : null;
  } catch {
    return null;
  }
}

export function setAdminToken(token: string): void {
  const trimmed = token.trim();
  if (!trimmed) return;
  localStorage.setItem(KEY, trimmed);
}

export function clearAdminToken(): void {
  localStorage.removeItem(KEY);
}
```

- [ ] **Step 2: Wrap fetch() to include Authorization header when token exists**

Update `ui/src/lib/api.ts` to route requests through a shared helper:

```ts
import type { Agent, ChatMessage, Skill } from "./types";
import { getAdminToken } from "./adminToken";

type ApiErrorShape = { detail?: string };

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = typeof window !== "undefined" ? getAdminToken() : null;
  const headers = new Headers(init?.headers ?? {});
  if (token) headers.set("authorization", `Bearer ${token}`);
  return fetch(path, { ...init, headers });
}

async function parseError(res: Response): Promise<string> {
  if (res.status === 401) return "Admin token required (401).";
  if (res.status === 403) return "Admin token rejected (403).";
  if (res.status === 503) return "Backend warming up (503). Retrying soon…";
  const body = (await res.json().catch(() => null)) as ApiErrorShape | null;
  return body?.detail ? String(body.detail) : `Request failed (${res.status}).`;
}

export async function fetchAgents(): Promise<Agent[]> {
  const res = await apiFetch("/api/agents");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Agent[]>;
}

export async function sendChat(agent_id: string, message: string): Promise<ChatMessage> {
  const res = await apiFetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id, message, meta: {} })
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ChatMessage>;
}

export async function fetchChat(): Promise<ChatMessage[]> {
  const res = await apiFetch("/api/chat");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<ChatMessage[]>;
}

export async function trainSkill(payload: {
  agent_id: string;
  title: string;
  body: string;
  idempotency_key: string;
}): Promise<Skill> {
  const res = await apiFetch("/api/skills", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Skill>;
}

export async function fetchSkills(): Promise<Skill[]> {
  const res = await apiFetch("/api/skills");
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<Skill[]>;
}

export async function exportSkills(): Promise<{ export_root: string; written_files: string[] }> {
  const res = await apiFetch("/api/skills/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json() as Promise<{ export_root: string; written_files: string[] }>;
}
```

- [ ] **Step 3: Add a small “Set Admin Token” UI affordance**

In each of:
- `ui/src/components/SidebarAgents.tsx`
- `ui/src/components/MainChat.tsx`
- `ui/src/components/SidebarTools.tsx`

Add a small inline input shown only when the error message contains `Admin token`:

```tsx
import { setAdminToken, clearAdminToken } from "../lib/adminToken";
```

Render block (same pattern in each component’s error panel):

```tsx
{error?.includes("Admin token") ? (
  <div className="mt-2 flex items-center gap-2">
    <input
      placeholder="Paste ADMIN_TOKEN…"
      className="w-full rounded-xl border border-white/10 bg-hz-bg/50 px-3 py-2 text-xs text-hz-text placeholder:text-hz-muted outline-none ring-0 focus:border-hz-accent/40"
      onKeyDown={(e) => {
        if (e.key !== "Enter") return;
        const target = e.target as HTMLInputElement;
        setAdminToken(target.value);
        target.value = "";
        window.location.reload();
      }}
    />
    <button
      type="button"
      className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-hz-text hover:bg-white/[0.05]"
      onClick={() => {
        clearAdminToken();
        window.location.reload();
      }}
    >
      Clear
    </button>
  </div>
) : null}
```

---

### Task 1.2: Add safe auto-retry for 503 “warming up”

- [ ] **Step 1: SidebarAgents auto-retry**

In `SidebarAgents.tsx`, add:

```ts
const [retryTick, setRetryTick] = useState(0);
```

Update the effect dependency list and retry logic:

```ts
useEffect(() => {
  let cancelled = false;
  fetchAgents()
    .then((data) => {
      if (cancelled) return;
      setAgents(data);
      setError(null);
    })
    .catch((e) => {
      if (cancelled) return;
      const msg = e instanceof Error ? e.message : "Failed to load agents";
      setError(msg);
      if (msg.includes("(503)")) {
        setTimeout(() => setRetryTick((v) => v + 1), 2000);
      }
    });
  return () => {
    cancelled = true;
  };
}, [retryTick]);
```

- [ ] **Step 2: Repeat the same retry pattern for Chat and Skills**

Use the same `retryTick` pattern in:
- `MainChat.tsx` (for `fetchChat()` and for send errors)
- `SidebarTools.tsx` (for `fetchSkills()`)

---

### Task 1.3: Verify + ship

- [ ] **Step 1: Run backend unit tests**

```powershell
cd H:\HYPERFOCUSZONE\HperCore\hyper-agents-ide
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 2: Typecheck + build UI**

```powershell
cd H:\HYPERFOCUSZONE\HperCore\hyper-agents-ide\ui
npm run build
```

Expected: PASS (tsc + vite build).

- [ ] **Step 3: Smoke check locally**

```powershell
cd H:\HYPERFOCUSZONE\HperCore\hyper-agents-ide
python -m uvicorn trae_ide_api.main:app --host 127.0.0.1 --port 3500
```

Open `http://127.0.0.1:3500/` and confirm:
- Agents list loads
- Chat history loads
- Skills list loads

- [ ] **Step 4: Commit**

```powershell
git add ui/src/lib/api.ts ui/src/lib/adminToken.ts ui/src/components/SidebarAgents.tsx ui/src/components/MainChat.tsx ui/src/components/SidebarTools.tsx
git commit -m "fix: Agents IDE auth + warming-up retries"
git push
```

---

## Task 2: Stripe go-live polish (Course)

**Goal:** Pricing never dead-ends and a smoke purchase produces entitlements.

- [ ] **Step 1: Confirm Payment Links exist (Stripe TEST first)**
- [ ] **Step 2: Set Vercel env vars (`VITE_STRIPE_*_URL`)**
- [ ] **Step 3: Redeploy Vercel**
- [ ] **Step 4: Click-test: Pricing uses Payment Link when present**
- [ ] **Step 5: Do one smoke purchase and verify DB side-effects**
  - `users.subscription_tier` updated
  - `token_transactions` row created
  - `enrollments` row created

---

## Task 3: HyperCode IDE “CRITICAL / Could not validate credentials”

**Goal:** Dashboard health goes green and agents/tasks stop failing auth.

- [ ] **Step 1: Identify which service is failing**

```powershell
cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4
docker compose -f docker-compose.yml ps
```

- [ ] **Step 2: Inspect failing container logs**

```powershell
docker logs --tail 200 <container_name>
```

- [ ] **Step 3: Verify HyperCode dashboard endpoints**

```powershell
curl.exe -s http://127.0.0.1:8088/api/health
curl.exe -s http://127.0.0.1:8000/health
```

- [ ] **Step 4: Fix credentials source**

Check `.env` / compose env for the failing integration, then restart only the affected service:

```powershell
docker compose -f docker-compose.yml up -d <service_name>
```

---

## Self-review checklist

- No secrets committed (no `.env` changes committed).
- Each task ends with objective verification (tests/health endpoints).
- Each repo is committed in its own repo folder with `fix:` / `feat:` / `docs:` / `chore:` prefixes.

