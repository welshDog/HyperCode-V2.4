# Documentation Sync Checklist

**Doc Tag:** v2.0.0 | **Last Updated:** 2026-03-10

Use this checklist to keep documentation aligned with code changes, infra changes, and released features.

## When to Run This Checklist

- Before merging a PR that changes behavior, configs, or public interfaces
- Before cutting a release tag
- After changing Docker Compose services, ports, or health checks
- After changing environment variables or defaults in `backend/app/core/config.py`

## Checklist (PR Author)

### 1) Identify doc impact

- [ ] Does this change affect **environment variables**? Update `.env.example`.
- [ ] Does this change affect **Docker/K8s**? Update `docker-compose*.yml` docs and deployment guides.
- [ ] Does this change affect **API routes**? Update API docs and any examples.
- [ ] Does this change affect **agent behavior**? Update `docs/notes/Goal for the agents.md` and any agent-facing docs.

### 2) Update canonical docs

- [ ] Root README: new features, links, and quick start remain accurate.
- [ ] [REPOSITORY_REPORT.md](../REPOSITORY_REPORT.md): keep links relative and metrics current.
- [ ] [docs/configuration/TINYLLAMA_CONFIGURATION.md](configuration/TINYLLAMA_CONFIGURATION.md): update model/host defaults.
- [ ] [CONTRIBUTING.md](../CONTRIBUTING.md): update contributor instructions.

### 3) Update doc metadata

For any doc you touched:

- [ ] Set `Doc Tag` to the current release version (e.g., `v2.0.0`).
- [ ] Set `Last Updated` to today’s date (ISO: `YYYY-MM-DD`).

### 4) Validate cross-references

- [ ] Grep for broken internal links (common drift: renamed files, moved docs).
- [ ] Ensure links are repo-relative (avoid `file:///` links).
- [ ] Ensure examples match the current service names:
  - `hypercode-ollama` (not `hypercode-llama`)
  - `docker compose` (Compose V2)

### 5) Run the “docs sanity” checks

- [ ] Backend tests still pass: `cd backend && python -m pytest -q`
- [ ] Backend lint passes: `cd backend && python -m ruff check app tests`
- [ ] Backend typecheck passes: `cd backend && python -m mypy app`

## Checklist (Maintainer / Release)

- [ ] Ensure [CHANGELOG.md](../CHANGELOG.md) entries match merged PRs.
- [ ] Tag release (`vX.Y.Z`) and ensure doc tags are consistent.
- [ ] If a doc is a historical report, add a **Snapshot banner** at the top with a link to current canonical docs.

