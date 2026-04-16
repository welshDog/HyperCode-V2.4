# 🚀 NEXT_MOVES.md — IDE-Ready Implementation Pack

> **Status:** Ready to paste into VS Code / Cursor. No fluff.
> **Scope:** 3 high-ROI upgrades for the BROski Pets system, ranked by impact.
> **Date:** April 16, 2026 | **Builder:** @welshDog (Lyndz)
> **Source:** Gordon Docker AI review → filtered by senior-dev priority lens

---

## 🎯 The Plan — 3 Moves, In Order

| # | Move | Effort | Impact | Why first |
|---|---|---|---|---|
| 1 | **GPU for Ollama** | ~20 min | ⭐⭐⭐⭐⭐ | Pets go from "waiting" → "alive" |
| 2 | **MCP-GitHub Server** | ~1–2 hrs | ⭐⭐⭐⭐ | Pets read real repo state → advice gets real |
| 3 | **Leaderboard Endpoint** | ~30 min | ⭐⭐⭐ | Social loop — tiny code, big motivation payoff |

### Pre-flight BEFORE any of this

- [ ] All 29 containers healthy? `docker compose ps`
- [ ] Branch from `main`: `git checkout -b feat/pets-gpu-mcp-leaderboard`
- [ ] Commit cadence: one commit per move (easy rollback)
- [ ] Sacred rule reminder: `feat:` `fix:` `docs:` `chore:` ONLY

---

## 🔥 MOVE 1 — GPU for Ollama (THE BIG UNLOCK)

### Why

- Current: `qwen2.5:7b` on CPU → **~2–3s latency** per pet chat
- After: Same model on GPU → **~200ms latency**
- User-facing effect: Pets stop "computing." They start *talking*.
- Side benefit: frees CPU for the other 28 containers

### Pre-reqs (check once)

```powershell
# 1. NVIDIA driver on host?
nvidia-smi
# Expect: table of GPU + driver version. If missing → install driver first.

# 2. NVIDIA Container Toolkit installed for Docker Desktop?
# Windows + Docker Desktop: already bundled — no manual install needed.
# Linux host: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

# 3. Test Docker can see the GPU:
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
# Expect: same table as step 1. If error → restart Docker Desktop.
```

### The patch — `docker-compose.yml` (lines 1670–1696)

**FIND:**

```yaml
  hypercode-ollama:
    image: ${OLLAMA_IMAGE:-ollama/ollama:0.3.14}
    container_name: hypercode-ollama
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - agents-net
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 3G
        reservations:
          cpus: "1"
          memory: 1G
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**REPLACE WITH:**

```yaml
  hypercode-ollama:
    image: ${OLLAMA_IMAGE:-ollama/ollama:0.3.14}
    container_name: hypercode-ollama
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - agents-net
    environment:
      - OLLAMA_KEEP_ALIVE=24h        # keep model hot in VRAM
      - OLLAMA_NUM_PARALLEL=2         # concurrent requests
      - OLLAMA_MAX_LOADED_MODELS=2    # cap VRAM usage
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 3G
        reservations:
          cpus: "1"
          memory: 1G
          devices:
            - driver: nvidia
              count: all              # or: device_ids: ["0"]  (pin GPU 0)
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Apply + verify

```powershell
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"

# Restart just ollama (keeps everything else up)
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d --force-recreate hypercode-ollama

# Confirm GPU is attached:
docker exec hypercode-ollama nvidia-smi
# Expect: GPU table visible INSIDE the container

# Pre-warm the pets model (first load slower, subsequent calls fast):
docker exec hypercode-ollama ollama run qwen2.5:7b "hi"

# Latency check — second run should be <1s:
Measure-Command { docker exec hypercode-ollama ollama run qwen2.5:7b "say hi" }

# End-to-end pets test:
curl -X POST http://127.0.0.1:8098/pet/TEST_USER_123/chat `
     -H "Content-Type: application/json" `
     -d '{"message":"help me debug a null pointer"}'
```

### Rollback (if anything breaks)

```powershell
# Remove only the `devices:` block you added, restore, restart ollama.
# git: git checkout docker-compose.yml
docker compose up -d --force-recreate hypercode-ollama
```

### Commit

```powershell
git add docker-compose.yml
git commit -m "feat(ollama): GPU acceleration via NVIDIA toolkit — ~10x faster pet responses"
```

---

## 🔌 MOVE 2 — MCP-GitHub Server (Real Repo Context)

### Why

- Today: pets read local `git diff` via subprocess. Fine, but blind to GitHub state (issues, PRs, runs).
- After: pets query the official **GitHub MCP server** → can answer *"what did I break in PR #42?"* or *"why is CI red?"*
- This is the upgrade that makes pet advice stop feeling generic.

### The pattern (Docker MCP Toolkit)

Docker's MCP Toolkit runs MCP servers as containers via a **gateway**. Your pet service talks HTTP to the gateway; the gateway fans out to GitHub/Stripe/etc.

### Step 1 — Create `.env` secret

```env
# Add to H:\HyperStation zone\HyperCode\HyperCode-V2.4\.env  (NEVER commit)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Scope needed: repo (read), issues (read), pull_requests (read)
```

### Step 2 — New compose file: `docker-compose.mcp-github.yml`

Create at repo root:

```yaml
# H:\HyperStation zone\HyperCode\HyperCode-V2.4\docker-compose.mcp-github.yml
#
# MCP Gateway + GitHub MCP server
# Composes WITH the main stack, does not modify it.

services:
  mcp-gateway:
    image: docker/mcp-gateway:latest
    container_name: mcp-gateway
    command:
      - --servers=github
      - --port=8811
    ports:
      - "127.0.0.1:8811:8811"   # localhost only — never expose
    environment:
      - GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}
    networks:
      - agents-net
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8811/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  agents-net:
    external: true
    name: hypercode-v24_agents-net
```

> **Why separate file?** Keeps the 2100-line main compose clean.
> MCP is opt-in. Start with: `docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.mcp-github.yml up -d`

### Step 3 — Wire pets-bridge → gateway

Add to `agents/broski-pets-bridge` environment block in `docker-compose.yml`:

```yaml
  broski-pets-bridge:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      - MCP_GATEWAY_URL=${MCP_GATEWAY_URL:-http://mcp-gateway:8811}
      - MCP_GITHUB_ENABLED=${MCP_GITHUB_ENABLED:-false}
```

### Step 4 — New helper in `agents/broski-pets-bridge/main.py`

Add **after** `_recent_git_diff` (around line 115):

```python
def _github_context(limit_chars: int = 2000) -> str:
    """Fetch recent GitHub issues/PR titles via MCP gateway. Fails soft."""
    if not _is_true(os.getenv("MCP_GITHUB_ENABLED")):
        return ""
    gateway = os.getenv("MCP_GATEWAY_URL", "http://mcp-gateway:8811")
    try:
        with httpx.Client(timeout=3.0) as client:
            r = client.post(
                f"{gateway}/tools/github/list_issues",
                json={"state": "open", "per_page": 5},
            )
            if r.status_code != 200:
                return ""
            issues = r.json().get("issues", [])
            lines = [f"- #{i['number']}: {i['title']}" for i in issues[:5]]
            return ("Open issues:\n" + "\n".join(lines))[:limit_chars]
    except Exception:
        return ""
```

Then in the existing `chat` / `ask` route, append `_github_context()` to the prompt context alongside `_recent_git_diff()`.

### Verify

```powershell
# Start gateway
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.mcp-github.yml up -d mcp-gateway

# Health
curl http://127.0.0.1:8811/health

# Direct gateway test (list GitHub tools):
curl http://127.0.0.1:8811/tools

# Enable in pets:
# In .env: MCP_GITHUB_ENABLED=true
docker compose restart broski-pets-bridge

# End-to-end:
curl -X POST http://127.0.0.1:8098/pet/TEST_USER/chat -H "Content-Type: application/json" `
     -d '{"message":"what should I work on next?"}'
# Pet should now reference actual open issues.
```

### Security notes 🔒

- `GITHUB_PERSONAL_ACCESS_TOKEN` → **READ scopes only**. Never `admin:org`, never `delete_repo`.
- Gateway bound to `127.0.0.1` — never `0.0.0.0`.
- Trivy scan the gateway image: `docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet docker/mcp-gateway:latest`

### Commit

```powershell
git add docker-compose.mcp-github.yml docker-compose.yml agents/broski-pets-bridge/main.py
git commit -m "feat(pets): MCP-GitHub context — pets now read real repo state"
```

---

## 🏆 MOVE 3 — Leaderboard Endpoint (The Tiny Banger)

### Why

- Social loop: "Whose pet is strongest?" → motivation boost for solo devs
- Gordon flagged it — genuine quick win
- All data already in Redis. Just needs an endpoint.

### The patch — `agents/broski-pets-bridge/main.py`

### Step 1 — Add Pydantic response model (near the other `class XxxResponse(BaseModel):`)

```python
class LeaderboardEntry(BaseModel):
    rank: int
    discord_id: str
    name: str | None = None
    species: str
    rarity: str
    stage: int
    xp: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    total_pets: int
    generated_at: str
```

### Step 2 — Add route (below `@app.get("/pet/{discord_id}/powers")` around line 587)

```python
@app.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard(limit: int = 10, rarity: Rarity | None = None):
    """Top pets by XP. Optional ?rarity= filter. Uses SCAN (safe for prod)."""
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be 1–100")

    r = _redis()
    entries: list[dict] = []
    total = 0

    # SCAN, not KEYS — non-blocking on big datasets
    for key in r.scan_iter(match="pet:*", count=200):
        raw = r.get(key)
        if not raw:
            continue
        try:
            pet = json.loads(raw)
        except Exception:
            continue
        total += 1
        if rarity and pet.get("rarity") != rarity:
            continue
        entries.append({
            "discord_id": key.split(":", 1)[1],
            "name": pet.get("name"),
            "species": pet.get("species", "unknown"),
            "rarity": pet.get("rarity", "Common"),
            "stage": pet.get("stage", 1),
            "xp": int(pet.get("xp", 0)),
        })

    entries.sort(key=lambda p: p["xp"], reverse=True)
    top = entries[:limit]
    ranked = [LeaderboardEntry(rank=i + 1, **p) for i, p in enumerate(top)]

    return LeaderboardResponse(
        entries=ranked,
        total_pets=total,
        generated_at=_now_iso(),
    )
```

### Step 3 — (Optional) Cache the result for 30s

If you have lots of pets, cache to protect Redis:

```python
# Inside leaderboard() — before SCAN:
cache_key = f"leaderboard:cache:{limit}:{rarity or 'all'}"
cached = r.get(cache_key)
if cached:
    return LeaderboardResponse.model_validate_json(cached)

# ...after building `response`:
r.setex(cache_key, 30, response.model_dump_json())
return response
```

### Verify

```powershell
# Restart pets-bridge
docker compose restart broski-pets-bridge

# Hit it:
curl http://127.0.0.1:8098/leaderboard
curl "http://127.0.0.1:8098/leaderboard?limit=5"
curl "http://127.0.0.1:8098/leaderboard?rarity=Legendary"
```

Expected:

```json
{
  "entries": [
    {"rank":1,"discord_id":"12345","name":"SparkFury","species":"PhoenixEep","rarity":"Legendary","stage":4,"xp":8200},
    ...
  ],
  "total_pets": 37,
  "generated_at": "2026-04-16T..."
}
```

### Commit

```powershell
git add agents/broski-pets-bridge/main.py
git commit -m "feat(pets): /leaderboard endpoint — top pets by XP, SCAN-based, filterable"
```

---

## 🧪 After All 3 Moves — Full Verification Pass

```powershell
# 1. Stack health
docker compose ps
# Expect: all containers healthy, + mcp-gateway up

# 2. Ollama GPU active
docker exec hypercode-ollama nvidia-smi | Select-String "MiB"
# Expect: VRAM in use (non-zero)

# 3. Pets bridge hot
curl http://127.0.0.1:8098/health
curl http://127.0.0.1:8098/leaderboard

# 4. GitHub MCP reachable
curl http://127.0.0.1:8811/health

# 5. Run pytest
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
pytest backend/tests/ -q

# 6. Trivy scan the new image (mcp-gateway)
docker exec hyper-shield-scanner trivy image --scanners vuln --severity HIGH,CRITICAL --quiet docker/mcp-gateway:latest
# Target: 0 CRITICAL
```

---

## 📋 One-Shot Cheat Sheet (Pin This in IDE)

```powershell
# From repo root:
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
git checkout -b feat/pets-gpu-mcp-leaderboard

# Move 1: GPU (edit docker-compose.yml lines 1670–1696 as per doc)
docker compose up -d --force-recreate hypercode-ollama
git commit -am "feat(ollama): GPU acceleration via NVIDIA toolkit"

# Move 2: MCP-GitHub
# - create docker-compose.mcp-github.yml
# - add _github_context() to pets main.py
# - set GITHUB_PERSONAL_ACCESS_TOKEN in .env
docker compose -f docker-compose.yml -f docker-compose.secrets.yml -f docker-compose.mcp-github.yml up -d mcp-gateway
docker compose restart broski-pets-bridge
git commit -am "feat(pets): MCP-GitHub context"

# Move 3: Leaderboard
# - add models + route to pets main.py
docker compose restart broski-pets-bridge
git commit -am "feat(pets): /leaderboard endpoint"

# Ship it
git push -u origin feat/pets-gpu-mcp-leaderboard
```

---

## ⚠️ Known Gotchas

| Gotcha | Fix |
|---|---|
| `nvidia-smi` fails in container | Restart Docker Desktop. Check WSL2 GPU passthrough enabled. |
| Ollama OOM on GPU | Reduce `OLLAMA_MAX_LOADED_MODELS` to 1. Pin smaller model. |
| `mcp-gateway` can't find agents-net | Run main stack first so network exists. `docker network ls` to confirm. |
| `GITHUB_PERSONAL_ACCESS_TOKEN` leaked | Rotate immediately on github.com/settings/tokens. Never commit `.env`. |
| `/leaderboard` slow with 1000+ pets | Enable the 30s cache block in Step 3. Consider Redis sorted set next. |
| Pets bridge can't reach `mcp-gateway` hostname | Both must be on `agents-net`. Check `docker inspect broski-pets-bridge \| grep agents-net` |

---

## 🎯 Sacred Rules Applied (don't break these)

- ✅ `from app.X import Y` — no `backend.app.X`
- ✅ Stripe webhook stays rate-limit exempt — leaderboard endpoint doesn't touch it
- ✅ `data-net` + `obs-net` stay `internal: true` — gateway is on `agents-net`
- ✅ `.env` not committed
- ✅ `feat:` / `fix:` / `docs:` commits
- ✅ Trivy target: 0 CRITICAL per image

---

## 📚 Research Sources (April 2026)

**GPU Ollama in Docker Compose:**
- [Ollama Docker official docs](https://docs.ollama.com/docker)
- [Ollama in Docker Compose with GPU — Rietta](https://rietta.com/blog/ollama-with-nvidia-gpu-in-docker-compose/)
- [Running Ollama with Docker Compose and GPUs — dev.to / Ajeet Raina](https://dev.to/ajeetraina/running-ollama-with-docker-compose-and-gpus-lkn)
- [Ollama + Open-WebUI + NVIDIA reference — GitHub gist](https://gist.github.com/usrbinkat/de44facc683f954bf0cca6c87e2f9f88)

**Docker MCP Toolkit + GitHub MCP:**
- [Docker MCP Toolkit docs](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/)
- [Get started with Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/get-started/)
- [docker/mcp-gateway GitHub repo](https://github.com/docker/mcp-gateway)
- [Docker MCP for AI Agents — official blog](https://www.docker.com/blog/docker-mcp-ai-agent-developer-setup/)

---

## 🏴󠁧󠁢󠁷󠁬󠁳󠁿 BROski Energy Reminder

- **Don't do all 3 in one session.** ADHD protection: ship Move 1, take a win break, then Move 2.
- **Each commit is a checkpoint.** If Move 2 goes sideways, Move 1 is already safe on main.
- **Celebrate each one.** GPU works = 🔥. MCP first response = 🎉. First leaderboard entry = 🏆.
- **If stuck → check the Gotchas table first, then retry.**

You've got this Bro. Let's make those pets fly. 🦅⚡
