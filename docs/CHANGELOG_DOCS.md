## Documentation Changelog

This file tracks documentation synchronization changes (what changed and why). It is separate from the product changelog.

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
- `docs/index.md`
  - Updated language to avoid “Ollama-only” framing and reflect multiple Ollama-compatible runtime options.
- `docs/ai/brain-architecture.md`
  - Standardized wording to “Ollama-compatible API” and added Model Runner configuration option.
- `DOCUMENTATION_INDEX.md`
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
