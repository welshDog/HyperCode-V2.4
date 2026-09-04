# Mission Ledger — HyperCode V3 Foundation

## Overview

The Mission Ledger is the persistent, auditable record of all agent work in HyperCode. Every mission has:
- A clear goal
- Assigned builder (Claude Code or specialist agent)
- Branch and PR tracking
- Proof of work (tests, scans, deployments)
- Approval state
- Rollback route
- Next action

## Schema

### missions
```sql
CREATE TABLE missions (
  mission_id TEXT PRIMARY KEY DEFAULT 'HC-' || to_char(now(), 'YYYY-MM') || '-' || lpad(next_id::text, 3, '0'),
  goal TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', -- pending, in_progress, awaiting_review, approved, completed, failed, rolled_back
  builder TEXT NOT NULL DEFAULT 'claude-code',
  branch TEXT,
  pr_url TEXT,
  pr_number INTEGER,
  preview_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  next_action TEXT,
  context_pack JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}'
);
```

### mission_events
```sql
CREATE TABLE mission_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id TEXT REFERENCES missions(mission_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL, -- created, started, task_completed, review_requested, approved, deployed, failed, rolled_back
  event_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### mission_proof
```sql
CREATE TABLE mission_proof (
  proof_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id TEXT REFERENCES missions(mission_id) ON DELETE CASCADE,
  proof_type TEXT NOT NULL, -- lint, tests, security_scan, playwright, deployment, rollback
  status TEXT NOT NULL, -- pending, passed, failed, skipped
  result_json JSONB DEFAULT '{}',
  artifact_url TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## API Endpoints

### POST /missions
```json
{
  "goal": "Add secure Vercel preview deployment flow",
  "builder": "claude-code",
  "context_pack": {
    "related_issues": ["#123"],
    "acceptance_criteria": ["Preview deploys on PR", "Secure token handling"]
  }
}
```

Response:
```json
{
  "mission_id": "HC-2026-09-001",
  "status": "pending",
  "next_action": "Review mission plan and approve start"
}
```

### PATCH /missions/{mission_id}
```json
{
  "status": "in_progress",
  "branch": "feat/vercel-preview-flow",
  "next_action": "Claude Code implementing feature"
}
```

### GET /missions/{mission_id}
```json
{
  "mission_id": "HC-2026-09-001",
  "goal": "Add secure Vercel preview deployment flow",
  "status": "in_progress",
  "builder": "claude-code",
  "branch": "feat/vercel-preview-flow",
  "pr_number": 453,
  "proof": {
    "lint": "passed",
    "tests": "passed",
    "security_scan": "passed",
    "playwright": "pending"
  },
  "next_action": "Review PR and approve preview deployment"
}
```

### GET /missions/{mission_id}/proof
Returns all proof records for a mission.

## Integration Points

1. **Mission Director** — Creates missions, updates status, assigns builders
2. **Crew Orchestrator** — Records events, attaches proof, manages workflow state
3. **Healer** — Monitors mission health, triggers rollback on failure
4. **Dashboard** — Displays mission timeline, proof, next action
5. **Claude Code** — Reads mission context, writes proof artifacts

## Security

- All missions require authentication (Supabase JWT)
- Write operations logged to mission_events
- Rollback requires explicit approval (no auto-rollback without human confirmation)
- Sensitive data (tokens, secrets) stored in Supabase vault, not mission metadata

## Next Steps

1. Create Supabase migrations
2. Build Python API (FastAPI or Flask)
3. Integrate with Mission Director
4. Add proof attachment to Crew Orchestrator
5. Build dashboard view
