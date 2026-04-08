# 🟢 Phase 1 — Wire It Up (Mission System → Core)  

**Goal:** Make the stack feel like one unified brain: one source of truth, one task stream, one dashboard.

## ✅ Phase 1 Outcomes

- Mission UI displays real tasks from `hypercode-core` (not a duplicate DB).
- Task lifecycle is end-to-end: UI → Core API → Celery → Agent → DB → UI.
- DB schema is versioned with Alembic (no more “mystery tables”).

## 🧠 Source Of Truth (Decide Once)

- **Tasks:** `hypercode-core` (Postgres `hypercode.tasks`)
- **Projects:** `hypercode-core` (Postgres `hypercode.projects`)
- **Auth:** `hypercode-core` JWT (`/api/v1/auth/login/access-token`)

## 🔗 Service Contract (Who talks to who)

- **Mission System UI** → talks to **Mission System Server** (simple `/api/*`)
- **Mission System Server** → proxies to **hypercode-core** (`/api/v1/*`)

This keeps browser auth simple while letting Core stay the central nervous system.

## 🧩 Endpoint Mapping (Mission System → Core)

### Read Tasks

- Mission: `GET /api/tasks`
- Core: `GET /api/v1/tasks/` (requires Bearer token)

**Transform (Core → Mission UI shape):**
- `urgency`: map from `task.priority` (`high|medium|low`)
- `status`: map `todo|in_progress|review|done` → `pending|completed` (UI-friendly)
- `impact/effort`: computed placeholders until Core gains real fields

### Create Task

- Mission: `POST /api/tasks`
- Core: `POST /api/v1/tasks/`

Core payload today:
```json
{
  "title": "…",
  "description": "…",
  "priority": "high",
  "type": "translate",
  "project_id": 1
}
```

### Mark Done

Mission currently expects:
- `PUT /api/tasks/:id/done` with `{ evidence_link, peer_review_checked }`

Core currently has **no update endpoint** for tasks, and tasks have **no evidence fields**.

Phase 1 must add in Core:
- `PUT /api/v1/tasks/{id}` (or `/complete`) to set `status=DONE`
- Optional: add `evidence_link` + `peer_review_checked` columns (or store in a `task_events` table)

### Dashboard Stats

- Mission: `GET /api/dashboard`
- Core: either:
  - add `GET /api/v1/dashboard/mission` (recommended), or
  - compute from `GET /api/v1/tasks/` server-side in Mission System

## 🗄️ DB Migrations (Replace create_all)

Core now ships an initial Alembic revision.

Fresh DB:
```powershell
docker exec hypercode-core alembic upgrade head
```

Existing DB created via `create_all`:
```powershell
docker exec hypercode-core alembic stamp head
```

## ✅ Acceptance Criteria (Phase 1 “done”)

- Mission UI task list matches Core task list (same IDs, same titles).
- Creating a task in Mission UI results in:
  - Core DB row created
  - Celery worker receives `hypercode.tasks.process_agent_job`
  - Task output is saved back to Core DB
  - Mission UI refresh shows status/output
- No duplicate “tasks” DB exists in Mission System for production mode.

