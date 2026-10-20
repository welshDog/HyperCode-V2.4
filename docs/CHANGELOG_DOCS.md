## Documentation Changelog

This file tracks documentation synchronization changes (what changed and why). It is separate from the product changelog.

### 2026-10-20

- Added `docs/NEXT_SESSION_HANDOVER_2026-10-20.md`: the leaked-secret rotation and where the old values also lived, the green security gate (#685-#688), the hyperhealth upgrade and its rollback, traps learned, and the open items. No secret values.

### 2026-10-19

- Added `docs/superpowers/plans/2026-10-19-hyperhealth-fastapi-upgrade.md`: an evidence-backed plan to clear the remaining hyperhealth dependency advisories (FastAPI/Starlette upgrade, drop the unused pyOpenSSL and slowapi, add a smoke test and CI job). Plan only; no dependency changes yet.

### 2026-10-18

- Marked NEXT_TASKS C11 fixed (iac-scan and weekly Trivy wiring) and recorded the two advisory gates and their backlog.

- Recorded the Dependabot triage and policy (NEXT_TASKS C10/C11 and the new policy section, handover, WHATS_DONE).

- Marked NEXT_TASKS C6 done (gate e2e re-enabled, PR #633) and recorded the two serious axe findings.

- Marked NEXT_TASKS C5 done (No Legacy Paths cleanup, PR #632); mcp configs left open for a decision.

- Marked NEXT_TASKS C4 done (stale unit tests repaired, PR #631); WHATS_DONE updated.

- Added `docs/NEXT_SESSION_HANDOVER_2026-10-18.md` (CI recovery, leaked-secret finding) and a new C1-C9 section in `docs/NEXT_TASKS.md`.
- Docs CI repaired: terminology rule now scans only the canonical files (199 old matches in 45 historical docs); lychee `--exclude` quoting, quoted `docs/**/*.md` glob, removed `--exclude-mail` (gone in lychee 0.23). The link check is advisory until the 106 broken links are cleaned up (NEXT_TASKS C9).

### 2026-04-20

- Canonical docs synchronized to current V2.4.2 behavior and naming:
  - Standardized docs hub references to `docs/INDEX.md` (case-correct).
  - Fixed broken/incorrect documentation links in `docs/README.md`, `docs/DOCUMENTATION_*` files, and doc index pointers.
  - Updated Mission Control documentation to match current WebSocket endpoints and dashboard panes.
- Documentation governance tightened:
  - Updated `docs/DOCUMENTATION_PROCESS.md` to include versioning guidance and explicit ownership model.
  - Aligned documentation CI checks to current canonical file locations and reduced false positives.

### 2026-03-19

- `README.md`
  - Fixed BROski API endpoint paths to include `/api/v1/...` to match actual router prefixes.
  - Replaced placeholder Discord invite with an explicit “to be published” note to prevent stale links.
- `QUICKSTART.md`
  - Removed references to non-existent `.env.agents.example` and `docker-compose.agents.yml`.
  - Standardized commands to `docker compose` and documented compose profiles for agents.
  - Clarified that `START_HERE.md` is for the MCP Gateway + Model Runner profile, not the base stack.
- `docs/API.md`
  - Corrected auth route to `/api/v1/auth/login/access-token` and clarified it uses form-encoded data.
  - Fixed invalid JSON example by removing inline comments.
  - Added a copy-paste login example consistent with FastAPI OAuth2 flow.
- `docs/INDEX.md`
  - Updated language to avoid “Ollama-only” framing and reflect multiple Ollama-compatible runtime options.
- `docs/ai/brain-architecture.md`
  - Standardized wording to “Ollama-compatible API” and added Model Runner configuration option.
- `docs/DOCUMENTATION_INDEX.md`
  - Converted to a Docker report index with correct links into `docs/reports/`.
  - Added explicit pointer to `docs/index.md` for repo-wide canonical documentation.
- `CONTRIBUTING.md`
  - Fixed corrupted heading character and updated project structure to match current directories.
  - Added documentation standards, review checklist, and validation expectations.
- `docs/DOCUMENTATION_PROCESS.md`
  - Added a documented review process and a maintenance schedule to keep docs synchronized.
  - Added an explicit rule to avoid pasting `.env` contents and to rotate secrets if exposed.
- `docs/screenshots-gallery.md`
  - Removed broken in-repo image links and converted the file into a screenshot inventory with recommended storage location.
- `docs/assets/README.md`
  - Documented where to store versioned documentation assets and how to manage screenshots.
- `DEPLOY_THROTTLE_IMPROVEMENTS.sh`
  - Standardized displayed commands to `docker compose` to match current tooling.
- `THROTTLE_AGENT_IMPROVEMENTS_COMPLETE.md`
  - Updated deploy commands to `docker compose` for consistency.
- `backend/app/api/v1/endpoints/tasks.py`
  - Removed a stale inline comment referencing a removed queue integration.
- `.gitignore`
  - Added `docs/outputs/` to prevent committing generated output artifacts.
