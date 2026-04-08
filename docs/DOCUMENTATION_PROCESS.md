## Documentation Process

**Status:** Active  
**Last Updated:** 2026-03-19

This repository contains a mix of canonical documentation, working notes, and historical reports. This file defines what “up to date” means, how documentation changes are reviewed, and how documentation stays synchronized across stakeholders.

### 1. Documentation Sources of Truth

**Canonical (must stay current)**
- `docs/` is the canonical documentation hub. Start at `docs/index.md`.
- Root entrypoints (`README.md`, `QUICKSTART.md`, `RUNBOOK.md`, `DEPLOYMENT_GUIDE.md`) should be kept aligned with `docs/`.

**Working notes (may drift)**
- `docs/notes/` contains drafts and scratchpads. Notes must be labeled as non-canonical if they are linked from canonical docs.

**Reports and historical snapshots (may drift by design)**
- `docs/reports/`, `docs/health-reports/`, and `docs/archive/` contain dated snapshots, audits, and one-off deliverables.
- These documents should not be edited to “keep current” unless the document explicitly states it is maintained.

### 2. Terminology and Formatting Standards

**Command style**
- Use `docker compose ...` everywhere (not `docker-compose ...`).
- Use `127.0.0.1` for local URLs unless a service is explicitly bound to a different interface.

**Service naming**
- Prefer Docker Compose service/container names as they appear in `docker-compose.yml` (e.g. `hypercode-core`, `hypercode-ollama`, `throttle-agent`).

**LLM runtime naming**
- Use “Ollama-compatible API” when referring to the HTTP interface.
- Use “Ollama runtime” for the `hypercode-ollama` service.
- Use “Model Runner” for the MCP profile service and call out when it is an alternative to running `hypercode-ollama`.

### 3. Documentation Review Checklist

For any change that impacts setup, deployment, API usage, security, or runbooks:
- Links resolve (relative links tested in the repo).
- Commands are copy-paste safe and consistent with current tooling (`docker compose`).
- API examples match actual routes, prefixes, and authentication behavior.
- No secrets are embedded (use placeholders and document where values come from).
- Never paste `.env` contents into tickets, PRs, or chat. If a secret is exposed, rotate it immediately.
- If screenshots/diagrams exist in the doc, they match current UI labels, ports, and service names.

### 4. Documentation Validation

When a doc includes runnable examples:
- Prefer adding a short “Verification” section that indicates exactly how to validate the example.
- Where feasible, validate examples in CI using lightweight checks (formatting, link checks, example syntax).

### 5. Maintenance Schedule

**Every change (ongoing)**
- If a change alters behavior, update the nearest canonical doc in the same PR.
- Add a short entry to `docs/CHANGELOG_DOCS.md`.

**Weekly (owner review)**
- Verify `README.md`, `QUICKSTART.md`, `RUNBOOK.md`, and `docs/index.md` match the current `docker-compose.yml` profiles and ports.
- Scan for new duplicated docs and consolidate to canonical docs.

**Monthly (ops review)**
- Review `docs/TROUBLESHOOTING.md` and `RUNBOOK.md` against the most frequent incidents.
- Confirm observability docs match deployed metrics/log format.
