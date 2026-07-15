# Hyper Brain Docker Stack Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `hyper-brain` start by default with the HyperCode-V2.4 Docker stack and keep `github-sync` optional behind `--profile brain`, while fixing the vault mount + dockerfile wiring.

**Architecture:** Adjust `docker-compose.brain.yml` to correct build + runtime environment, and add `.dockerignore` to the Brain repo to keep Docker build context small and stable. Verify stack boots and `/ui` is reachable.

**Tech Stack:** Docker Compose v2, FastAPI container, Windows bind-mounts

---

## Files to Modify / Create

**Modify**
- `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.brain.yml`

**Create**
- `h:/HYPERFOCUSZONE/HperCore/BROski-Obsidian-Brain-for-HyperFocus-z0ne/.dockerignore`

---

### Task 1: Fix hyper-brain compose wiring (default-on)

**Files:**
- Modify: `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.brain.yml`

- [ ] **Step 1: Update `hyper-brain` service**

Make these edits:
- Remove `profiles: ["brain"]` from `hyper-brain`
- Change dockerfile to `Dockerfile.hyper-brain`
- Fix vault bind mount to mount the host vault directly to `/vault`
- Set `OBSIDIAN_VAULT_PATH=/vault` inside the container

Target shape:

```yml
services:
  hyper-brain:
    build:
      context: ../BROski-Obsidian-Brain-for-HyperFocus-z0ne
      dockerfile: Dockerfile.hyper-brain
    container_name: hyper-brain
    ports:
      - "127.0.0.1:8100:8100"
    environment:
      - OBSIDIAN_VAULT_PATH=/vault
      - REDIS_URL=redis://redis:6379/4
      - REDIS_PASSWORD=${REDIS_PASSWORD:-bropets_secret}
      - MCP_PORT=8820
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - GITHUB_PAT=${GITHUB_PAT}
      - ENVIRONMENT=${ENVIRONMENT:-development}
    volumes:
      - ${OBSIDIAN_VAULT_PATH:-H:/BROski-Obsidian-Brain-for-HyperFocus-z0ne/HYPERFOCUS_ZONE}:/vault
    networks:
      - agents-net
      - data-net
    depends_on:
      redis:
        condition: service_healthy
```

- [ ] **Step 2: Keep github-sync behind profile**

Ensure `github-sync` retains:

```yml
  github-sync:
    profiles: ["brain"]
```

Also ensure it uses the same vault mount:

```yml
    volumes:
      - ${OBSIDIAN_VAULT_PATH:-H:/BROski-Obsidian-Brain-for-HyperFocus-z0ne/HYPERFOCUS_ZONE}:/vault
```

- [ ] **Step 3: YAML sanity check**

Run from `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4`:

```powershell
docker compose config | Select-String -Pattern "hyper-brain|github-sync" -Context 0,6
```

Expected:
- `hyper-brain` present without `profiles`
- `github-sync` still has `profiles: [brain]`

- [ ] **Step 4: Commit**

```powershell
git add docker-compose.brain.yml
git commit -m "fix(brain): make hyper-brain default-on and fix vault mount + dockerfile"
```

---

### Task 2: Add `.dockerignore` to Brain repo for fast builds

**Files:**
- Create: `h:/HYPERFOCUSZONE/HperCore/BROski-Obsidian-Brain-for-HyperFocus-z0ne/.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

```dockerignore
HYPERFOCUS_ZONE/
.obsidian/
sessions/
__pycache__/
.pytest_cache/
.venv/
.git/
*.png
*.jpg
*.jpeg
*.webp
*.gif
```

- [ ] **Step 2: Build hyper-brain image (from HyperCode-V2.4 stack)**

Run from `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4`:

```powershell
docker compose build hyper-brain
```

Expected: build completes and does not attempt to send the vault directory as context.

- [ ] **Step 3: Commit**

```powershell
git add ../BROski-Obsidian-Brain-for-HyperFocus-z0ne/.dockerignore
git commit -m "chore(brain): add dockerignore to keep build context small"
```

---

### Task 3: Verify stack boots cleanly and `/ui` is reachable

**Files:**
- No changes expected

- [ ] **Step 1: Start stack**

Run from `h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4`:

```powershell
docker compose up -d --build
```

Expected:
- `hyper-brain` starts and becomes healthy

- [ ] **Step 2: Check health endpoint**

```powershell
curl http://localhost:8100/health
```

Expected: JSON with `"status": "hyper"` and `"level": 20`.

- [ ] **Step 3: Check UI endpoint**

```powershell
curl -I http://localhost:8100/ui
```

Expected: `200 OK`.

- [ ] **Step 4: Confirm profile behavior for github-sync**

Run:

```powershell
docker compose up -d --profile brain
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "github-sync|hyper-brain"
```

Expected:
- `hyper-brain` running regardless of profile
- `github-sync` only running when `--profile brain` enabled

