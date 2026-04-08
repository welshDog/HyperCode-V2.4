# MCP Architecture (Win Log) 🚀

## TL;DR
We run the MCP Gateway on the host (Windows) so it can read Docker Desktop’s secret store, then let the Dockerized REST adapter talk to it over SSE. Agents only ever speak REST to `:8821`, and everything else happens behind the curtain.

## Why Host Gateway?
Because Windows + Docker Desktop secrets = ✨special rules✨.

- 🧩 `docker mcp secret set ...` stores secrets in Docker Desktop’s credential store (docker-pass)
- 🚫 The `docker/mcp-gateway` *container* can’t reliably access that Docker Desktop secret store on Windows
- ✅ A **HOST-RUN** gateway process *can* read those secrets
- 🛠️ Solution: **Gateway runs on host**, **adapter stays in Docker**

In other words:
- If you want GitHub tools to authenticate cleanly (no “Secret not found”), the gateway must be host-run.

## Architecture Diagram (ASCII)
```
            (REST)                          (SSE)                          (stdio)
┌───────────────┐     POST /tools/call      ┌────────────────────────┐     ┌─────────────────────┐
│   Agents / AI │ ────────────────────────> │ mcp-rest-adapter :8821  │ ──> │ Host MCP Gateway     │
│ (crew, bots)  │     GET /tools/discover   │  (Docker container)     │     │ docker mcp gateway   │
└───────────────┘                           └────────────────────────┘     │ run :8820            │
                                                                            └─────────┬───────────┘
                                                                                      │ spawns
                                                                                      ▼
                                                                            ┌─────────────────────┐
                                                                            │ Tool containers      │
                                                                            │ - github / github-official
                                                                            │ - filesystem          │
                                                                            │ - postgres            │
                                                                            └─────────────────────┘
```

## Quick Start
### 0) One-time secrets
Do this once (per machine/user):
- Set the GitHub token in Docker MCP secrets (see below)

### 1) Start the host gateway (PowerShell window #1)
- Open a separate PowerShell window
- Run:

```powershell
.\scripts\start-mcp-host-gateway.ps1
```

### 2) Start the adapter in Docker (PowerShell window #2)
Run the adapter (and whatever else you need), but do **not** rely on the `mcp-gateway` container for auth:

```powershell
docker compose -f docker-compose.mcp-gateway.yml up -d mcp-rest-adapter
```

## Secret Setup
### One-time: GitHub PAT → Docker MCP secret store 🔐
```powershell
docker mcp secret set github.personal_access_token <your_token>
docker mcp secret ls
```

Expected to see something like:
```
docker/mcp/github.personal_access_token  | docker-pass
```

## Verification Commands
### 1) Adapter health ✅
```powershell
curl.exe -i http://localhost:8821/health
```

### 2) Tools discovery count 🔎
```powershell
curl.exe http://localhost:8821/tools/discover
```

Today’s working count: **52 tools**

### 3) GitHub through gateway ✅
This call goes: Agent → REST adapter → SSE gateway → GitHub tool container.

```powershell
curl.exe -X POST http://localhost:8821/tools/call `
  -H "Content-Type: application/json" `
  -d "{\"tool\":\"github\",\"action\":\"list_repos\",\"params\":{\"owner\":\"welshDog\"}}"
```

Expected today:
- ✅ GitHub via gateway worked
- ✅ Returned **79 repos** for `welshDog`

### 4) Filesystem `/workspace` ✅
```powershell
curl.exe -X POST http://localhost:8821/tools/call `
  -H "Content-Type: application/json" `
  -d "{\"tool\":\"filesystem\",\"action\":\"list\",\"params\":{\"path\":\"/workspace\"}}"
```

Expected today:
- ✅ `/workspace` listing worked
- ✅ **138 entries**

## Today’s Win 🏆
- 🧠 Health score: **9.5/10**
- 🧰 Tools discovered: **52**
- 🐙 GitHub via gateway: ✅ (**79 repos** from `welshDog` returned)
- 🗂️ Filesystem `/workspace`: ✅ (**138 entries**)
- 🟢 All core services: ✅ healthy

