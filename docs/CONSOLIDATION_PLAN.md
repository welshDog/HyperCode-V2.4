# HyperCode Docs Consolidation Plan

> **Goal:** One living truth per category. No more hunting across 160+ files to find the current status.
> **Principle:** Keep what's alive. Archive what's historical. Never delete real content — just move it where it belongs.

## The core problem

`docs/` has 160+ files. The sprawl hotspots, sampled from the live listing:

| Category | Files found | What they all claim to be |
|---|---:|---|
| Session / handover reports | 15 | "the latest session status" |
| Audit / code review reports | 13 | "the real audit" |
| Delivery / phase / "complete" reports | 13 | "what shipped" |
| Health / status reports | 10 | "current system health" |
| Roadmap / future / vision | 8 | "where we're going" |
| Documentation indices | 5 | "the index of all docs" |

When you have 15 files all claiming to be "the latest handover," none of them is. For an ADHD brain, that's a cognitive-load tax every single session.

## Target structure

Keep **5 living canonical docs** at the top of `docs/`. Everything else moves into dated archive folders. Nothing is deleted.

```text
docs/
├── INDEX.md                  ← ONE entry point (replaces DOCUMENTATION_INDEX, DOCUMENTATION_INVENTORY, DOCS_SYNC_CHECKLIST)
├── STATUS.md                 ← ONE living status (replaces 10 health variants)
├── ROADMAP.md                ← ONE living roadmap (replaces 8 future/vision variants)
├── SESSION.md                ← ONE living handover (replaces 15 session variants)
├── AUDIT.md                  ← ONE living audit/security summary (replaces 13 audit variants)
├── RESEARCH.md               ← ONE index of docs/research/ (NEW — lives next to the others)
├── guides/                   ← KEEP — real reference guides
├── runbooks/                 ← KEEP — real runbooks
├── architecture/            ← KEEP — real architecture docs
├── mcp/                     ← KEEP — real MCP docs
├── observability/           ← KEEP — real observability docs
├── research/                 ← KEEP — research reports (AgentDojo spec, protocol stack report)
├── agents/                   ← KEEP — real agent docs
├── api/                      ← KEEP — real API docs
├── deployment/              ← KEEP — real deployment docs
├── security/                 ← KEEP — real security docs
└── archive/                  ← ALL historical snapshots land here
    ├── sessions/             ← 15 session/handover files
    ├── audits/               ← 13 audit/code-review files
    ├── delivery/             ← 13 phase/"complete" files
    ├── health/               ← 10 health/status snapshot files
    ├── roadmap/              ← 8 superseded roadmap variants
    └── indices/              ← 5 superseded index files
```

## Consolidation rules

1. **Newest dated file in each category becomes the seed for the living doc.** The rest archive.
2. **Root-level duplicates** (`HYPERCODE_V3_ROADMAP.md`, `STATUS_REPORT.md`, `HEALTH_CHECK_*.md`, `NEXT_SESSION_HANDOVER_*.md`) — root copies archive into `docs/archive/`, canonical lives in `docs/`.
3. **"FINAL_" / "ULTIMATE_" / "COMPLETE_" prefixed files are almost always snapshots** — they archive unless they're still the newest truth.
4. **Throttle-agent code review (4 files) collapses into the living `AUDIT.md`** with a pointer to the archived full reports.
5. **Living docs get a `Last Updated:` line and a `Supersedes:` note** so future-you knows which archives fed it.
6. **Never delete.** `git mv` everything to `archive/`. History is preserved by git; cognitive load is reduced by location.

## File-by-file decisions

### Roadmaps → merge into `docs/ROADMAP.md`

| File | Decision |
|---|---|
| `ROADMAP.md` | **SEED** — make this the living roadmap |
| `AI_EVOLUTION_ROADMAP_2025-2027.md` | archive → `archive/roadmap/` |
| `HYPERCODE_AGENTIC_EVOLUTION_ROADMAP_2026.md` | archive |
| `HYPERCODE_FUTURE_VISION.md` | merge vision into ROADMAP intro, archive file |
| `FINAL_STATUS_AND_ROADMAP.md` | archive |
| `NEXT_MOVES.md` / `NEXT_TASKS.md` | merge open tasks into ROADMAP "Next" section, archive |
| `PRODUCTION_UPGRADE_ROADMAP.md` | archive |
| root `HYPERCODE_V3_ROADMAP.md` | **KEEP at root** — it's the project's headline roadmap we just updated; link it from `docs/ROADMAP.md` |

### Status → merge into `docs/STATUS.md`

| File | Decision |
|---|---|
| `STATUS.md` | **SEED** — make this the living status |
| `STATUS_REPORT.md` (docs) + root copy | keep one, archive the other |
| `PROJECT_HEALTH_AND_UPGRADES.md` | merge upgrade notes into STATUS, archive |
| `PROJECT_HEALTH_REPORT.md` / `PROJECT_HEALTH_STATUS.md` | archive (older snapshots) |
| `health_assessment_report.md` / `comprehensive-health-check.md` | archive |
| `final-system-status-report.md` | archive |
| `ULTIMATE_HEALTH_REPORT_2026-04-01.md` | archive (April snapshot) |
| `HEALTH_CHECK_2026-06-03.md` | archive (June snapshot) |
| root `HEALTH_CHECK_*.md` files | archive |

### Sessions → merge into `docs/SESSION.md`

| File | Decision |
|---|---|
| `NEXT_SESSION_HANDOVER_2026-08-24.md` | **SEED** — newest, becomes the living handover |
| All other `NEXT_SESSION_HANDOVER_*.md` (12 files) | archive → `archive/sessions/` |
| `FINAL_SESSION_HANDOVER_2026-06-03.md` | archive |
| `SESSION_REPORT_2026-05-*.md` (3 files) | archive |
| `SESSION_SNAPSHOT_2026-06-*.md` (2 files) | archive |

> Rule: after each session, **edit `docs/SESSION.md` in place**. Don't create `NEXT_SESSION_HANDOVER_2026-08-27.md`. The old session's content moves to `archive/sessions/` in the same commit.

### Audits → merge into `docs/AUDIT.md`

| File | Decision |
|---|---|
| `security_threat_model.md` | **SEED** — make this the living security/audit summary |
| `SECURITY_AUDIT_REPORT.md` | merge summary, archive |
| `ULTIMATE_AUDIT_REPORT.md` | archive |
| `AUDIT_ADDENDUM_V2.md` | archive |
| `codebase-audit-report.md` | archive |
| `DOC_AUDIT_REPORT.md` | archive |
| `THROTTLE_AGENT_CODE_REVIEW*.md` (7 files) | archive all; one-line pointer in AUDIT.md |

### Delivery / "complete" → archive

All 13 are point-in-time snapshots. They don't merge — they're history.

| File | Decision |
|---|---|
| `FINAL_IMPLEMENTATION_SUMMARY.md` | archive → `archive/delivery/` |
| `FINAL_VALIDATION_REPORT_2026-04-01.md` | archive |
| `DELIVERY_SUMMARY.md` | archive |
| `PHASE_2_COMPLETE.md` / `PHASE_2_INTEGRATION.md` / `PHASE_BROSKI_INTEGRATION.md` | archive |
| `TASKS_COMPLETE_2026-06-03.md` | archive |
| `COOLING_COMPLETE_REPORT.md` | archive |
| `AUTO_FIXES_APPLIED.md` / `BLOCKERS_FIXED.md` | archive |
| `GAP_ANALYSIS_AND_ACTION_PLAN.md` / `ASSESSMENT_AND_PLAN.md` | archive |
| `WOW_FACTOR_SESSION_2026-06-04.md` | archive (celebration history) |

### Indices → collapse into `docs/INDEX.md`

| File | Decision |
|---|---|
| `INDEX.md` | **SEED** — the single living entry point |
| `DOCUMENTATION_INDEX.md` | merge, archive |
| `DOCUMENTATION_INVENTORY.md` | merge, archive |
| `DOCS_SYNC_CHECKLIST.md` | archive |
| `docs/README.md` | keep as the folder README, link from INDEX |

### Tech debt / ops → keep + trim

| File | Decision |
|---|---|
| `TECH_DEBT.md` | **KEEP** living — update in place |
| `technical_debt_closure_report.md` | archive |
| `TROUBLESHOOTING.md` / `RUNBOOK.md` | **KEEP** — real reference |
| `DEPLOYMENT_CONTAINER_FAILURES.md` | archive (incident record) |

### Everything not sampled (guides, API, architecture, MCP, observability)

**KEEP as-is.** These are real reference docs, not snapshots. The sprawl is in the report/snapshot categories only.

## Execution order (ADHD-friendly chunks)

Do one chunk per session. Commit after each. Never batch all at once.

### Chunk 1 — Sessions (biggest win, smallest risk)

```bash
mkdir -p docs/archive/sessions
git mv docs/SESSION_REPORT_*.md docs/archive/sessions/
git mv docs/SESSION_SNAPSHOT_*.md docs/archive/sessions/
git mv docs/FINAL_SESSION_HANDOVER_2026-06-03.md docs/archive/sessions/
# Keep newest handover as the seed
cp docs/NEXT_SESSION_HANDOVER_2026-08-24.md docs/SESSION.md
git mv docs/NEXT_SESSION_HANDOVER_2026-08-2*.md docs/archive/sessions/
git mv docs/NEXT_SESSION_HANDOVER_2026-08-23*.md docs/archive/sessions/
git mv docs/NEXT_SESSION_HANDOVER_2026-0[56]*.md docs/archive/sessions/
git add -A && git commit -m "docs: consolidate 15 session files into single living SESSION.md"
```

### Chunk 2 — Delivery + audit reports

```bash
mkdir -p docs/archive/delivery docs/archive/audits
git mv docs/FINAL_*.md docs/PHASE_*.md docs/TASKS_COMPLETE_*.md \
       docs/COOLING_COMPLETE_REPORT.md docs/AUTO_FIXES_APPLIED.md \
       docs/BLOCKERS_FIXED.md docs/GAP_ANALYSIS_AND_ACTION_PLAN.md \
       docs/ASSESSMENT_AND_PLAN.md docs/DELIVERY_SUMMARY.md \
       docs/WOW_FACTOR_SESSION_*.md docs/archive/delivery/
git mv docs/THROTTLE_AGENT_*.md docs/archive/audits/
git mv docs/AUDIT_ADDENDUM_V2.md docs/ULTIMATE_AUDIT_REPORT.md \
       docs/codebase-audit-report.md docs/DOC_AUDIT_REPORT.md \
       docs/SECURITY_AUDIT_REPORT.md docs/archive/audits/
git add -A && git commit -m "docs: archive 26 delivery + audit snapshot reports"
```

### Chunk 3 — Health + roadmap variants

```bash
mkdir -p docs/archive/health docs/archive/roadmap
git mv docs/PROJECT_HEALTH_*.md docs/health_assessment_report.md \
       docs/comprehensive-health-check.md docs/final-system-status-report.md \
       docs/ULTIMATE_HEALTH_REPORT_*.md docs/HEALTH_CHECK_*.md \
       docs/archive/health/
git mv docs/AI_EVOLUTION_ROADMAP_*.md docs/HYPERCODE_AGENTIC_EVOLUTION_*.md \
       docs/FINAL_STATUS_AND_ROADMAP.md docs/PRODUCTION_UPGRADE_ROADMAP.md \
       docs/HYPERCODE_FUTURE_VISION.md docs/NEXT_MOVES.md docs/NEXT_TASKS.md \
       docs/archive/roadmap/
git add -A && git commit -m "docs: archive 18 health + superseded roadmap snapshots"
```

### Chunk 4 — Indices + write the canonical 5

Write the 5 living canonical docs (`INDEX.md`, `STATUS.md`, `ROADMAP.md`, `SESSION.md`, `AUDIT.md`) by pulling the newest content from their seeds. Add a `Last Updated:` and `Supersedes:` line to each.

```bash
git add -A && git commit -m "docs: publish 5 living canonical docs + archive 5 superseded indices"
```

## Guardrails

- **Never `git rm`.** Only `git mv`. Content is never lost — just relocated.
- **One category per commit.** If a chunk goes wrong, revert one commit, not all.
- **Update links.** After moving, grep for broken links and fix in the same commit.
- **Run the CI lint.** The repo has markdownlint — let it catch link rot.
- **Keep root `HYPERCODE_V3_ROADMAP.md` and `WHATS_DONE.md`** — they're the project's headline docs, not part of the sprawl.

## What this unlocks

- One file to read for status. One for roadmap. One for "where did we leave off."
- `docs/INDEX.md` becomes the actual front door, not a 15th index.
- Future sessions stop creating `NEXT_SESSION_HANDOVER_<date>.md` — they edit `docs/SESSION.md` and archive the previous content.
- Your ADHD brain finds the truth in one place, every time.

> 🐶♾️ Less hunting. More building. The docs finally serve your brain instead of taxing it.
