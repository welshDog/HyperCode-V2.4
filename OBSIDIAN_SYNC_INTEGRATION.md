# HyperAgent Loop → Obsidian Vault Integration

## Current State — ✅ LIVE & AUTONOMOUS (2026-06-07)

The crew → Obsidian-Brain vault-sync loop is wired, proven end-to-end, and
fully autonomous. Every `POST /execute` results in a PARA session note pushed
to the Brain vault on GitHub — **no manual step**.

| Piece | Status |
|---|---|
| `result_writer.py` write-only post-run hook in `main.py` | ✅ Live |
| `crew-orchestrator` mounts shared `./results` | ✅ Live (commit `27fdd6f`) |
| `obsidian-watcher` sidecar (auto-push on change) | ✅ Live (commits `67919bb`, `72e1038`) |
| Dead in-container trigger removed | ✅ Done (commit `9c4c2db`) |

---

## How It Works (current architecture)

```
1. POST /execute  (X-API-Key: $ORCHESTRATOR_API_KEY)
   ↓
2. crew-orchestrator runs the agents, collects results
   ↓
3. POST-RUN HOOK — result_writer.write_and_sync():
   └─ write_execution_results() -> ./results/latest-{summary.md,metrics.json,report.md}
      (write ONLY — returns {"sync_mode": "watcher"}; it does NOT push)
   ↓
4. obsidian-watcher sidecar (always running, profile: agents):
   ├─ polls ./results every WATCH_INTERVAL s (default 15, 3s debounce)
   ├─ on change: clones the vault fresh, builds a PARA session note,
   │  commits, and `git push` to origin/main
   └─ uses host ~/.ssh/id_ed25519 for GitHub SSH auth
   ↓
5. Your Obsidian vault is auto-updated on GitHub 🧠
```

> **Why a watcher, not an in-container trigger?** The crew-orchestrator
> container has no docker CLI/socket, so the old
> `docker compose run obsidian-sync` call from inside it could never work
> (always returned `sync_result:false`). The watcher decouples the loop — the
> orchestrator only writes files; the sidecar reacts and pushes. No
> docker-in-docker, no socket surface.

---

## Operating It

### Start (auto-starts with the agent stack)
The watcher is gated by `profiles: ["agents"]` and included in the root stack,
so it comes up with the crew:

```bash
docker compose --profile agents up -d        # crew-orchestrator + obsidian-watcher
docker ps --filter name=obsidian-watcher     # confirm it's running
docker logs obsidian-watcher --tail 5        # should show "Watching /results ..."
```

### Manual one-shot (ad-hoc sync without the watcher)
The one-shot service is gated by `profiles: ["vault-sync"]`; `run` ignores
profiles, so this still works any time:

```bash
docker compose -f docker-compose.obsidian-sync.yml run --rm obsidian-sync
# add -e DRY_RUN=true to clone + build the note WITHOUT pushing
```

### Tuning
| Env | Default | Meaning |
|---|---|---|
| `WATCH_INTERVAL` | `15` | watcher poll interval (seconds) |
| `DRY_RUN` | `false` | `true` = build note but skip `git push` |
| `VAULT_REPO` | BROski-Obsidian-Brain (SSH) | target vault |
| `DEFAULT_BRANCH` | `main` | vault branch |

---

## Verify End-to-End

```bash
# 1. Fire a test execution (zero LLM cost — agents run without an LLM key)
KEY=$(docker exec crew-orchestrator printenv ORCHESTRATOR_API_KEY)
curl -sS -X POST http://127.0.0.1:8081/execute \
  -H "Content-Type: application/json" -H "X-API-Key: $KEY" \
  -d '{"task":{"id":"test-sync-001","type":"feature","description":"verify vault sync","agents":["backend_specialist"],"requires_approval":false}}'
# Response includes:  "obsidian_sync": { "status":"success", "sync_mode":"watcher", ... }

# 2. Watcher auto-pushes within ~one interval
docker logs obsidian-watcher --tail 15 | grep -E "Change detected|Pushed"

# 3. Confirm the vault advanced on GitHub
git ls-remote git@github.com:welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne.git main
```

---

## Files

| File | Location | Role |
|---|---|---|
| `result_writer.py` | `agents/crew-orchestrator/` | write-only result serializer (`write_and_sync`) |
| `main.py` | `agents/crew-orchestrator/` | `/execute` post-run hook → `write_and_sync` |
| `obsidian-sync.sh` | `scripts/` | sync logic + `WATCH_MODE` watcher loop |
| `docker-compose.obsidian-sync.yml` | root | `obsidian-watcher` (profile agents) + `obsidian-sync` one-shot (profile vault-sync) |
| `docker-compose.yml` | root | includes obsidian-sync.yml |

---

## Rollback / Disable

- **Pause auto-push:** `docker stop obsidian-watcher` (results still get written; just not pushed).
- **Dry-run a sync:** run the one-shot with `-e DRY_RUN=true`.
- **Fully detach:** remove `obsidian-watcher` from the `agents` profile (or stop it); the orchestrator keeps writing `./results` harmlessly.

---

**BROski♾️ — The nervous system is connected and self-driving. 🧠🔥**
