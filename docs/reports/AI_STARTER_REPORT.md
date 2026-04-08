# 🤖 AI Starter Report: HyperCode V2.0 Context Guide

**Objective:** Rapidly orient an AI agent or LLM to the HyperCode V2.0 codebase for development, debugging, or architectural analysis.

## 1. 🗺️ High-Level Architecture
HyperCode V2.0 is a **neurodivergent-first AI orchestration platform** built on a microservices architecture.
- **Core**: FastAPI backend (`hypercode-core`).
- **Orchestration**: Multi-agent system managed by `crew-orchestrator`.
- **Infrastructure**: Docker Compose managing 33+ containers (Postgres, Redis, MinIO, ChromaDB, Ollama).
- **Observability**: Full stack (Prometheus, Grafana, Loki, Tempo).

## 2. 🔑 Critical Entry Points (Read These First)
| File | Purpose |
|------|---------|
| `README.md` | **Start Here.** Project mission, architecture overview, and quick start. |
| `MASTER_TODO_LIST_2026-03-02.md` | **Current Status.** The single source of truth for immediate tasks and roadmap. |
| `docker-compose.yml` | **System Map.** Defines all services, networks, ports, and volume mounts. |
| `DOCKER_COMPLETE_INVENTORY_REPORT.md` | **Deep Dive.** Detailed specs of every running container. |

## 3. 📂 Directory Structure & Key Files

### 🧠 Core Logic (Backend)
- **Path:** `backend/app/`
- **Key File:** `backend/app/main.py` (FastAPI entry point, routes).
- **Key File:** `backend/app/core/config.py` (Settings management).
- **Key File:** `backend/app/api/api.py` (Router definitions).

### 🤖 AI Agents (The Swarm)
- **Path:** `agents/`
- **Structure:** Each agent has its own directory (e.g., `agents/coder/`, `agents/healer/`).
- **Key File:** `agents/HYPER-AGENT-BIBLE.md` (The "Constitution" for agent behavior and protocols).
- **Key File:** `agents/crew-orchestrator/main.py` (The brain coordinating the swarm).
- **Key File:** `agents/healer/main.py` (Self-healing logic).

### 🖥️ Frontend (Dashboard)
- **Path:** `agents/dashboard/` (Next.js application).
- **Purpose:** Mission Control interface for users.

### ⚙️ Configuration & Env
- **File:** `.env.example` (Template for environment variables).
- **File:** `docker-compose.yml` (Service orchestration).

### 📚 Documentation
- **Path:** `docs/`
- **Key File:** `docs/notes/COGNITIVE_UPLINK_ANALYSIS.md` (Explains the user-agent bridge).
- **Key File:** `SECURITY_OPERATIONS_CHECKLIST.md` (Security hardening tasks).

## 4. 🚀 Operational Commands
- **Start System:** `docker-compose up -d`
- **Run Tests:** `docker compose exec hypercode-core pytest`
- **Backup:** `./scripts/backup_hypercode.sh`
- **Logs:** `docker logs -f <container_name>`

## 5. 💡 Context for AI Tasks
- **If fixing bugs:** Check `backend/app/tests/` for existing coverage.
- **If adding agents:** Reference `agents/HYPER-AGENT-BIBLE.md` for standards.
- **If optimizing:** Check `DOCKER_HEALTH_REPORT.md` for resource usage.
- **If deploying:** Review `SECURITY_OPERATIONS_CHECKLIST.md` first.

---
**Generated:** 2026-03-02
**Status:** Production Ready (Pending Security Hardening)
