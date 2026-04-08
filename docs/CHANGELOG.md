# Changelog

> **built with WelshDog + BROski 🚀🌙**

**Doc Tag:** v2.1.0 | **Last Updated:** 2026-03-25

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 🦅 **Agent X (Meta-Architect)** — autonomous agent designer, deployer and evolver using Docker Model Runner
- 🧠 **Crew Orchestrator** — full agent lifecycle + task execution system (`localhost:8081`)
- 🩺 **Healer Agent** — self-healing monitor, auto-recovers failed services (`localhost:8008`)
- 🖥️ **BROski Terminal** — custom neurodivergent-first CLI UI (`localhost:3000`)
- 🐳 **Docker Model Runner integration** — OpenAI-compatible local LLM backend for agents
- 📡 **MCP Gateway** — fully operational tool gateway for AI agents
- 📊 **Grafana Observability stack** — full metrics/tracing dashboard (`localhost:3001`)
- 📄 **AGENT_X_GUIDE.md** — full guide for Agent X operations
- 📄 **BROSKI_TERMINAL_GUIDE.md** — CLI UI usage and commands
- 📄 **HEALER_AGENT_GUIDE.md** — self-healing agent operations
- 📄 **CREW_ORCHESTRATOR.md** — crew lifecycle and task management
- 📄 **DOCKER_MODEL_RUNNER.md** — Docker Model Runner integration guide

### Changed
- 🏗️ **ARCHITECTURE.md** — updated to reflect full V2.0 agent stack
- 📋 **STATUS_REPORT.md** — updated to current system state (2026-03-25)
- 🔌 **API.md** — expanded with agent endpoints, health checks, MCP routes
- Local-first LLM defaults (TinyLlama-first) with auto model selection and tuned generation options
- Backend documentation links standardized to repo-relative paths

### Fixed
- 🔥 **Tempo container crash on startup** — `grafana/tempo:latest` (v2.10.3+) introduced hardcoded Kafka/ingester config fields that caused immediate exit. Fixed by pinning to `grafana/tempo:2.4.2` and cleaning `tempo/tempo.yaml` of deprecated fields
- 🐳 **`docker-compose.yml`** — Pinned `grafana/tempo` image from `latest` to `2.4.2`
- SQLAlchemy Base migrated to `DeclarativeBase` with SQLAlchemy 2.0 typed models (`Mapped[]`, `mapped_column`)
- Test suite stability improved via deterministic mocks and reduced external side effects during imports

## [2.0.0] - 2026-01-15

### Initial Release
- Core microservices architecture
- Basic Coder Agent capabilities
- Next.js Frontend and FastAPI Backend

---
> **built with WelshDog + BROski 🚀🌙**
