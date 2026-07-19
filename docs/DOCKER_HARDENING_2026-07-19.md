# 🔒 Docker hardening — 2026-07-19

Closes the network exposure found in `DOCKER_SYSTEM_INVENTORY.md`, plus the memory
fragility behind "44/44 healthy".

---

## ✅ FIXED — 5 services were reachable from the whole network

`0.0.0.0` (or a bare `host:container` mapping, which **defaults** to `0.0.0.0`) means
the port listens on **every network interface** — any device on the same wifi can reach it.
All five are now bound to `127.0.0.1`.

| Service | File | Before | After |
|---|---|---|---|
| **Ollama** ⚠️ | `docker-compose.core.yml` | `0.0.0.0:11434:11434` | `127.0.0.1:11434:11434` |
| Hypercode Core API | `docker-compose.core.yml` | `0.0.0.0:8000:8000` | `127.0.0.1:8000:8000` |
| Grafana | `docker-compose.observability.yml` | `3001:3000` | `127.0.0.1:3001:3000` |
| Loki | `docker-compose.observability.yml` | `3100:3100` | `127.0.0.1:3100:3100` |
| node-exporter | `docker-compose.mcp-gateway.yml` | `9101:9100` | `127.0.0.1:9101:9100` |

**Ollama was the worst and the inventory doc missed it.** The Ollama API is
**unauthenticated by default** — anyone who could reach `:11434` could run inference on
your machine, and pull or delete your models.

**Nothing breaks.** Containers talk to each other over the internal Docker network by
service name (`hypercode-core:8000`, `http://hypercode-ollama:11434`), never via the host
port. The host bind exists only for your own browser/tools, and Docker Desktop on WSL2
forwards `127.0.0.1` to the Windows host normally.

### 📌 The inventory doc was WRONG about the web IDE
It listed **3500 (Hyper Agents IDE)** as public. Disk says otherwise —
`docker-compose.trae.yml` already had `127.0.0.1:3500:3000`. It was never exposed.
*(Another label-vs-reality drift. Verify, don't trust.)*

### Apply the changes
Port mappings only change when a container is **recreated** — a restart is not enough:

```powershell
cd "H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4"
docker compose -f docker-compose.core.yml up -d
docker compose -f docker-compose.observability.yml up -d
docker compose -f docker-compose.mcp-gateway.yml up -d
```

### Verify — must return nothing
```powershell
docker ps --format "{{.Names}}`t{{.Ports}}" | Select-String "0.0.0.0"
```

---

## ⚠️ TODO (yours) — memory is the real fragility

**Docker Desktop has 3.825 GB. Declared memory limits total ~72 GB across all compose
files — 19× oversubscribed.** Only a subset of profiles run at once, but even the running
44: **Ollama alone is allowed 3 GB of the 3.825 GB budget**, and it is configured to hold
**2 models loaded for 24h** (`OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_KEEP_ALIVE=24h`).

Limits are *ceilings, not reservations* — so everything looks healthy at idle and starts
OOM-killing when two containers spike together. That's why "44/44 healthy" doesn't predict
behaviour under demo load.

### Fix: give WSL2 more memory
Create/edit **`C:\Users\Lyndz\.wslconfig`** (Windows side — not in this repo):

```ini
[wsl2]
memory=10GB        # if you have 16GB RAM. Use 8GB if 12GB. Never more than ~65% of total.
processors=6
swap=4GB
```

Then, in PowerShell:
```powershell
wsl --shutdown          # closes WSL; Docker Desktop restarts it
```
Reopen Docker Desktop, then confirm:
```powershell
docker info --format "{{.MemTotal}}"
```

### If you can't raise it, lower Ollama instead
In `docker-compose.core.yml` under `hypercode-ollama`:
- `memory: 3G` → `2G`
- `OLLAMA_MAX_LOADED_MODELS=2` → `1`
- `OLLAMA_KEEP_ALIVE=24h` → `30m` (frees memory when idle)

### Prove it under load, not at idle
```powershell
docker stats --no-stream --format "table {{.Name}}`t{{.MemUsage}}`t{{.CPUPerc}}"
```
Run that **while** an agent is actually working. "Healthy at idle" is not the same claim.

---

## 🧹 Disk cleanup — safe order

17.88 GB of build cache is the hog. **Do NOT run `docker system prune -a`** — the `-a`
deletes all unused *images*, forcing a full rebuild of a 44-container stack. Never do that
near a demo.

```powershell
docker builder prune          # ~8.6 GB back, images untouched
docker image prune            # dangling only — no -a
docker volume ls -f dangling=true    # LOOK first; "reclaimable" can mean a detached DB volume
```

---

## Checklist

- [x] 5 exposed ports bound to localhost
- [x] Corrected the inventory's false "IDE exposed" claim
- [ ] Recreate the 3 stacks so the port changes take effect
- [ ] Verify `docker ps | Select-String "0.0.0.0"` returns nothing
- [ ] Raise WSL2 memory via `.wslconfig` (or lower Ollama)
- [ ] Re-check `docker stats` **under load**
- [ ] `docker builder prune` to reclaim ~8.6 GB

> 🐶♾️ Verify against the running system, not the label.
