---
name: hypercode-merge-bridge
description: Cross-repo integration patterns for the 3-repo HyperCode ecosystem — Course ↔ V2.4 ↔ SDK. Use when working on Merge Roadmap Phase 3 (agent access shop), Phase 4 (npm run graduate), or Phase 5 (course metrics in Grafana). Also covers API contracts, shared secrets, and the identity bridge between systems.
---

# HyperCode Merge Bridge Skill

Full plan in: `hyper-vibe-coding-hub/MERGE_ROADMAP.md`

## The 3-Repo Architecture

```
Hyper-Vibe-Course (Vercel + Supabase)
    │ course-profile Edge Function
    │ sync-tokens-to-v24 Edge Function
    │ shop-purchase Edge Function
    ▼
HyperCode V2.4 (Docker, localhost:8000)
    │ POST /api/v1/economy/award-from-course
    │ POST /api/v1/access/provision    ← PHASE 3 (TO BUILD)
    │ POST /api/v1/access/graduate     ← PHASE 3 (TO BUILD)
    ▼
HyperAgent-SDK (npm @w3lshdog/hyper-agent)
    │ npx hyper-agent validate
    │ npx hyper-agent graduate
```

## Phase Status

| Phase | Goal | Status |
|-------|------|--------|
| 0 | Hard conflict fixes | ✅ DONE |
| 1 | Identity Bridge (Discord ID link) | ✅ DONE |
| 2 | Token Sync (Course → V2.4) | ✅ Code done — needs webhook registered |
| 3 | Agent Access + Shop | 🔴 BUILD THIS |
| 4 | `npm run graduate` | 🔴 BUILD THIS (after Phase 3) |
| 5 | Course Metrics in Grafana | 🔴 BUILD THIS |

---

## Phase 3 — What to Build

### V2.4 side (build first)

```python
# backend/app/api/v1/endpoints/access.py

# POST /api/v1/access/provision
# Input: {"discord_id": "...", "tier": "sandbox"}
# Action: create scoped API key, set agent_access_level=1
# Returns: {"api_key": "hc_...", "mission_control_url": "...", "expires_at": "..."}

# POST /api/v1/access/graduate  
# Input: {"discord_id": "...", "course_user_id": "..."}
# Action: upgrade agent_access_level to 4 (HyperCoder)
# Returns: {"ok": true, "new_level": 4}
```

API key format: `hc_` + `secrets.token_urlsafe(32)` (43 chars total)

### Course side (after V2.4 endpoints exist)

```typescript
// Update supabase/functions/shop-purchase/index.ts
// Add detection for metadata.type === 'agent_access':

if (item.metadata?.type === 'agent_access') {
  const provision = await fetch(
    `${V24_API_URL}/api/v1/access/provision`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ discord_id: user.discord_id, tier: 'sandbox' })
    }
  )
  const { api_key, mission_control_url } = await provision.json()
  // Store in shop_purchases.metadata
  // Send Discord DM via broski-bot with credentials
}
```

### Shop item to seed

```sql
INSERT INTO shop_items (id, name, description, cost_tokens, metadata, is_active)
VALUES (
  'agent-sandbox-access',
  'Agent Sandbox Access',
  'Unlock real HyperCode V2.4 agent sandbox. Build your first AI agent.',
  300,
  '{"type": "agent_access", "tier": "sandbox"}',
  true
);
```

---

## Phase 4 — Graduate Script

### Edge Functions needed (Course side)

```
supabase/functions/generate-v2-config/index.ts   ← generates V2.4 config
supabase/functions/award-graduate-badge/index.ts  ← awards badge + calls V2.4
```

### Package.json script (Course root)

```json
{
  "scripts": {
    "graduate": "node scripts/graduate.js"
  }
}
```

---

## Phase 5 — Course Metrics in Grafana

### Edge Function (Course side)

```typescript
// supabase/functions/course-metrics-relay/index.ts
// Triggered by: lesson_completions, token_transactions, shop_purchases

const metrics = {
  lesson_completions_total: completionCount,
  tokens_awarded_total: tokenSum,
  shop_purchases_total: purchaseCount,
}

// POST to V2.4 metrics receiver
await fetch(`${V24_API_URL}/api/v1/metrics/course`, {
  method: 'POST',
  body: JSON.stringify(metrics)
})
```

### V2.4 side

```python
# Add to prometheus.yml scrape config:
- job_name: 'course-metrics'
  static_configs:
    - targets: ['hypercode-core:8000']
  metrics_path: '/api/v1/metrics/course/prometheus'
```

---

## Shared Secrets Contract

```
COURSE_WEBHOOK_SECRET    → Both V2.4 .env AND Supabase Edge Function secrets
X-Sync-Secret header     → Used by sync-tokens-to-v24 to authenticate calls to V2.4
V24_API_URL              → Supabase env var pointing to V2.4 (use ngrok for local)
```

## What NEVER Crosses the Bridge

```
❌ Supabase schema into V2.4 Postgres
❌ V2.4 SQLAlchemy models into Course
❌ .env files from either repo
❌ Discord bot tokens (each bot = separate identity)
❌ apps/web/ (archived, never migrate)
```

## Testing the Bridge End-to-End

```bash
# 1. Token sync (Phase 2 verify)
curl -X POST http://localhost:8000/api/v1/economy/award-from-course \
  -H "X-Sync-Secret: $COURSE_WEBHOOK_SECRET" \
  -d '{"discord_id":"test","delta":50,"reason":"test","source_id":"test-001"}'

# 2. Access provision (Phase 3 verify — after building)
curl -X POST http://localhost:8000/api/v1/access/provision \
  -H "Content-Type: application/json" \
  -d '{"discord_id":"test_user","tier":"sandbox"}'

# 3. Course profile (Phase 1 verify)
curl https://{project}.supabase.co/functions/v1/course-profile \
  -H "Authorization: Bearer $ANON_KEY" \
  -d '{"discord_id":"test_user"}'
```
