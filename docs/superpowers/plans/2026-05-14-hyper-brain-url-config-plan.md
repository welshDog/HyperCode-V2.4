# Hyper Brain URL Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Hyper IDE Station “🧠 Hyper Brain” button configurable via `NEXT_PUBLIC_HYPER_BRAIN_URL`, with a safe localhost fallback when unset.

**Architecture:** Client resolves URL from `process.env.NEXT_PUBLIC_HYPER_BRAIN_URL` first. If missing, derive `http://localhost:8100/ui` (or `127.0.0.1`) based on current hostname. Docker build passes the env var as a build arg so Next can embed it in the client bundle.

**Tech Stack:** Next.js (client components), Docker (build args), docker compose

---

### Task 1: Client URL resolver

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/dashboard/components/shell/AppShell.tsx`

- [ ] Add a `getHyperBrainUrl()` helper and compute `hyperBrainUrl` via `useMemo`.
- [ ] Prefer `process.env.NEXT_PUBLIC_HYPER_BRAIN_URL` when set.
- [ ] Else, if `window.location.hostname` is `localhost` or `127.0.0.1`, use that hostname with `:8100/ui`.
- [ ] Else, fallback to `http://localhost:8100/ui`.

---

### Task 2: Make env var build-time effective

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/dashboard/Dockerfile`
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.agents.yml`

- [ ] Add `ARG NEXT_PUBLIC_HYPER_BRAIN_URL` and `ENV NEXT_PUBLIC_HYPER_BRAIN_URL=$NEXT_PUBLIC_HYPER_BRAIN_URL` in the dashboard Dockerfile builder stage before `npm run build`.
- [ ] Pass the build arg in compose for `dashboard` using `${NEXT_PUBLIC_HYPER_BRAIN_URL:-}`.

---

### Task 3: Update spec note

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docs/superpowers/specs/2026-05-14-hyper-ide-station-hyper-brain-link-design.md`

- [ ] Mention `NEXT_PUBLIC_HYPER_BRAIN_URL` and note it is embedded at build time for the dashboard.

---

### Task 4: Verification

- [ ] Build with a custom value:

```powershell
$env:NEXT_PUBLIC_HYPER_BRAIN_URL='http://127.0.0.1:8100/ui'
docker compose build dashboard
docker compose up -d --no-deps --force-recreate dashboard
```

- [ ] Confirm server HTML includes the configured link:

```powershell
(Invoke-WebRequest -UseBasicParsing http://localhost:8088/).Content | Select-String -SimpleMatch "http://127.0.0.1:8100/ui"
```

