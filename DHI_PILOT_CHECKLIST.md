# DHI Pilot Checklist — First Image Migration (HyperCode-V2.4)

> Goal: prove the Docker Hardened Images (DHI) swap on ONE low-risk agent image, learn the gotchas, then roll out to hypercode-core + postgres + redis.
> DHI Community is free, Apache 2.0, 1000+ images — no cost, no lock-in.

---

## Why This First

- 40+ agent images on `python:3.12-slim`, `node:18`, `alpine:3.20` bases
- DHI = distroless → up to 95% less attack surface, near-zero CVEs
- Picking ONE throwaway image first = cheap failure, fast learning ⚡

---

## Phase 0 — Scout Baseline (5 min, zero risk)

Run BEFORE touching anything. These numbers are your before/after proof.

```bash
docker scout quickview hypercode-core:latest
docker scout quickview <pilot-agent-image>:latest
docker scout cves <pilot-agent-image>:latest
```

- [x] Baseline captured 2026-09-07 → `docs/health-reports/scout-baseline-2026-09-07.md` (24C/224H across 10 images)
- [ ] Record CVE counts (Critical / High) for pilot image

---

## Phase 1 — Pick the Pilot Image

Pick an agent that is:
- Stateless (no DB writes, no Redis pub/sub)
- Low traffic (not on the critical path)
- Simple Dockerfile (few `RUN` steps)

- [ ] Chosen pilot: `____________________`
- [ ] Read its Dockerfile top to bottom — flag every `RUN apk add`, `sh`, `curl`

---

## Phase 2 — The Swap + Gotcha Fixes

### The swap (one line)

```dockerfile
# BEFORE
FROM python:3.12-slim
# AFTER
FROM dhi/python:3.12-slim
```

### ⚠️ Gotcha List — check each one

| # | Gotcha | Symptom | Fix |
|---|---|---|---|
| 1 | **No shell** in runtime | `docker exec -it <c> sh` fails | Exec the binary directly: `docker exec -it <c> python -c "..."` |
| 2 | **No package manager** | `RUN apk add curl` fails at build | Multi-stage build: install tools in builder stage, COPY only artifacts |
| 3 | **Healthcheck uses curl/sh** | Container marked unhealthy | Use `CMD` array with the app's own binary, or `python -c "import urllib.request..."` |
| 4 | **ENTRYPOINT path differs** | `exec format error` / not found | Verify binary path — DHI images may differ from Debian slim; check `dhi` docs for the image |
| 5 | **Non-root user** | Permission denied on writes | DHI runs non-root by default — only write to volumes or `/tmp` |
| 6 | **Debugging without exec** | Can't poke around container | Use `docker logs`, `docker debug` (Docker Desktop), or add a debug profile variant |
| 7 | **COPY of system dirs** | Missing files at runtime | Distroless = minimal FS — vendor anything you need into the image explicitly |

### Build + test

- [ ] `docker build -t <pilot-image>:dhi-pilot ./agents/<pilot>/`
- [ ] Container starts and stays up
- [ ] Healthcheck passes
- [ ] Agent completes one normal task end-to-end
- [ ] `docker scout quickview <pilot-image>:dhi-pilot` — record new CVE count

---

## Phase 3 — Go/No-Go

- [ ] CVEs dropped (expect near-zero)
- [ ] No functional regressions
- [ ] Write 3-line lessons-learned in this file's Notes section

**If GO →** proceed to Phase 4. **If NO-GO →** note the blocker, pick next candidate.

---

## Phase 4 — Rollout Order (one image at a time)

1. `hypercode-core` — biggest CVE-scan win
2. `redis` — Sacred Rule: DB 1 = cache, DB 2 = rate limits. NEVER mix. Verify after swap.
3. `postgres` — verify volume data survives, run a migration dry-run
4. Remaining Python agents (batch of 5 at a time)
5. Node agents (`node:18` → DHI equivalent)

- [ ] After each: `docker scout quickview` + smoke test + `docker compose ps` all healthy
- [ ] Stripe webhook still rate-limit EXEMPT after redis swap (Sacred Rule)

---

## Definition of Done

- [ ] Pilot migrated + verified
- [ ] Core trio (core, redis, postgres) migrated + verified
- [ ] Before/after CVE table saved to `reports/`
- [ ] Entry added to WHATS_DONE.md — so no AI session ever suggests this again

---

## Notes / Lessons Learned

<!-- Fill in during the pilot — gotchas hit, fixes used, surprises -->

---

## Sources

- https://docs.docker.com/dhi/migration/
- https://www.docker.com/blog/docker-hardened-images-for-every-developer/
- https://docs.docker.com/scout/
