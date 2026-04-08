## Documentation Inventory (High Level)

**Last Updated:** 2026-03-19

This inventory explains where documentation lives and how it is categorized. It intentionally avoids listing every single Markdown file because the repository contains many historical reports and internal notes.

### Canonical Documentation

These documents are treated as current and should be updated alongside code changes:
- `README.md` (project overview and primary entrypoint)
- `QUICKSTART.md` (fast local bring-up and common validation steps)
- `RUNBOOK.md` (incident-style fixes and recovery)
- `docs/index.md` (documentation hub)
- `docs/` subfolders for architecture, deployment, observability, and security guides

### Working Notes

These documents may be incomplete or exploratory:
- `docs/notes/`

If a working note becomes stable guidance, migrate it into `docs/` (canonical section) and link it from `docs/index.md`.

### Reports and Historical Snapshots

These documents represent point-in-time outputs (audits, health checks, status reports) and may not match the current code:
- `docs/reports/`
- `docs/health-reports/`
- `docs/archive/`

### Subproject Documentation

Some subprojects have their own documentation. Keep these consistent with canonical root/docs guidance when they describe shared infrastructure:
- `agents/**`
- `BROski-Community-Bot/**`
- `hyperstudio-platform/**`
- `hyper-mission-system/**`
- `docker/**`
- `k8s/**`
- `monitoring/**`

### How to Find Documentation Files

Common patterns:
- `README*.md` across the repo
- `docs/**/*.md`
- `**/*.md` for historical reports and notes

For synchronization work, prioritize canonical docs first, then update or clearly label anything else that might be mistaken for canonical guidance.

