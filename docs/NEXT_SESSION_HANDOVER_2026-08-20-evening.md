# 🏁 Session Handover — 2026-08-20 (evening) · "Verify, Don't Trust the Grep"

> Continues directly from `NEXT_SESSION_HANDOVER_2026-08-20.md` (the morning
> fleet-reconciliation + health + playtest session). That session found "3 port
> collisions" in `docker-compose.agents-full.yml` via grep and logged them in
> `docs/NEXT_TASKS.md` P2-2. This session verified them with `docker compose
> config` instead of trusting the earlier grep-based count — and found the real
> picture was both fixable-tonight and bigger than expected.

---

## ⚡ TL;DR

Fixed the 3 real port collisions (confirmed against live containers, not just
other compose files) and deleted a phantom `hypercode-mcp-server` ghost block
that was silently corrupting the real service's build context on merge. Along
the way, found the documented fleet-launch command has never actually worked
(missing `--profile agents`), a 4th port collision the morning session missed
(`tips-tricks-writer` vs live `chroma`), and — the important one — **14 of the
25 agent names in `agents-full.yml` are also defined in `docker-compose.agents.yml`
with different build contexts, ports, or profiles.** Same-named services merge
silently across compose files instead of erroring. This means "launch the
25-agent fleet" has likely never deployed the roster the docs describe for most
of these agents. That's an architecture decision, not a port fix — it's now
`NEXT_TASKS.md` item #0, and it needs Bro's call before anyone attempts the
full-fleet launch again. Commit: `e9638019`, pushed clean (evo gate 26/26).

## ✅ What shipped this session

- **Deleted the `hypercode-mcp-server` ghost block** from `docker-compose.agents-full.yml`
  — its `context: ./agents/hypercode-mcp-server` never existed. It wasn't a 25th
  agent needing a rename (as P1-2 assumed); it was a phantom duplicate of the
  already-live `:8823` service, and merging it silently swapped the real
  service's build context to the nonexistent path plus double-bound the host port.
- **3 real port collisions fixed**, each verified against a live `docker ps`
  container, not just another compose file: `system-architect` 8008→8010 (was
  colliding with `healer-agent`), `hyper-split-agent` 8096→8013 (`safety-shepherd`),
  `session-snapshot` 8097→8017 (`evolve-relay`, `--profile pets`).
- **Fixed the launch command itself** — `docker compose -f docker-compose.yml -f
  docker-compose.agents-full.yml up -d` (as documented in `CLAUDE.md`) has never
  worked: `crew-orchestrator` carries `profiles: ["agents"]` from
  `docker-compose.agents.yml`, and without `--profile agents` on the command it
  silently drops out of the merge, breaking every agent's `depends_on`. Fixed in
  `CLAUDE.md` and the compose file's own header comment.
- **Synced the ports into everything that referenced them**: `scripts/fleet-roster-check.sh`
  (re-ran it after editing — clean exit 0, 24-entry roster now that the phantom
  is gone) and `.github/workflows/health-check.yml`'s `EXPECTED_PORTS` dict.
- **Left 2 deliberately unfixed and documented why**: `tips-tricks-writer` (:8009)
  vs live `chroma` — new finding, not in the original list — and `test-agent`
  (:8100) vs live `hyper-brain`, which is entangled with the item-#0 architecture
  question below, so a port move alone might not be the right fix.

## 🧭 The big one — see `NEXT_TASKS.md` item #0

Ran `comm -12` between the service names in `agents-full.yml` and every file
`docker-compose.yml` actually `include:`s (`core`, `observability`, `agents`,
`obsidian-sync`, `bropets`, `brain`, `grafana-cloud`). **14 real agent names
overlap** (plus 3 shared network names, which are fine/intentional):
`agent-x`, `backend-specialist`, `coder-agent`, `crew-orchestrator`,
`database-architect`, `devops-engineer`, `frontend-specialist`, `goal-keeper`,
`hyper-architect`, `hypercode-mcp-server`, `hyper-observer`, `hyper-worker`,
`project-strategist`, `qa-engineer`.

Proved this is a real problem on two of them, not theoretical:
- `hypercode-mcp-server` — already covered above.
- `hyper-architect` — `docker-compose.agents.yml` defines a *second*
  `hyper-architect` with `profiles: ["hyper"]` and a completely different build
  path (`agents/hyper-agents/architect/Dockerfile` vs `agents-full.yml`'s
  `./agents/architect`). Since `--profile agents` doesn't include `hyper`, this
  merged service vanishes from `docker compose config` entirely — a second,
  independent instance of the exact same profile-drop bug that broke
  `crew-orchestrator`.

**This wasn't fixed tonight, on purpose.** Renumbering 14 agents' ports/contexts
without knowing which definition is supposed to be authoritative would very
likely paper over a wrong-image-gets-deployed bug rather than fix it. That's a
decision for Bro: rename one side's agents, formally retire the older
`docker-compose.agents.yml` definitions in favor of `agents-full.yml` (or vice
versa), or make the profile gating mutually exclusive on purpose.

## 🪤 Also found, flagged, not fixed (see `NEXT_TASKS.md` #5–#8)

| Finding | Where |
|---|---|
| `docs/STATUS.md`'s "Agent Fleet — 25 Total" table is stale (predates the reconciliation, still shows e.g. `crew-orchestrator :8010`) | flagged with a banner in place |
| `ghost-agents-build.yml`'s build matrix `context:` paths are wrong for most/all of its 12 entries (point at nonexistent directories) | not touched — separate, bigger problem |
| `ghost-agents-build.yml`'s `port-check` job regex isn't anchored — matches garbage substrings on `"127.0.0.1:X:Y"` port strings, has likely never caught a real collision | not touched |
| `health-check.yml`'s `EXPECTED_PORTS` gate's own port parser (`str(p).split(':')[0].split('127.0.0.1:')[-1]`) yields the literal string `'127.0.0.1'` on any real port entry — verified in isolation. **Pre-existing, not caused by tonight's dict edit** — the gate has probably always failed regardless of what the dict says. | not touched |
| `business-agent` still has no Dockerfile anywhere sensible | unchanged, still needs a human decision (P2-1) |

## 🔑 Key facts (don't re-derive)

| Thing | Value |
|---|---|
| Full-fleet launch command | now `docker compose --profile agents -f docker-compose.yml -f docker-compose.agents-full.yml up -d` — the `--profile agents` flag is not optional |
| New ports | `system-architect :8010`, `hyper-split-agent :8013`, `session-snapshot :8017` |
| `hypercode-mcp-server` | the real one lives in `docker-compose.agents.yml` at `:8823` — it is NOT a ghost agent, don't re-add it to `agents-full.yml` |
| Still-open collisions | `tips-tricks-writer` (:8009) vs `chroma`; `test-agent` (:8100) vs `hyper-brain` |
| Evidence for item #0 | `comm -12 <(grep service names from agents-full.yml) <(grep from core/observability/agents/obsidian-sync/bropets/brain/grafana-cloud)` — re-run this before assuming it's stale |
| This session's commit | `e9638019` on `HyperCode-V2.4`, evo gate 26/26 before push |

---

> 🐶♾️ *"The morning session found 3 collisions with grep. Verifying with the real merge found 2 more, a phantom agent, a broken launch flag, and 14 unaudited name collisions underneath all of it. Grep tells you what's there — `docker compose config` tells you what actually happens."*
