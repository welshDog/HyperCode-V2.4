# Agent API keys from secret files (`*_FILE`)

**Goal:** no agent needs an API key in `.env` or in a container's `environment:` block. Each reads it from a
Compose secret file, the same convention core already uses.

## How it works

Every agent file that reads an inter-agent / core key calls `read_secret("NAME")`:

1. `NAME_FILE` set, readable and non-empty -> that file's contents (stripped, BOM removed);
2. else the `NAME` environment variable;
3. else `""`.

**Until a `*_FILE` variable is actually set this behaves exactly like `os.getenv`**, so merging the code changes
nothing in a running stack. The file is re-read on every call, so a rotated secret needs no restart for agents that
read per call.

Agents ship as isolated images, so the function is *vendored* (copied verbatim) between marker comments:

```
agents/shared/secret_env.py          <- the ONLY place to edit
scripts/vendor_secret_env.py         <- copies it into every target file (TARGETS list)
python scripts/vendor_secret_env.py          # refresh the copies
python scripts/vendor_secret_env.py --check  # CI: fail if any copy drifted
```

`.github/scripts/tests/test_agent_secret_env_sync.py` also fails if a raw `os.getenv("HYPERCODE_API_KEY"|"AGENT_API_KEY"|
"API_KEY"|"CORE_AGENT_KEY")` read is reintroduced (a short allow-list with reasons covers the few already
file-aware sites). CI lane: `.github/workflows/secret-env-sync.yml`.

## Adopting it for an agent (deployment step, not part of the code change)

1. Put the key in a file under `secrets/` (gitignored) and declare it in `docker-compose.secrets.yml`.
2. In that agent's overlay block set `HYPERCODE_API_KEY_FILE: /run/secrets/<name>` (or `API_KEY_FILE`,
   `CORE_AGENT_KEY_FILE`, ... whichever variable the agent reads) and list the secret under `secrets:`.
3. Remove the matching value from `.env` / `environment:` once it is verified.
4. Launch with the overlay: `hyperlaunch.ps1`, or for the agents launched from `agents-full.yml`:
   `-f docker-compose.yml -f docker-compose.agents-full.yml -f docker-compose.secrets.yml --profile agents --profile hyper`.

Per-agent identities (`agent_api_keys` table, header `X-Agent-Key`) are minted with
`python scripts/mint_agent_keys.py <agent> | docker exec -i postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'`.
It rotates only the named agent; `--all` is required to rotate every agent (no arguments is refused).

## The shared inter-agent key (read before recreating any agent)

`crew-orchestrator`, `coder-agent`, `qa-engineer`, `safety-shepherd`, `coder-studio`, `evolve-relay` and `governor` use
one shared value as `HYPERCODE_API_KEY` / `API_KEY`: callers send it, receivers check it. Compose supplies it as
`${API_KEY:-dev-master-key}`, so **recreating one of them from a shell without `API_KEY` silently switches it to
`dev-master-key` and its calls to the others get 401.** Check peers with
`curl -H "X-API-Key: $HYPERCODE_API_KEY" http://<agent>:<port>/__authprobe` from inside the container
(404 = accepted, 401 = rejected). The fix is to move ALL holders to one new secret file in a single coordinated
recreate; that rollout is not part of this code change.

Check all seven at once, read-only, with `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\probe_inter_agent_key.ps1`
(it sends each holder's own key to every peer and never prints a key). A `?` after a code means that peer also answered 404 to a
deliberately wrong key, i.e. it does not enforce the key on `/__authprobe`; on 2026-10-16 only `coder-agent`, `qa-engineer`,
`safety-shepherd` and `evolve-relay` enforce it there, so the probe proves nothing for `crew-orchestrator`, `coder-studio`, `governor`.


Also: `agent-registry` auto-restarts any watched container it sees die (exit 137 after a stop or recreate), so expect
a second start ~13 s after a manual recreate.

**Rolled out 2026-10-16.** All seven now use `secrets/inter_agent_key.txt` (gitignored; the previous key is kept in
`secrets/inter_agent_key.old.txt` for rollback). `crew-orchestrator`, `coder-agent`, `safety-shepherd` and `governor` read it as a
file (`HYPERCODE_API_KEY_FILE` / `API_KEY_FILE` in `docker-compose.secrets.yml`); `qa-engineer`, `coder-studio` and
`evolve-relay` have no `read_secret` yet and get it as an env value. To change it again, or to recreate any of the seven
safely, use `scriptsollout_inter_agent_key.ps1` (dry run by default, `-Apply` to change; it recreates all seven with their
own compose file sets, diffs env names, then runs the probe). Recreating one of the three env-fed agents by hand without the
key in `API_KEY` still falls back to `dev-master-key`.

**healer-agent (2026-10-17):** its inbound routes were protected by the public default `dev-master-key`. It now takes the shared key as an env value (its image predates `read_secret`, so the overlay's `HYPERCODE_API_KEY_FILE` only takes effect after a rebuild). `/health`, `/metrics` and `/alerts/webhook` stay open by design. No caller was sending a key to its protected routes, so nothing regressed.

**All nine on the file (2026-10-17).** `healer-agent` (rebuilt), `throttle-agent` (rebuilt; now also sends the key on its healer calls), `evolve-relay` (rebuilt from BROskiPets-LLM-dNFT PR #3), `qa-engineer` and `coder-studio` (already file-aware) join the first four. `scriptsollout_inter_agent_key.ps1` therefore no longer puts the key in any env value by default (`-PassKeyAsEnv` is the rollback switch) and prints whether each container carries a `*_API_KEY_FILE`. `throttle-agent` is started from `docker-compose.throttle.yml` (its own `secrets:` block), so recreate it with `docker compose -f docker-compose.yml up -d --no-deps --force-recreate throttle-agent`. Rebuilding `evolve-relay` needs the BROskiPets checkout (`BROSKIPETS_DIR`) on a branch that has PR #3, otherwise the image loses file support.
