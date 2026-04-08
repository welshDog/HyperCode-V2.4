# 🧠 Planning System — Test Guide

## Quick Start

```bash
# 1. Install deps
pip install httpx rich

# 2. Run with your local server
python tests/test_planning_system.py

# 3. Run against a different URL
BASE_URL=http://your-server:8000 python tests/test_planning_system.py

# 4. Run with an auth token
BASE_URL=http://localhost:8000 HYPERCODE_TOKEN=your_jwt_here python tests/test_planning_system.py
```

## What's Tested

| # | Test | What it checks |
|---|------|----------------|
| 1 | Health check | Server is up |
| 2 | Generate from PRD | Full plan pipeline, phases count |
| 3 | Generate from Issue | Bug → plan → file_changes_summary |
| 4 | Generate from Design | Architecture doc → tech spec plan |
| 5 | Auto-detect generic | Falls back to generic type gracefully |
| 6 | `?persist=true` | Query param accepted, no crash |
| 7 | generate-from-task 404 | Non-existent task returns proper error |
| 8 | Schema validation | Missing `content` returns 422 |
| 9 | Router keyword detect | `generate plan` task_type triggers planner |
| 10 | TaskCreate generate_plan | `generate_plan: true` field accepted |

## Postman Collection

Import `tests/planning_postman_collection.json` into Postman.

1. Set the `base_url` variable to your server
2. Set the `token` variable to your JWT
3. Run the collection

## Expected Happy-Path Response Shape

```json
{
  "summary": "Implement GitHub OAuth login flow",
  "phases": [
    {
      "phase_number": 1,
      "title": "Auth Foundation",
      "description": "Set up OAuth provider integration and session management",
      "workflow_steps": ["Configure OAuth app credentials", "Implement callback handler"]
    }
  ],
  "file_changes_summary": [
    {
      "file_path": "backend/app/api/v1/endpoints/auth.py",
      "change_type": "create",
      "description": "New OAuth endpoints",
      "rationale": "Centralise auth logic"
    }
  ],
  "follow_up_instructions": "Verify token expiry handling with the security agent."
}
```

## 🔥 BROski Power Level: Test Commander
