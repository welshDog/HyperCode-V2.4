# Security Quick Wins — Verified Pins (2026-09-07)

> Baseline: `docs/health-reports/scout-baseline-2026-09-07.md` — 24 CRITICAL / 224 HIGH across 10 local images.
> Every fix below was verified against public CVE data before pinning.

---

## Fix Order (cheapest → deepest)

### 1. requirements.txt — dependency pins

```
gitpython>=3.1.59
mcp>=1.28.1,<2
```

- **gitpython 3.1.50 → 3.1.59** clears 1 CRITICAL + ~20 HIGH alone.
  - CVE-2026-78676 — CRITICAL RCE: dormant multi-line git-config values become live `core.hooksPath` hook execution on the next GitPython write. Real attack path for any agent that clones repos.
  - CVE-2026-78679 — arbitrary file read via `TagReference.create()`.
- **mcp 1.26.0 → 1.28.1** fixes CVE-2026-59950 — deprecated WebSocket transport accepted handshakes with no Host/Origin validation (cross-site WebSocket hijacking).
- ⚠️ **MUST cap `<2`** — MCP Python SDK v2 went stable 2026-07-28 with breaking changes (protocol rewrite, `MCPServer` rename, stateless sessions). A bare `>=1.28.1` will pull v2 and break the stack (same failure class as the Sept prod outage from mcp pinning).
- Also bump the one-version-behind list from the Scout report, then rebuild hypercode-core.

### 2. memstream/Dockerfile — ancient base

```
# BEFORE
FROM python:3.9-slim
# AFTER
FROM python:3.12-slim
```

One line, clears 3 CRITICAL / 26 HIGH.

### 3. Fleet rebuild cycle

Pull current bases, rebuild `--no-cache` on the next build cycle. Proof this works: `agent-mcp-bridge` rebuilt for the v5 bake scans at 0 CRITICAL / 2 HIGH — the 224 highs are mostly stale bases, not app code.

### 4. postgres/redis bases

Scout says `alpine:3.21` clears 3C/15H in one move — but decide first whether to jump straight to DHI (`dhi/postgres`, `dhi/redis`) instead of bumping twice. See `DHI_PILOT_CHECKLIST.md`.

---

## Watch Items (not blocking)

- **chromadb 1.0.15** — 2 unfixed criticals per Scout. Scout's "no fix available" can lag reality: recheck the latest chromadb release against the CVE IDs. Verify it is NOT reachable off the internal network. If unfixed: document as accepted-risk with a recheck date.
- **mcp WebSocket transport is deprecated** — plan migration to Streamable HTTP or stdio before any future SDK v2 jump.

---

## Sources

- https://nvd.nist.gov/vuln/detail/CVE-2026-59950
- https://www.sentinelone.com/vulnerability-database/cve-2026-78676/
- https://www.sentinelone.com/vulnerability-database/cve-2026-78679/
- https://docs.docker.com/scout/
