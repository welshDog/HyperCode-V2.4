# Pricing Tab → Grafana Embed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the WelshDog HyperCode IDE `/pricing` tab content with an embedded Grafana “tool” (iframe) that behaves like a simple in-app window/browser.

**Architecture:** The IDE dashboard (Next.js app in `agents/dashboard`) will render an iframe pointing to Grafana (defaulting to the Ecosystem Launchpad dashboard). A small “window browser” toolbar (tabs + optional path input + pop-out link) controls which Grafana page is shown. Grafana must allow iframe embedding (set via container env vars).

**Tech Stack:** Next.js (App Router) + React 19 + TypeScript, Vitest + Testing Library, Docker Compose (Grafana env vars).

---

## Scope / Assumptions (lock these before you start)

- Grafana runs locally on `http://127.0.0.1:3001` (or `http://localhost:3001`), and the IDE runs on `http://127.0.0.1:8088`.
- We will embed Grafana using the same hostname as the IDE (`127.0.0.1` vs `localhost`) to avoid cookie/session weirdness.
- We will not re-implement pricing/Stripe inside the IDE during this task (pricing cards become obsolete on this page).

---

## File Map (what changes where)

**Docker/ops**
- Modify: `docker-compose.observability.yml` (enable Grafana iframe embedding)

**Dashboard UI**
- Create: `agents/dashboard/components/grafana/GrafanaBrowser.tsx` (toolbar + iframe wrapper)
- Modify: `agents/dashboard/app/pricing/page.tsx` (replace pricing UI with GrafanaBrowser)
- Modify (optional): `agents/dashboard/components/shell/AppShell.tsx` (rename nav label to Grafana)

**Tests**
- Create: `agents/dashboard/__tests__/GrafanaPricingPage.test.tsx`

---

### Task 1: Allow Grafana to be embedded in an iframe

**Files:**
- Modify: `docker-compose.observability.yml`

- [ ] **Step 1: Add Grafana embedding env var**

Edit `docker-compose.observability.yml` and append the environment variable under `grafana.environment:`:

```yaml
  grafana:
    environment:
      - GF_SECURITY_ADMIN_USER=${GF_SECURITY_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GF_SECURITY_ADMIN_PASSWORD:-}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SECURITY_ALLOW_EMBEDDING=true
```

- [ ] **Step 2: Restart Grafana**

Run (from `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`):

```powershell
docker compose -f docker-compose.core.yml -f docker-compose.observability.yml up -d grafana
```

Expected: Grafana container restarts successfully and stays healthy.

- [ ] **Step 3: Verify headers allow embedding**

Run:

```powershell
curl.exe -I http://127.0.0.1:3001/login
```

Expected:
- No `X-Frame-Options: deny` header (or at least not one that blocks embedding).

---

### Task 2: Build the “Grafana window browser” component

**Files:**
- Create: `agents/dashboard/components/grafana/GrafanaBrowser.tsx`

- [ ] **Step 1: Create the component (no tests yet)**

Create `agents/dashboard/components/grafana/GrafanaBrowser.tsx`:

```tsx
'use client'

import React, { useMemo, useState } from 'react'

type GrafanaView = 'launchpad' | 'dashboards' | 'explore' | 'alerting' | 'custom'

function getGrafanaBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_GRAFANA_URL) return process.env.NEXT_PUBLIC_GRAFANA_URL
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    if (host === 'localhost' || host === '127.0.0.1') return `http://${host}:3001`
  }
  return 'http://127.0.0.1:3001'
}

function viewToPath(view: GrafanaView, customPath: string): string {
  if (view === 'launchpad') return '/d/hypercode-ecosystem-launchpad'
  if (view === 'dashboards') return '/dashboards'
  if (view === 'explore') return '/explore'
  if (view === 'alerting') return '/alerting/list'
  const trimmed = customPath.trim()
  if (!trimmed) return '/dashboards'
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) return trimmed
  if (!trimmed.startsWith('/')) return `/${trimmed}`
  return trimmed
}

export function GrafanaBrowser(): React.JSX.Element {
  const grafanaBaseUrl = useMemo(() => getGrafanaBaseUrl(), [])
  const [view, setView] = useState<GrafanaView>('launchpad')
  const [customPath, setCustomPath] = useState<string>('')

  const src = useMemo(() => {
    const pathOrUrl = viewToPath(view, customPath)
    if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) return pathOrUrl
    return `${grafanaBaseUrl}${pathOrUrl}`
  }, [grafanaBaseUrl, view, customPath])

  return (
    <div className="pane" style={{ height: '100%' }}>
      <div className="pane-header" style={{ gap: 10, alignItems: 'center' }}>
        <div className="pane-title">📈 Grafana</div>
        <div style={{ display: 'inline-flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn" onClick={() => setView('launchpad')} aria-pressed={view === 'launchpad'}>
            Launchpad
          </button>
          <button className="btn" onClick={() => setView('dashboards')} aria-pressed={view === 'dashboards'}>
            Dashboards
          </button>
          <button className="btn" onClick={() => setView('explore')} aria-pressed={view === 'explore'}>
            Explore
          </button>
          <button className="btn" onClick={() => setView('alerting')} aria-pressed={view === 'alerting'}>
            Alerting
          </button>
        </div>
        <div style={{ marginLeft: 'auto', display: 'inline-flex', gap: 8, alignItems: 'center' }}>
          <label className="hc-mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            Path
          </label>
          <input
            value={customPath}
            onChange={(e) => setCustomPath(e.target.value)}
            onFocus={() => setView('custom')}
            placeholder="/d/hypercode-mission-control"
            aria-label="Grafana path"
            style={{
              width: 280,
              maxWidth: '42vw',
              padding: '6px 10px',
              borderRadius: 8,
              border: '1px solid var(--pane-border)',
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
            }}
          />
          <a className="btn" href={src} target="_blank" rel="noreferrer">
            Pop out
          </a>
        </div>
      </div>
      <div style={{ height: '100%', overflow: 'hidden' }}>
        <iframe
          data-testid="grafana-iframe"
          title="Grafana"
          src={src}
          style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
          allow="fullscreen"
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Ensure it fits the shell height**

If the iframe does not fill the available height, adjust the wrapper in Task 3 to ensure the page’s outer container uses `height: '100%'`.

---

### Task 3: Replace `/pricing` page with the Grafana tool

**Files:**
- Modify: `agents/dashboard/app/pricing/page.tsx`

- [ ] **Step 1: Replace the page content**

Replace `agents/dashboard/app/pricing/page.tsx` with:

```tsx
'use client'

import React from 'react'
import { GrafanaBrowser } from '@/components/grafana/GrafanaBrowser'

export default function PricingPage(): React.JSX.Element {
  return (
    <div style={{ height: '100%' }}>
      <GrafanaBrowser />
    </div>
  )
}
```

---

### Task 4: Rename the nav label (Pricing → Grafana)

**Files:**
- Modify: `agents/dashboard/components/shell/AppShell.tsx`

- [ ] **Step 1: Change the label but keep the route**

Update the nav item:

```ts
  { href: '/pricing', label: '📈 Grafana' },
```

This keeps your existing `/pricing` URL stable while turning it into the Grafana tool tab.

---

### Task 5: Add tests (Vitest)

**Files:**
- Create: `agents/dashboard/__tests__/GrafanaPricingPage.test.tsx`

- [ ] **Step 1: Write a failing test**

Create `agents/dashboard/__tests__/GrafanaPricingPage.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import PricingPage from '../app/pricing/page'

describe('/pricing embeds Grafana', () => {
  const prev = process.env.NEXT_PUBLIC_GRAFANA_URL

  beforeEach(() => {
    process.env.NEXT_PUBLIC_GRAFANA_URL = 'http://127.0.0.1:3001'
  })

  afterEach(() => {
    process.env.NEXT_PUBLIC_GRAFANA_URL = prev
  })

  it('renders an iframe pointing at Grafana launchpad by default', () => {
    render(<PricingPage />)
    const iframe = screen.getByTestId('grafana-iframe') as HTMLIFrameElement
    expect(iframe).toBeInTheDocument()
    expect(iframe.getAttribute('src')).toContain('http://127.0.0.1:3001')
    expect(iframe.getAttribute('src')).toContain('/d/hypercode-ecosystem-launchpad')
  })

  it('renders Grafana toolbar buttons', () => {
    render(<PricingPage />)
    expect(screen.getByRole('button', { name: 'Launchpad' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dashboards' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Explore' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Alerting' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Pop out' })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the test**

Run:

```powershell
cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4\agents\dashboard
npm test
```

Expected: PASS.

---

### Task 6: Manual verification in the browser

**Files:**
- No code changes

- [ ] **Step 1: Start the IDE dashboard**

Run:

```powershell
cd H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4\agents\dashboard
npm run dev
```

Expected: Next dev server runs.

- [ ] **Step 2: Open `/pricing`**

Open:
- `http://127.0.0.1:8088/pricing`

Expected:
- You see the “📈 Grafana” pane and the embedded Grafana Launchpad dashboard.
- Clicking “Explore” switches the iframe to Grafana Explore.
- “Pop out” opens the same URL in a new tab.

---

### Task 7: Commit (dashboard repo + HyperCode repo)

**Files:**
- Dashboard repo changes are inside `agents/dashboard/`
- Grafana embedding change is in repo root compose

- [ ] **Step 1: Commit dashboard UI + tests**

From `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4\agents\dashboard`:

```powershell
git add app/pricing/page.tsx components/grafana/GrafanaBrowser.tsx __tests__/GrafanaPricingPage.test.tsx components/shell/AppShell.tsx
git commit -m "feat: embed Grafana in /pricing tab"
```

- [ ] **Step 2: Commit Grafana embedding config**

From `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`:

```powershell
git add docker-compose.observability.yml
git commit -m "chore: allow Grafana iframe embedding"
```

- [ ] **Step 3: Push**

```powershell
git push
```

---

## Self-review checklist (run before execution)

- No placeholders: every task has exact file paths, code, and commands.
- Iframe host alignment: IDE hostname matches `NEXT_PUBLIC_GRAFANA_URL` hostname.
- Grafana embedding: `GF_SECURITY_ALLOW_EMBEDDING=true` is set and container restarted.

