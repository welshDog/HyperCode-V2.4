# Hyper Brain Docker Stack Integration — Design

## Goal
Make the Hyper Brain service come up automatically with the HyperCode-V2.4 stack so the web Command Center at `http://localhost:8100/ui` is always available after `docker compose up -d`.

Keep `github-sync` optional behind `--profile brain`.

## Context
HyperCode-V2.4 includes `docker-compose.brain.yml`, but the current `hyper-brain` service is misconfigured:
- `dockerfile: Dockerfile` points to a file that does not exist in the Brain repo (canonical is `Dockerfile.hyper-brain`)
- The volume mapping is incorrect and results in the container seeing a non-existent vault path, causing watchdog startup failure

## Scope
### In scope
- Fix HyperCode-V2.4 `docker-compose.brain.yml` so:
  - `hyper-brain` starts by default (no profile gate)
  - Vault is mounted correctly to `/vault`
  - `OBSIDIAN_VAULT_PATH` inside container is `/vault`
  - Build uses the correct dockerfile (`Dockerfile.hyper-brain`)
- Keep `github-sync` behind `profiles: ["brain"]`
- Add a `.dockerignore` to the Brain repo to prevent shipping the entire vault + `.obsidian` as Docker build context

### Out of scope
- Webhook hardening
- SSE events
- Any new ports, proxies, or UI changes

## Desired Runtime Contract
- Host:
  - `OBSIDIAN_VAULT_PATH` points to the vault root folder on the host
    - default: `H:/BROski-Obsidian-Brain-for-HyperFocus-z0ne/HYPERFOCUS_ZONE`
- Container:
  - Vault bind-mounted to `/vault`
  - Hyper Brain reads `OBSIDIAN_VAULT_PATH=/vault`

## Compose Changes
File: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.brain.yml`

### hyper-brain (default-on)
- Remove: `profiles: ["brain"]`
- Build:
  - `context: ../BROski-Obsidian-Brain-for-HyperFocus-z0ne`
  - `dockerfile: Dockerfile.hyper-brain`
- Environment:
  - `OBSIDIAN_VAULT_PATH=/vault`
  - keep existing `REDIS_URL`, `MCP_PORT`, `GITHUB_*` passthroughs
- Volumes:
  - `- ${OBSIDIAN_VAULT_PATH:-H:/BROski-Obsidian-Brain-for-HyperFocus-z0ne/HYPERFOCUS_ZONE}:/vault`
- Networks:
  - unchanged (`agents-net`, `data-net`)

### github-sync (still optional)
- Keep: `profiles: ["brain"]`
- Use the same vault bind mount to `/vault`

## Brain Repo Docker Build Context
Add `.dockerignore` in `h:/HYPERFOCUSZONE/HperCore/BROski-Obsidian-Brain-for-HyperFocus-z0ne/` to ignore:
- `HYPERFOCUS_ZONE/`
- `.obsidian/`
- `sessions/`
- `__pycache__/`, `.pytest_cache/`, `.venv/`
- any large images/artifacts if needed

## Verification
- From `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4`:
  - `docker compose up -d --build`
  - Confirm `hyper-brain` is healthy and serving:
    - `GET http://localhost:8100/health` -> 200
    - `GET http://localhost:8100/ui` -> 200
- Optional profile:
  - `docker compose --profile brain up -d`
  - Confirm `github-sync` starts without affecting `hyper-brain`

