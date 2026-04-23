# 🚀 HyperCode V2.4.2 Quickstart

**Goal:** Run the entire ecosystem (Agents, API, Dashboard, Observability) in under 2 minutes.

## 📋 Prerequisites

- **Docker & Docker Compose** (Desktop 4.0+)
- **Git**
- **Node.js 18+** (Optional, only for local frontend development)

## ⚡ Steps

### 1. Clone the Repository
```bash
git clone https://github.com/welshDog/HyperCode-V2.4.git
cd HyperCode-V2.4
```

### 2. Configure Environment
Set up your environment variables (API keys, Database credentials).
```bash
cp .env.example .env
# Edit .env and add your PERPLEXITY_API_KEY / OPENAI_API_KEY
```

### 3. Launch the Stack
Start the core services (API + dashboard + observability).
```bash
docker compose up -d
```

### 4. Verify Services
Check that all 23+ containers are healthy.
```bash
docker compose ps
```

## 🖥️ Access Interfaces

| Service | URL | Credentials (Default) |
|---------|-----|-----------------------|
| **Mission Control** | [http://localhost:8088](http://localhost:8088) | Uses Core auth (see `seed_data.py`) |
| **Core API Docs** | [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs) | N/A |
| **Grafana** | [http://localhost:3001](http://localhost:3001) | Set via `GF_SECURITY_ADMIN_USER` / `GF_SECURITY_ADMIN_PASSWORD` in `.env` |
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | N/A |

## 🧭 Ports + Profiles

Some services are always on, while others are opt-in via Docker Compose profiles.

| Service | Port | Profile | Notes |
|---|---:|---|---|
| Core API | 8000 | default | Always on |
| Mission Control | 8088 | default | Always on |
| Healer Agent | 8008 | default | Always on |
| Project Strategist | 8001 | agents | `docker compose --profile agents up -d` |
| AI API | 8002 | ai | `docker compose --profile ai up -d` |
| Grafana | 3001 | default | Always on |
| Prometheus | 9090 | default | Always on |

## 🎮 Run Your First Mission

1. Open the **Web Terminal** at `http://localhost:3000`.
2. Navigate to the **Agents** tab.
3. Select **Coder Agent**.
4. Type: `"Create a Python script that calculates the Fibonacci sequence."`
5. Watch the agent think, plan, and code in real-time.

## 🛑 Stop Services
```bash
docker compose down
```

---
> *Need help? Check [DEPLOYMENT_SUMMARY_ONE_PAGE.md](../deployment/DEPLOYMENT_SUMMARY_ONE_PAGE.md) for quick troubleshooting.*
