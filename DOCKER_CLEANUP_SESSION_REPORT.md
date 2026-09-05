# Docker System Health & Cleanup — Full Session Report
**Date:** 2026-09-05
**Machine:** Windows Docker Desktop (WSL2 backend)
**Scope:** HyperCode-V2.4 dev box — 48-container core stack + agents
**Prepared for:** Claude Code session handover

---

## 1. Executive Summary

- Recovered **~46.4GB disk** (total usage 66GB → 19.6GB, −70%)
- Fixed a **corrupted overlay2 RW layer** that was blocking all Docker operations
- **All volumes preserved** — no data loss. Postgres, Redis (DB 0/1/2) intact
- 37 containers running healthy post-cleanup (was 38 running + 45 exited + 14 never-started)
- Root cause of corruption traced to container `bf21b343167b` (hypercode-ollama:0.3.14, OOM-killed ~2 days prior)

---

## 2. Timeline of Events

| Step | Action | Result |
|---|---|---|
| 1 | Full health report taken | 83 containers, 45 exited (mostly 137), 100 images (80 unused), 45GB images, 34GB build cache |
| 2 | Cleanup planned; `docker system prune -a --volumes` recommended but **rejected as too risky** | Safer ladder agreed instead |
| 3 | `docker rm -f bf21b343167b` (targeted force-remove of corrupted container) | **Success** — dangling overlay2 reference cleared; Docker auto-recovered 45 orphaned containers + 37 unused images |
| 4 | `docker builder prune` | 13.5GB freed (18.46GB → 4.978GB) |
| 5 | Ollama duplicate removal | `ollama/ollama:0.3.14` untagged (~4.9GB); **status of `:latest` needs verification** (see §5) |
| 6 | `docker container prune` | No-op — all exited containers already cleared during layer recovery |
| 7 | Redis integrity check | DB 0: 107 keys, DB 1 (cache): 482 keys, DB 2 (rate limits): 0 keys — all accessible, no loss |
| 8 | Prevention files created | 6 files: strategy docs, cleanup scripts (bash + PowerShell), cron template, memory-limits compose overlay |

---

## 3. Root Cause

- Container `bf21b343167b` (hypercode-ollama:0.3.14) was killed ~2 days ago (exit 137)
- Its RW layer snapshot was **not cleaned up properly** on kill, leaving a dangling reference in overlay2 metadata
- The dangling reference **blocked all Docker commands that enumerate containers**
- Fix: targeted `docker rm -f` on the specific container ID. No metadata surgery, no factory reset, no `--volumes` flag used.

---

## 4. Exit-137 Analysis — CAVEAT: Evidence Is Gone

- ~45 exited containers, mostly exit code 137 (SIGKILL), from ~2 days ago
- One pre-deletion check reportedly returned `OOMKilled=false` on 23 of them (suggesting orchestration shutdown, not cgroup OOM)
- **The report contradicts itself**: it also claims the containers "no longer exist and can't be retrospectively inspected." If the containers were removed before inspection, the `OOMKilled=false` finding is unverified.
- **Current conclusion is provisional**: exit-137s were probably orchestration/CI shutdowns, not memory leaks — but this is NOT confirmed
- **Reopen the investigation if any new exit-137 containers appear** in the next 1–2 weeks

---

## 5. Outstanding Items — VERIFY BEFORE CLOSING THIS OUT

### 5.1 Ollama image status (verify FIRST)
The report says "No ollama image in the output (already removed when we untagged it earlier)" — which may mean **both** ollama images are gone, including `:latest` (8GB). If the stack expects to start ollama, it will trigger a full re-pull.
```powershell
docker images | grep ollama
```

### 5.2 Orphaned volumes (9 of them)
In-use volumes went from 17 → 8 (of 30 total). The removed containers left dangling volumes. Ollama volumes typically hold **downloaded models — potentially several GB**.
```powershell
docker volume ls -f dangling=true
```
Check contents before ever pruning. **Never add `--volumes` to any prune command.**

### 5.3 OOM watch
Monitor agent restarts for 1–2 weeks. Any new exit-137 = the memory question reopens.

### 5.4 Quick health verification
```powershell
docker ps --format "{{.Names}}: {{.Status}}"
docker system df
```

---

## 6. Data Integrity — CONFIRMED SAFE

| System | Status |
|---|---|
| Postgres volumes | Preserved (2.246GB safe) |
| Redis DB 0 (default) | 107 keys, intact |
| Redis DB 1 (cache) | 482 keys, intact — Sacred Rule: DB 1 = cache only |
| Redis DB 2 (rate limits) | Accessible, 0 keys — Sacred Rule: DB 2 = rate limits only, never mix |
| All 30 volumes | Preserved, untouched |

**Uptime note:** Redis reported "Up 2 hours" during the check — consistent with a Docker restart during the layer fix, not a data event.

---

## 7. Prevention Strategy (Files Created)

| File | Purpose |
|---|---|
| `DOCKER_CLEANUP_STRATEGY.md` | Comprehensive guide — scheduling options, memory tiers, root cause |
| `DOCKER_CLEANUP_QUICK_START.md` | Implementation checklist, troubleshooting |
| `scripts/docker-cleanup.sh` | Linux/macOS automation (colored output, logging) |
| `scripts/docker-cleanup.ps1` | Windows automation (Task Scheduler compatible) |
| `cron-setup.txt` | Ready-to-paste cron jobs |
| `docker-compose.memory-limits.yml` | Memory limits overlay for all 40+ agents |

### Memory limit tiers
| Tier | Limit | Count | Examples |
|---|---|---|---|
| Lightweight | 256M | 6 agents | github-sync, evolve-relay, watchers |
| Standard | 512M | 25+ agents | coder-agent, crew-orchestrator, specialists |
| Heavy | 1GB | 5 agents | meta-research-architect, brain-agent, agent-x |
| Data-Intensive | 1.5GB | 3 agents | hyper-brain, hyper-architect, hyper-brain-core |

**Rollout guidance:** Deploy gradually — rolling out all limits at once to previously-unbounded agents risks manufacturing new OOM kills. Do the Lightweight tier first, observe a few days, then continue. If ollama returns, give it Data-Intensive or better.

### Scheduled cleanup
- **Weekly (Sun 02:00 UTC):** `docker image prune -a` then `docker container prune`
- **Monthly (1st, 02:30 UTC):** `docker builder prune` (expect ~13.5GB/month)
- ~~Quarterly `docker system prune`~~ — **recommend removing this from the schedule**; it's the blunt command that caused risk framing in the first place. Note: weekly `image prune -a` deletes images of anything stopped between Sundays (forces re-pull). Acceptable if intentional.

### Hard rules going forward
- NEVER use `--volumes` on prune commands
- NEVER use Docker Desktop "Clean / Purge data" (factory reset — destroys everything)
- Investigate OOM evidence BEFORE pruning stopped containers
- Always capture before/after numbers (`docker system df`)

---

## 8. Related Repo Work (same session, HyperCode-V2.4)

- **PR #453** (Governor + Capability Tokens, Phase 2): docstring work complete — 131/131 = **100% source coverage** (commit `3d36ec0d`), 97/97 governor tests green. CodeRabbit official re-review was **rate-limited** ("next included review available in 44 minutes" as of ~18:38 UTC; the `@coderabbitai review` command bounced). Stale official number on the PR is 50.94% (267 functions incl. ~150 test functions, which deliberately have no docstrings). **Decision pending:** exclude tests from the docstring gate via `.coderabbit.yaml`, or stub test docstrings.
- **Other open PRs pending tidy-up:** ~21 Dependabot bumps (uvicorn/fastapi/pydantic/structlog/stripe 11→15 major), PR #452 (unpinned npx MCP packages with credentials — pin before merge), PR #448 (🔴 broken — StudioView implementation removed), PR #450 (draft, Kimi K3 stubs).
